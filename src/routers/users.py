"""
Users router — allows listing users (for task assignment UI).
"""
from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.db import get_db
from src.dependencies import get_current_user
from src.models import User
from src.schemas import UserOut

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
    """List all active users. Used by the frontend for task assignment."""
    result = await db.execute(select(User).where(User.is_active == True).order_by(User.username))
    users = result.scalars().all()
    return [UserOut.model_validate(u) for u in users]
