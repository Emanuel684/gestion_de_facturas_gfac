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
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.httpsredirect import HTTPSRedirectMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from sqlalchemy import select, and_, func

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
    NotificationType,
)
from src.notifications import create_notification_for_org
from src.routers import (
    auth,
    billing,
    fiscal,
    invoices,
    notifications,
    organizations,
    platform_insights,
    public_signup,
    reports,
    users,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(name)s — %(message)s",
)
logger = logging.getLogger(__name__)

SECURITY_HEADERS = {
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "Referrer-Policy": "strict-origin-when-cross-origin",
    "Permissions-Policy": "camera=(), microphone=(), geolocation=()",
    "X-XSS-Protection": "0",
}


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
    docs_url="/docs" if settings.enable_openapi else None,
    redoc_url="/redoc" if settings.enable_openapi else None,
    openapi_url="/openapi.json" if settings.enable_openapi else None,
)

# ── CORS ──────────────────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=[] if settings.cors_allow_any else settings.cors_origins_list,
    allow_origin_regex=".*" if settings.cors_allow_any else None,
    allow_credentials=True,
    allow_methods=settings.cors_allow_methods_list,
    allow_headers=settings.cors_allow_headers_list,
)
if not settings.trusted_hosts_allow_any:
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=settings.trusted_hosts_list)
if settings.require_https_redirect:
    app.add_middleware(HTTPSRedirectMiddleware)


@app.middleware("http")
async def add_security_headers(request, call_next):
    response = await call_next(request)
    for key, value in SECURITY_HEADERS.items():
        response.headers.setdefault(key, value)
    response.headers.setdefault(
        "Content-Security-Policy",
        "default-src 'self'; frame-ancestors 'none'; object-src 'none'; base-uri 'self';"
        " img-src 'self' data: blob:; style-src 'self' 'unsafe-inline'; script-src 'self';",
    )
    if settings.is_production:
        response.headers.setdefault("Strict-Transport-Security", "max-age=31536000; includeSubDomains")
    return response

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
app.include_router(notifications.router)


# ── Startup ───────────────────────────────────────────────────────────────────
@app.on_event("startup")
async def on_startup() -> None:
    if settings.auto_migrate_on_startup and os.getenv("SKIP_ALEMBIC_ON_STARTUP", "").lower() not in ("1", "true", "yes"):
        await asyncio.to_thread(_run_alembic_upgrade)

    if not settings.seed_demo_data:
        asyncio.create_task(_expire_overdue_invoices_loop())
        asyncio.create_task(_reconcile_subscriptions_loop())
        return

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

        await db.flush()

        target_demo_invoices = 100
        r_count = await db.execute(
            select(func.count())
            .select_from(Invoice)
            .where(Invoice.organization_id == demo.id)
        )
        current_demo_invoices = r_count.scalar_one()

        if current_demo_invoices < target_demo_invoices:
            r_admin = await db.execute(
                select(User).where(
                    User.organization_id == demo.id,
                    User.username == "admin",
                )
            )
            admin_user = r_admin.scalar_one_or_none()
            if admin_user:
                r_numbers = await db.execute(
                    select(Invoice.invoice_number).where(Invoice.organization_id == demo.id)
                )
                existing_numbers = set(r_numbers.scalars().all())
                to_create = target_demo_invoices - current_demo_invoices
                created = 0
                seq = 1
                now = datetime.now(timezone.utc)
                statuses = [InvoiceStatus.pendiente, InvoiceStatus.pagada, InvoiceStatus.vencida]

                while created < to_create:
                    invoice_number = f"FAC-DEMO-{seq:04d}"
                    seq += 1
                    if invoice_number in existing_numbers:
                        continue

                    status = statuses[created % len(statuses)]
                    issue_date = now - timedelta(days=(created % 60))
                    due_date = issue_date + timedelta(days=30)
                    amount = Decimal("50000.00") + (Decimal(created % 25) * Decimal("12500.00"))

                    db.add(
                        Invoice(
                            organization_id=demo.id,
                            invoice_number=invoice_number,
                            supplier=f"Proveedor {((created % 12) + 1):02d}",
                            description=f"Factura de prueba #{created + 1}",
                            amount=amount,
                            status=status,
                            due_date=due_date,
                            creator_id=admin_user.id,
                            issue_date=issue_date,
                        )
                    )
                    existing_numbers.add(invoice_number)
                    created += 1

                logger.info(
                    "Seeded %d demo invoices (total target=%d)",
                    created,
                    target_demo_invoices,
                )
            else:
                logger.warning("No se pudieron sembrar facturas demo: usuario admin no encontrado")

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
                pending_rows = await db.execute(
                    select(Invoice.id, Invoice.organization_id, Invoice.invoice_number).where(
                        and_(
                            Invoice.status == InvoiceStatus.pendiente,
                            Invoice.due_date != None,  # noqa: E711
                            Invoice.due_date < now,
                        )
                    )
                )
                overdue_items = pending_rows.all()
                expired_ids = [row.id for row in overdue_items]
                if expired_ids:
                    await db.execute(
                        update(Invoice)
                        .where(Invoice.id.in_(expired_ids))
                        .values(status=InvoiceStatus.vencida)
                    )
                    for item in overdue_items:
                        await create_notification_for_org(
                            db,
                            organization_id=item.organization_id,
                            exclude_user_id=None,
                            notification_type=NotificationType.invoice_overdue_auto,
                            title="Factura marcada como vencida",
                            message=(
                                f"La factura {item.invoice_number} cambió automáticamente a vencida "
                                "por fecha de pago expirada."
                            ),
                            invoice_id=item.id,
                            payload={"invoice_number": item.invoice_number},
                        )
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
    payload = {"message": "Sistema de Gestión de Facturas (SGF)"}
    if settings.enable_openapi:
        payload["docs"] = "/docs"
    return payload
