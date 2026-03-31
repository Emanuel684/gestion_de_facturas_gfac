"""
FastAPI application entry point — Sistema de Gestión de Facturas (SGF).

On startup: runs `alembic upgrade head` (subprocess) unless SKIP_ALEMBIC_ON_STARTUP is set,
then seeds organizations and users if missing. Docker Compose also runs Alembic before uvicorn.

  - Plataforma: super / super123 (plataforma_admin)
  - Demo: admin, maria, carlos (roles tenant)
"""
import asyncio
import logging
import os
import subprocess
import sys
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import select, and_

from src.auth import hash_password
from src.billing import grace_end_from, now_utc, period_end_from, recompute_subscription_status
from src.config import settings
from src.models import (
    Organization,
    PlanTier,
    Subscription,
    SubscriptionStatus,
    User,
    UserRole,
    Invoice,
    InvoiceStatus,
)
from src.routers import auth, billing, fiscal, invoices, organizations, platform_insights, public_signup, reports, users

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(name)s — %(message)s",
)
logger = logging.getLogger(__name__)


def _run_alembic_upgrade() -> None:
    """Aplica migraciones en un subproceso (Alembic usa asyncio.run en env.py; no mezclar con el loop de uvicorn)."""
    root = Path(__file__).resolve().parent.parent
    r = subprocess.run(
        [sys.executable, "-m", "alembic", "upgrade", "head"],
        cwd=str(root),
        capture_output=True,
        text=True,
        check=False,
    )
    if r.returncode != 0:
        logger.error("alembic stdout:\n%s", r.stdout)
        logger.error("alembic stderr:\n%s", r.stderr)
        r.check_returncode()
    logger.info("Alembic: schema al día (upgrade head).")


app = FastAPI(
    title="Sistema de Gestión de Facturas (SGF)",
    description="API multi-organización para gestión de facturas en PYMES.",
    version="1.1.0",
)

# ── CORS ──────────────────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Routers ───────────────────────────────────────────────────────────────────
app.include_router(auth.router)
app.include_router(organizations.router)
app.include_router(invoices.router)
app.include_router(reports.router)
app.include_router(platform_insights.router)
app.include_router(users.router)
app.include_router(billing.router)
app.include_router(public_signup.router)
app.include_router(fiscal.router)


# ── Startup ───────────────────────────────────────────────────────────────────
@app.on_event("startup")
async def on_startup() -> None:
    if os.getenv("SKIP_ALEMBIC_ON_STARTUP", "").lower() not in ("1", "true", "yes"):
        await asyncio.to_thread(_run_alembic_upgrade)

    from src.db import AsyncSessionLocal

    async with AsyncSessionLocal() as db:
        # ── Plataforma (administradores de producto) ──────────────────────────
        r_plat = await db.execute(select(Organization).where(Organization.slug == "plataforma"))
        if not r_plat.scalar_one_or_none():
            plat = Organization(
                name="Plataforma SGF",
                slug="plataforma",
                plan_tier=PlanTier.empresarial,
            )
            db.add(plat)
            await db.flush()
            db.add(
                User(
                    organization_id=plat.id,
                    username="super",
                    email="super@example.com",
                    hashed_password=hash_password("super123"),
                    role=UserRole.plataforma_admin,
                )
            )
            logger.info("Seeded platform org + user super (plataforma_admin)")

        # ── Organización demo (cliente de ejemplo) ───────────────────────────
        r_demo = await db.execute(select(Organization).where(Organization.slug == "demo"))
        demo = r_demo.scalar_one_or_none()
        if demo is None:
            demo = Organization(
                name="Empresa Demo",
                slug="demo",
                plan_tier=PlanTier.profesional,
            )
            db.add(demo)
            await db.flush()
            logger.info("Seeded organization: demo")
        r_sub = await db.execute(select(Subscription).where(Subscription.organization_id == demo.id))
        if r_sub.scalar_one_or_none() is None:
            now = now_utc()
            end = period_end_from(now)
            db.add(
                Subscription(
                    organization_id=demo.id,
                    plan_tier=PlanTier.profesional,
                    status=SubscriptionStatus.active,
                    current_period_start=now,
                    current_period_end=end,
                    next_due_date=end,
                    grace_expires_at=grace_end_from(end),
                    last_paid_at=now,
                )
            )

        seed_users = [
            {"username": "admin", "email": "admin@example.com", "password": "admin123", "role": UserRole.administrador},
            {"username": "maria", "email": "maria@example.com", "password": "maria123", "role": UserRole.contador},
            {"username": "carlos", "email": "carlos@example.com", "password": "carlos123", "role": UserRole.asistente},
        ]
        for data in seed_users:
            q = await db.execute(
                select(User).where(
                    User.organization_id == demo.id,
                    User.username == data["username"],
                )
            )
            if not q.scalar_one_or_none():
                db.add(
                    User(
                        organization_id=demo.id,
                        username=data["username"],
                        email=data["email"],
                        hashed_password=hash_password(data["password"]),
                        role=data["role"],
                    )
                )
                logger.info("Seeded user: %s (%s) in org demo", data["username"], data["role"].value)

        await db.commit()

    asyncio.create_task(_expire_overdue_invoices_loop())
    asyncio.create_task(_reconcile_subscriptions_loop())


# ── Background: auto-expire overdue invoices ──────────────────────────────────

EXPIRE_INTERVAL_SECONDS = 3600
SUBSCRIPTION_RECONCILE_SECONDS = 3600


async def _expire_overdue_invoices_loop() -> None:
    from src.db import AsyncSessionLocal
    from datetime import datetime, timezone
    from sqlalchemy import update

    while True:
        try:
            now = datetime.now(timezone.utc)
            async with AsyncSessionLocal() as db:
                result = await db.execute(
                    update(Invoice)
                    .where(
                        and_(
                            Invoice.status == InvoiceStatus.pendiente,
                            Invoice.due_date != None,  # noqa: E711
                            Invoice.due_date < now,
                        )
                    )
                    .values(status=InvoiceStatus.vencida)
                    .returning(Invoice.id)
                )
                expired_ids = result.scalars().all()
                await db.commit()

            if expired_ids:
                logger.info(
                    "Auto-expired %d invoice(s) to 'vencida': ids=%s",
                    len(expired_ids),
                    expired_ids,
                )
        except Exception:
            logger.exception("Error in overdue-invoice expiry task")

        await asyncio.sleep(EXPIRE_INTERVAL_SECONDS)


async def _reconcile_subscriptions_loop() -> None:
    from src.db import AsyncSessionLocal

    while True:
        try:
            async with AsyncSessionLocal() as db:
                result = await db.execute(select(Subscription))
                subscriptions = result.scalars().all()
                for sub in subscriptions:
                    recompute_subscription_status(sub)
                await db.commit()
        except Exception:
            logger.exception("Error reconciling subscriptions")

        await asyncio.sleep(SUBSCRIPTION_RECONCILE_SECONDS)


@app.get("/health", tags=["health"])
async def health() -> dict:
    return {"status": "ok"}


@app.get("/", tags=["health"])
async def root() -> dict:
    return {"message": "Sistema de Gestión de Facturas (SGF)", "docs": "/docs"}
