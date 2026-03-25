"""
FastAPI application entry point — Sistema de Gestión de Facturas (SGF).

On startup: seeds organizations and users if missing. Schema is applied with
`alembic upgrade head` (see docker-compose) before the process starts.

  - Plataforma: super / super123 (plataforma_admin)
  - Demo: admin, maria, carlos (roles tenant)
"""
import asyncio
import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import select, and_

from src.auth import hash_password
from src.config import settings
from src.models import (
    Organization,
    PlanTier,
    User,
    UserRole,
    Invoice,
    InvoiceStatus,
)
from src.routers import auth, invoices, users, organizations

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(name)s — %(message)s",
)
logger = logging.getLogger(__name__)

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
app.include_router(users.router)


# ── Startup ───────────────────────────────────────────────────────────────────
@app.on_event("startup")
async def on_startup() -> None:
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


# ── Background: auto-expire overdue invoices ──────────────────────────────────

EXPIRE_INTERVAL_SECONDS = 3600


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


@app.get("/health", tags=["health"])
async def health() -> dict:
    return {"status": "ok"}


@app.get("/", tags=["health"])
async def root() -> dict:
    return {"message": "Sistema de Gestión de Facturas (SGF)", "docs": "/docs"}
