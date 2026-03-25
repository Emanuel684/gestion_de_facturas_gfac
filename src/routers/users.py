"""
Users router — user management and listing for the SGF system.

Endpoints:
  GET    /api/users/me    — current user profile
  GET    /api/users       — list active users in the same organization (tenant)
  POST   /api/users       — create user (administrador del tenant)
  DELETE /api/users/{id}  — delete user (admin; scoped to organization)
"""
import logging

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.auth import hash_password
from src.db import get_db
from src.dependencies import get_current_user, require_admin, require_tenant_user
from src.models import Invoice, InvoiceAssignee, User, UserRole
from src.schemas import UserCreate, UserOut, user_to_out

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/users", tags=["users"])


@router.get("/me", response_model=UserOut)
async def get_me(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> UserOut:
    """Return the currently authenticated user's profile."""
    result = await db.execute(
        select(User).options(selectinload(User.organization)).where(User.id == current_user.id)
    )
    user = result.scalar_one()
    return user_to_out(user)


@router.get("", response_model=list[UserOut])
async def list_users(
    current_user: User = Depends(require_tenant_user),
    db: AsyncSession = Depends(get_db),
) -> list[UserOut]:
    """List active users in the same organization (for invoice assignment)."""
    result = await db.execute(
        select(User)
        .options(selectinload(User.organization))
        .where(
            User.organization_id == current_user.organization_id,
            User.is_active == True,  # noqa: E712
        )
        .order_by(User.username)
    )
    users = result.scalars().all()
    return [user_to_out(u) for u in users]


@router.post("", response_model=UserOut, status_code=status.HTTP_201_CREATED)
async def create_user(
    payload: UserCreate,
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> UserOut:
    """Create a user in the current organization (solo administrador de empresa)."""
    result = await db.execute(
        select(User).where(
            User.organization_id == current_user.organization_id,
            User.username == payload.username,
        )
    )
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"El nombre de usuario '{payload.username}' ya está en uso en esta organización",
        )

    result = await db.execute(
        select(User).where(
            User.organization_id == current_user.organization_id,
            User.email == payload.email,
        )
    )
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"El email '{payload.email}' ya está en uso en esta organización",
        )

    user = User(
        organization_id=current_user.organization_id,
        username=payload.username,
        email=payload.email,
        hashed_password=hash_password(payload.password),
        role=payload.role,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    result = await db.execute(
        select(User).options(selectinload(User.organization)).where(User.id == user.id)
    )
    user = result.scalar_one()

    logger.info(
        "User id=%d (%s) created by admin id=%d in org id=%d",
        user.id,
        user.username,
        current_user.id,
        current_user.organization_id,
    )
    return user_to_out(user)


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(
    user_id: int,
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> None:
    """Delete a user in the same organization; removes their invoices as creator."""
    if user_id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No puede eliminar su propia cuenta",
        )

    result = await db.execute(
        select(User).where(
            User.id == user_id,
            User.organization_id == current_user.organization_id,
        )
    )
    target = result.scalar_one_or_none()
    if target is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Usuario no encontrado",
        )

    if target.role == UserRole.administrador:
        n_admins = await db.execute(
            select(func.count()).select_from(User).where(
                User.role == UserRole.administrador,
                User.organization_id == target.organization_id,
            )
        )
        if n_admins.scalar_one() <= 1:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No puede eliminar el último administrador de la organización",
            )

    created_invoice_ids = select(Invoice.id).where(Invoice.creator_id == user_id)

    await db.execute(delete(InvoiceAssignee).where(InvoiceAssignee.user_id == user_id))
    await db.execute(
        delete(InvoiceAssignee).where(InvoiceAssignee.invoice_id.in_(created_invoice_ids))
    )
    await db.execute(delete(Invoice).where(Invoice.creator_id == user_id))
    await db.execute(delete(User).where(User.id == user_id))
    await db.commit()

    logger.info(
        "User id=%d (%s) deleted by admin id=%d (org id=%d)",
        user_id,
        target.username,
        current_user.id,
        current_user.organization_id,
    )
