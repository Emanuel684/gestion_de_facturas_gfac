import os
import ssl
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from src.config import settings


def _strip_sslmode_from_url(url: str) -> str:
    """asyncpg no usa sslmode= de libpq; el SSL se pasa en connect_args."""
    parsed = urlparse(url)
    if not parsed.query:
        return url
    pairs = [(k, v) for k, v in parse_qsl(parsed.query, keep_blank_values=True) if k.lower() != "sslmode"]
    new_query = urlencode(pairs)
    return urlunparse(parsed._replace(query=new_query))


def _connect_args_for_database_url(url: str) -> dict:
    """TLS para Postgres gestionado (Render, Neon, etc.). Desactivar con DATABASE_SSL=false."""
    if os.getenv("DATABASE_SSL", "true").lower() in ("0", "false", "no"):
        return {}
    try:
        host = urlparse(url).hostname
    except Exception:
        host = None
    local = {"localhost", "127.0.0.1", "::1", "db", "postgres"}
    if not host or host in local:
        return {}
    return {"ssl": ssl.create_default_context()}


_db_url = _strip_sslmode_from_url(settings.database_url)

engine = create_async_engine(
    _db_url,
    echo=False,
    pool_pre_ping=True,
    connect_args=_connect_args_for_database_url(_db_url),
)

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


class Base(DeclarativeBase):
    """Declarative base for all ORM models."""
    pass


async def get_db() -> AsyncSession:
    """Dependency that yields a DB session and closes it after the request."""
    async with AsyncSessionLocal() as session:
        yield session
