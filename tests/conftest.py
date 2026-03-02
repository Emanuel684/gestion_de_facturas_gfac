"""
Test fixtures.

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
async def owner_user(db_session: AsyncSession) -> User:
    """Seed and return an owner-role user."""
    user = User(
        username="admin",
        email="admin@test.local",
        hashed_password=hash_password("admin123"),
        role=UserRole.owner,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest_asyncio.fixture()
async def member_user(db_session: AsyncSession) -> User:
    """Seed and return a member-role user."""
    user = User(
        username="alice",
        email="alice@test.local",
        hashed_password=hash_password("alice123"),
        role=UserRole.member,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest_asyncio.fixture()
async def owner_token(client: AsyncClient, owner_user: User) -> str:
    """Login as owner and return the bearer token."""
    resp = await client.post(
        "/api/auth/login", data={"username": "admin", "password": "admin123"}
    )
    assert resp.status_code == 200
    return resp.json()["access_token"]


@pytest_asyncio.fixture()
async def member_token(client: AsyncClient, member_user: User) -> str:
    """Login as member and return the bearer token."""
    resp = await client.post(
        "/api/auth/login", data={"username": "alice", "password": "alice123"}
    )
    assert resp.status_code == 200
    return resp.json()["access_token"]