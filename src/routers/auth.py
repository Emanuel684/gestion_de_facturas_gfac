"""
Authentication router.

POST /api/auth/login — JSON body: organization_slug, username, password → JWT.
"""
import logging

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth import create_access_token, verify_password
from src.db import get_db
from src.models import Organization, User
from src.schemas import LoginJSON, TokenResponse

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/login", response_model=TokenResponse)
async def login(
    body: LoginJSON,
    db: AsyncSession = Depends(get_db),
) -> TokenResponse:
    """Authenticate within an organization and return a JWT access token."""
    slug = body.organization_slug.strip().lower()
    result_org = await db.execute(
        select(Organization).where(
            Organization.slug == slug,
            Organization.is_active == True,  # noqa: E712
        )
    )
    org: Organization | None = result_org.scalar_one_or_none()
    if org is None:
        logger.warning("Login failed: unknown org slug=%r", slug)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Organización o credenciales incorrectas",
            headers={"WWW-Authenticate": "Bearer"},
        )

    result_user = await db.execute(
        select(User).where(
            User.organization_id == org.id,
            User.username == body.username,
        )
    )
    user: User | None = result_user.scalar_one_or_none()

    if not user or not verify_password(body.password, user.hashed_password):
        logger.warning("Failed login org=%r username=%r", slug, body.username)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Organización o credenciales incorrectas",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cuenta deshabilitada",
        )

    token = create_access_token(
        subject=user.id,
        role=user.role.value,
        organization_id=user.organization_id,
    )
    logger.info("User id=%d logged in successfully (org_id=%d)", user.id, user.organization_id)
    return TokenResponse(access_token=token)
