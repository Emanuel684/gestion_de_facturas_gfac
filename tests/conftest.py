"""
Test fixtures — Sistema de Gestión de Facturas (SGF).

Uses an in-memory SQLite database (via aiosqlite) so tests run without a
real Postgres instance.  Each test function gets a fresh DB.
"""
import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from src.auth import hash_password
from src.db import Base, get_db
from src.main import app
from src.models import User, UserRole

TEST_DB_URL = "sqlite+aiosqlite:///:memory:"


@pytest_asyncio.fixture()
async def db_session():
    """Create a fresh in-memory DB and yield a session."""
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
    """AsyncClient wired to the FastAPI app with the test DB session."""

    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        yield ac

    app.dependency_overrides.clear()


@pytest_asyncio.fixture()
async def admin_user(db_session: AsyncSession) -> User:
    """Seed and return an administrador-role user."""
    user = User(
        username="admin",
        email="admin@sgf.local",
        hashed_password=hash_password("admin123"),
        role=UserRole.administrador,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest_asyncio.fixture()
async def contador_user(db_session: AsyncSession) -> User:
    """Seed and return a contador-role user."""
    user = User(
        username="maria",
        email="maria@sgf.local",
        hashed_password=hash_password("maria123"),
        role=UserRole.contador,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest_asyncio.fixture()
async def asistente_user(db_session: AsyncSession) -> User:
    """Seed and return an asistente-role user."""
    user = User(
        username="carlos",
        email="carlos@sgf.local",
        hashed_password=hash_password("carlos123"),
        role=UserRole.asistente,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest_asyncio.fixture()
async def admin_token(client: AsyncClient, admin_user: User) -> str:
    """Login as administrador and return the bearer token."""
    resp = await client.post(
        "/api/auth/login", data={"username": "admin", "password": "admin123"}
    )
    assert resp.status_code == 200
    return resp.json()["access_token"]


@pytest_asyncio.fixture()
async def contador_token(client: AsyncClient, contador_user: User) -> str:
    """Login as contador and return the bearer token."""
    resp = await client.post(
        "/api/auth/login", data={"username": "maria", "password": "maria123"}
    )
    assert resp.status_code == 200
    return resp.json()["access_token"]


@pytest_asyncio.fixture()
async def asistente_token(client: AsyncClient, asistente_user: User) -> str:
    """Login as asistente and return the bearer token."""
    resp = await client.post(
        "/api/auth/login", data={"username": "carlos", "password": "carlos123"}
    )
    assert resp.status_code == 200
    return resp.json()["access_token"]