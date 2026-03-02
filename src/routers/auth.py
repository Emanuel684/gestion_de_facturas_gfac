"""
Authentication router.

POST /api/auth/login  — accepts form data (username + password) and returns JWT.
"""
import logging

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth import create_access_token, verify_password
from src.db import get_db
from src.models import User
from src.schemas import TokenResponse

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/login", response_model=TokenResponse)
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db),
) -> TokenResponse:
    """Authenticate a user and return a JWT access token."""
    result = await db.execute(select(User).where(User.username == form_data.username))
    user: User | None = result.scalar_one_or_none()

    if not user or not verify_password(form_data.password, user.hashed_password):
        logger.warning("Failed login attempt for username=%r", form_data.username)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is disabled",
        )

    token = create_access_token(subject=user.id, role=user.role.value)
    logger.info("User id=%d logged in successfully", user.id)
    return TokenResponse(access_token=token)
