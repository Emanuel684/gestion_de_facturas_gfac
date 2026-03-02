"""
FastAPI application entry point.

On startup:
  1. Creates all DB tables (SQLAlchemy DDL).
  2. Seeds two default users if they don't exist:
     - admin / admin123  (role: owner)
     - alice  / alice123 (role: member)
"""
import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import select

from src.auth import hash_password
from src.config import settings
from src.db import engine, Base
from src.models import User, UserRole
from src.routers import auth, tasks, users

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(name)s — %(message)s",
)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Task Manager API",
    description="Production-ready Task Manager with JWT auth and role-based access.",
    version="1.0.0",
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
app.include_router(tasks.router)
app.include_router(users.router)


# ── Startup ───────────────────────────────────────────────────────────────────
@app.on_event("startup")
async def on_startup() -> None:
    # Create tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)    
        logger.info("Database tables created / verified.")

    # Seed default users
    from src.db import AsyncSessionLocal

    async with AsyncSessionLocal() as db:
        seed_users = [
            {"username": "admin", "email": "admin@taskmanager.local", "password": "admin123", "role": UserRole.owner},
            {"username": "alice", "email": "alice@taskmanager.local", "password": "alice123", "role": UserRole.member},
            {"username": "bob",   "email": "bob@taskmanager.local",   "password": "bob123",   "role": UserRole.member},
        ]
        for data in seed_users:
            result = await db.execute(select(User).where(User.username == data["username"]))
            if not result.scalar_one_or_none():                    
                db.add(
                    User(
                        username=data["username"],
                        email=data["email"],
                        hashed_password=hash_password(data["password"]),
                        role=data["role"],
                    )
                )
                logger.info("Seeded user: %s (%s)", data["username"], data["role"].value)
        await db.commit()


# ── Health ────────────────────────────────────────────────────────────────────
@app.get("/health", tags=["health"])
async def health() -> dict:
    return {"status": "ok"}


@app.get("/", tags=["health"])
async def root() -> dict:
    return {"message": "Task Manager API", "docs": "/docs"}
