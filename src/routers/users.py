"""
Users router — user management and listing for the SGF system.

Endpoints:
  GET  /api/users/me    — current user profile
  GET  /api/users       — list all active users (authenticated)
  POST /api/users       — create a new user (administrador only)
"""
import logging

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth import hash_password
from src.db import get_db
from src.dependencies import get_current_user, require_admin
from src.models import User
from src.schemas import UserCreate, UserOut

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/users", tags=["users"])


@router.get("/me", response_model=UserOut)
async def get_me(current_user: User = Depends(get_current_user)) -> UserOut:
    """Return the currently authenticated user's profile."""
    return UserOut.model_validate(current_user)


@router.get("", response_model=list[UserOut])
async def list_users(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[UserOut]:
    """List all active users. Used by the frontend for invoice assignment."""
    result = await db.execute(select(User).where(User.is_active == True).order_by(User.username))
    users = result.scalars().all()
    return [UserOut.model_validate(u) for u in users]


@router.post("", response_model=UserOut, status_code=status.HTTP_201_CREATED)
async def create_user(
    payload: UserCreate,
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> UserOut:
    """
    Create a new user. Only administradores can create users.
    """
    # Check for duplicate username
    result = await db.execute(select(User).where(User.username == payload.username))
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"El nombre de usuario '{payload.username}' ya está en uso",
        )

    # Check for duplicate email
    result = await db.execute(select(User).where(User.email == payload.email))
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"El email '{payload.email}' ya está en uso",
        )

    user = User(
        username=payload.username,
        email=payload.email,
        hashed_password=hash_password(payload.password),
        role=payload.role,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)

    logger.info(
        "User id=%d (%s) created by admin id=%d",
        user.id, user.username, current_user.id,
    )
    return UserOut.model_validate(user)
