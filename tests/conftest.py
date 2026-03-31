"""
Test fixtures — Sistema de Gestión de Facturas (SGF).

Uses an in-memory SQLite database (via aiosqlite). Each test gets a fresh DB.
Login uses organization_slug + username + password.
"""
import os

# Evitar `alembic upgrade head` en el arranque de la app (usa DATABASE_URL real).
os.environ.setdefault("SKIP_ALEMBIC_ON_STARTUP", "true")

from datetime import timedelta

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from src.auth import hash_password
from src.billing import now_utc
from src.db import Base, get_db
from src.main import app
from src.models import Organization, PlanTier, Subscription, SubscriptionStatus, User, UserRole

TEST_DB_URL = "sqlite+aiosqlite:///:memory:"
TEST_ORG_SLUG = "test-org"


@pytest_asyncio.fixture()
async def db_session():
    engine = create_async_engine(TEST_DB_URL, connect_args={"check_same_thread": False})
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)

    async with session_factory() as session:
        yield session

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest_asyncio.fixture()
async def client(db_session: AsyncSession):
    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        yield ac

    app.dependency_overrides.clear()


@pytest_asyncio.fixture()
async def tenant_org(db_session: AsyncSession) -> Organization:
    org = Organization(
        name="Test Org",
        slug=TEST_ORG_SLUG,
        plan_tier=PlanTier.basico,
    )
    db_session.add(org)
    await db_session.flush()
    now = now_utc()
    db_session.add(
        Subscription(
            organization_id=org.id,
            plan_tier=PlanTier.basico,
            status=SubscriptionStatus.active,
            current_period_start=now,
            current_period_end=now + timedelta(days=30),
            next_due_date=now + timedelta(days=30),
            grace_expires_at=now + timedelta(days=40),
            last_paid_at=now,
        )
    )
    await db_session.commit()
    await db_session.refresh(org)
    return org


@pytest_asyncio.fixture()
async def admin_user(db_session: AsyncSession, tenant_org: Organization) -> User:
    user = User(
        organization_id=tenant_org.id,
        username="admin",
        email="admin@example.com",
        hashed_password=hash_password("admin123"),
        role=UserRole.administrador,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest_asyncio.fixture()
async def contador_user(db_session: AsyncSession, tenant_org: Organization) -> User:
    user = User(
        organization_id=tenant_org.id,
        username="maria",
        email="maria@example.com",
        hashed_password=hash_password("maria123"),
        role=UserRole.contador,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest_asyncio.fixture()
async def asistente_user(db_session: AsyncSession, tenant_org: Organization) -> User:
    user = User(
        organization_id=tenant_org.id,
        username="carlos",
        email="carlos@example.com",
        hashed_password=hash_password("carlos123"),
        role=UserRole.asistente,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


def _login_json(username: str, password: str) -> dict:
    return {
        "organization_slug": TEST_ORG_SLUG,
        "username": username,
        "password": password,
    }


@pytest_asyncio.fixture()
async def admin_token(client: AsyncClient, admin_user: User) -> str:
    resp = await client.post("/api/auth/login", json=_login_json("admin", "admin123"))
    assert resp.status_code == 200
    return resp.json()["access_token"]


@pytest_asyncio.fixture()
async def contador_token(client: AsyncClient, contador_user: User) -> str:
    resp = await client.post("/api/auth/login", json=_login_json("maria", "maria123"))
    assert resp.status_code == 200
    return resp.json()["access_token"]


@pytest_asyncio.fixture()
async def asistente_token(client: AsyncClient, asistente_user: User) -> str:
    resp = await client.post("/api/auth/login", json=_login_json("carlos", "carlos123"))
    assert resp.status_code == 200
    return resp.json()["access_token"]


@pytest_asyncio.fixture()
async def platform_org(db_session: AsyncSession) -> Organization:
    org = Organization(
        name="Plataforma",
        slug="plataforma",
        plan_tier=PlanTier.empresarial,
    )
    db_session.add(org)
    await db_session.commit()
    await db_session.refresh(org)
    return org


@pytest_asyncio.fixture()
async def platform_admin_user(db_session: AsyncSession, platform_org: Organization) -> User:
    user = User(
        organization_id=platform_org.id,
        username="super",
        email="super@example.com",
        hashed_password=hash_password("super123"),
        role=UserRole.plataforma_admin,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest_asyncio.fixture()
async def platform_token(client: AsyncClient, platform_admin_user: User) -> str:
    resp = await client.post(
        "/api/auth/login",
        json={"organization_slug": "plataforma", "username": "super", "password": "super123"},
    )
    assert resp.status_code == 200
    return resp.json()["access_token"]
