"""
Authentication router.

POST /api/auth/login — JSON body: organization_slug, username, password → JWT.
"""
import logging
import time

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth import create_access_token, revoke_token, verify_password
from src.config import settings
from src.db import get_db
from src.models import Organization, User
from src.schemas import LoginJSON, TokenResponse

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/auth", tags=["auth"])
_LOGIN_ATTEMPTS: dict[str, list[float]] = {}


def _rate_limit_key(request: Request, slug: str, username: str) -> str:
    ip = request.client.host if request.client else "unknown"
    return f"{ip}|{slug}|{username.strip().lower()}"


def _enforce_login_rate_limit(key: str) -> None:
    now = time.time()
    window = settings.login_rate_limit_window_seconds
    bucket = [t for t in _LOGIN_ATTEMPTS.get(key, []) if now - t <= window]
    _LOGIN_ATTEMPTS[key] = bucket
    if len(bucket) >= settings.login_rate_limit_max_attempts:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Demasiados intentos de inicio de sesión. Intente nuevamente en unos minutos.",
        )


def _register_failed_attempt(key: str) -> None:
    now = time.time()
    _LOGIN_ATTEMPTS.setdefault(key, []).append(now)


def _clear_attempts(key: str) -> None:
    _LOGIN_ATTEMPTS.pop(key, None)


@router.post("/login", response_model=TokenResponse)
async def login(
    body: LoginJSON,
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db),
) -> TokenResponse:
    """Authenticate within an organization and return a JWT access token."""
    slug = body.organization_slug.strip().lower()
    login_key = _rate_limit_key(request, slug, body.username)
    _enforce_login_rate_limit(login_key)
    result_org = await db.execute(
        select(Organization).where(
            Organization.slug == slug,
            Organization.is_active == True,  # noqa: E712
        )
    )
    org: Organization | None = result_org.scalar_one_or_none()
    if org is None:
        logger.warning("Login failed: unknown org slug=%r", slug)
        _register_failed_attempt(login_key)
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
        _register_failed_attempt(login_key)
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

    _clear_attempts(login_key)
    token = create_access_token(
        subject=user.id,
        role=user.role.value,
        organization_id=user.organization_id,
    )
    response.set_cookie(
        key=settings.jwt_cookie_name,
        value=token,
        httponly=True,
        secure=settings.is_production,
        samesite="lax",
        max_age=settings.access_token_expire_minutes * 60,
        path="/",
    )
    logger.info("User id=%d logged in successfully (org_id=%d)", user.id, user.organization_id)
    return TokenResponse(access_token=token)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(request: Request, response: Response) -> None:
    auth_header = request.headers.get("Authorization", "")
    token = request.cookies.get(settings.jwt_cookie_name, "")
    if not token and auth_header.startswith("Bearer "):
        token = auth_header[7:].strip()
    if token:
        revoke_token(token)
    response.delete_cookie(settings.jwt_cookie_name, path="/")
