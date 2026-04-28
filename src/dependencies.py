"""
FastAPI dependencies shared across routers.
"""
import logging

from fastapi import Depends, HTTPException, Request, status
from jose import JWTError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.billing import recompute_subscription_status
from src.auth import decode_access_token, is_token_revoked
from src.config import settings
from src.db import get_db
from src.models import Subscription, SubscriptionStatus, User, UserRole

logger = logging.getLogger(__name__)


async def get_current_user(
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> User:
    """Validate JWT and return the authenticated User."""
    credentials_exc = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    auth_header = request.headers.get("Authorization", "")
    token = ""
    if auth_header.startswith("Bearer "):
        token = auth_header[7:].strip()
    if not token:
        token = request.cookies.get(settings.jwt_cookie_name, "")
    if not token:
        raise credentials_exc

    try:
        payload = decode_access_token(token)
        if is_token_revoked(payload):
            raise credentials_exc
        user_id: str = payload.get("sub")
        if user_id is None:
            raise credentials_exc
    except JWTError:
        raise credentials_exc

    result = await db.execute(select(User).where(User.id == int(user_id)))
    user = result.scalar_one_or_none()
    if user is None or not user.is_active:
        raise credentials_exc
    return user


async def require_admin(current_user: User = Depends(get_current_user)) -> User:
    """Restrict access to users with the 'administrador' role."""
    if current_user.role != UserRole.administrador:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Se requiere rol de administrador",
        )
    return current_user


async def require_tenant_user(current_user: User = Depends(get_current_user)) -> User:
    """Tenant-only: facturas y usuarios de una organización cliente."""
    if current_user.role == UserRole.plataforma_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Los administradores de plataforma gestionan organizaciones, no datos de clientes.",
        )
    return current_user


async def require_active_tenant_user(
    current_user: User = Depends(require_tenant_user),
    db: AsyncSession = Depends(get_db),
) -> User:
    """Tenant user with active subscription or within grace period."""
    result = await db.execute(
        select(Subscription)
        .where(Subscription.organization_id == current_user.organization_id)
        .order_by(Subscription.id.desc())
    )
    subscription = result.scalars().first()
    if subscription is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="La organización no tiene suscripción activa",
        )
    recompute_subscription_status(subscription)
    await db.commit()
    if subscription.status not in (SubscriptionStatus.active, SubscriptionStatus.past_due):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Suscripción vencida. Regularice el pago para recuperar el acceso.",
        )
    return current_user


async def require_platform_admin(current_user: User = Depends(get_current_user)) -> User:
    if current_user.role != UserRole.plataforma_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Se requiere rol de administrador de plataforma",
        )
    return current_user
