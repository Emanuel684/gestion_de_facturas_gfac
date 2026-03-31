"""
Organizations router — administradores de plataforma crean tenants (organizaciones).
"""
import logging
from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.auth import hash_password
from src.billing import now_utc
from src.db import get_db
from src.dependencies import require_platform_admin
from src.models import (
    CheckoutSession,
    Invoice,
    InvoiceAssignee,
    InvoiceEvent,
    Organization,
    OrganizationFiscalProfile,
    Payment,
    Subscription,
    SubscriptionStatus,
    User,
    UserRole,
)
from src.schemas import (
    OrganizationCreate,
    OrganizationOut,
    OrganizationUpdate,
    PlatformInvoiceSummaryOut,
    UserOut,
    UserUpdate,
    user_to_out,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/organizations", tags=["organizations"])

PLATFORM_SLUG = "plataforma"


@router.get("", response_model=list[OrganizationOut])
async def list_organizations(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_platform_admin),
) -> list[OrganizationOut]:
    """Lista organizaciones cliente (no incluye la org reservada de plataforma)."""
    result = await db.execute(
        select(Organization)
        .where(Organization.slug != PLATFORM_SLUG)
        .order_by(Organization.name)
    )
    orgs = result.scalars().all()
    return [OrganizationOut.model_validate(o) for o in orgs]


@router.post("", response_model=OrganizationOut, status_code=status.HTTP_201_CREATED)
async def create_organization(
    payload: OrganizationCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_platform_admin),
) -> OrganizationOut:
    """Crea una organización y su primer usuario administrador."""
    dup = await db.execute(select(Organization).where(Organization.slug == payload.slug))
    if dup.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Ya existe una organización con slug '{payload.slug}'",
        )

    org = Organization(
        name=payload.name,
        slug=payload.slug,
        plan_tier=payload.plan_tier,
    )
    db.add(org)
    await db.flush()

    u_dup = await db.execute(
        select(User).where(
            User.organization_id == org.id,
            User.username == payload.admin_username.strip(),
        )
    )
    if u_dup.scalar_one_or_none():
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Usuario administrador duplicado",
        )

    e_dup = await db.execute(
        select(User).where(User.organization_id == org.id, User.email == payload.admin_email)
    )
    if e_dup.scalar_one_or_none():
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email ya registrado en la organización",
        )

    admin = User(
        organization_id=org.id,
        username=payload.admin_username.strip(),
        email=str(payload.admin_email),
        hashed_password=hash_password(payload.admin_password),
        role=UserRole.administrador,
    )
    db.add(admin)
    now = now_utc()
    db.add(
        Subscription(
            organization_id=org.id,
            plan_tier=payload.plan_tier,
            status=SubscriptionStatus.past_due,
            next_due_date=now,
            grace_expires_at=now + timedelta(days=10),
        )
    )
    await db.commit()
    await db.refresh(org)

    logger.info(
        "Organization id=%d slug=%s created by platform_admin id=%d (admin user %s)",
        org.id,
        org.slug,
        current_user.id,
        admin.username,
    )
    return OrganizationOut.model_validate(org)


@router.get("/{organization_id}", response_model=OrganizationOut)
async def get_organization(
    organization_id: int,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_platform_admin),
) -> OrganizationOut:
    result = await db.execute(select(Organization).where(Organization.id == organization_id))
    org = result.scalar_one_or_none()
    if not org or org.slug == PLATFORM_SLUG:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Organización no encontrada")
    return OrganizationOut.model_validate(org)


@router.patch("/{organization_id}", response_model=OrganizationOut)
async def update_organization(
    organization_id: int,
    payload: OrganizationUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_platform_admin),
) -> OrganizationOut:
    result = await db.execute(select(Organization).where(Organization.id == organization_id))
    org = result.scalar_one_or_none()
    if not org or org.slug == PLATFORM_SLUG:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Organización no encontrada")

    if payload.slug is not None and payload.slug != org.slug:
        dup = await db.execute(
            select(Organization.id).where(
                Organization.slug == payload.slug,
                Organization.id != org.id,
            )
        )
        if dup.scalar_one_or_none() is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Ya existe una organización con slug '{payload.slug}'",
            )

    if payload.name is not None:
        org.name = payload.name
    if payload.slug is not None:
        org.slug = payload.slug
    if payload.plan_tier is not None:
        org.plan_tier = payload.plan_tier

    await db.commit()
    await db.refresh(org)

    logger.info(
        "Organization id=%d updated by platform_admin id=%d",
        org.id,
        current_user.id,
    )
    return OrganizationOut.model_validate(org)


@router.get("/{organization_id}/users", response_model=list[UserOut])
async def list_organization_users(
    organization_id: int,
    include_inactive: bool = Query(default=False),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_platform_admin),
) -> list[UserOut]:
    org_res = await db.execute(select(Organization).where(Organization.id == organization_id))
    org = org_res.scalar_one_or_none()
    if not org or org.slug == PLATFORM_SLUG:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Organización no encontrada")

    stmt = (
        select(User)
        .options(selectinload(User.organization))
        .where(User.organization_id == organization_id)
        .order_by(User.is_active.desc(), User.username)
    )
    if not include_inactive:
        stmt = stmt.where(User.is_active == True)  # noqa: E712
    users = (await db.execute(stmt)).scalars().all()
    return [user_to_out(u) for u in users]


@router.put("/{organization_id}/users/{user_id}", response_model=UserOut)
async def update_organization_user(
    organization_id: int,
    user_id: int,
    payload: UserUpdate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_platform_admin),
) -> UserOut:
    result = await db.execute(
        select(User)
        .options(selectinload(User.organization))
        .where(
            User.id == user_id,
            User.organization_id == organization_id,
        )
    )
    target = result.scalar_one_or_none()
    if target is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Usuario no encontrado")

    new_role = payload.role if payload.role is not None else target.role
    new_is_active = payload.is_active if payload.is_active is not None else target.is_active
    if target.role == UserRole.administrador and (new_role != UserRole.administrador or new_is_active is False):
        n_admins = await db.execute(
            select(func.count()).select_from(User).where(
                User.role == UserRole.administrador,
                User.organization_id == target.organization_id,
                User.is_active == True,  # noqa: E712
                User.id != target.id,
            )
        )
        if n_admins.scalar_one() <= 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No puede deshabilitar o cambiar el último administrador de la organización",
            )

    if payload.username is not None and payload.username != target.username:
        r = await db.execute(
            select(User.id).where(
                User.organization_id == organization_id,
                User.username == payload.username,
                User.id != target.id,
            )
        )
        if r.scalar_one_or_none() is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"El nombre de usuario '{payload.username}' ya está en uso en esta organización",
            )

    if payload.email is not None and payload.email != target.email:
        r = await db.execute(
            select(User.id).where(
                User.organization_id == organization_id,
                User.email == payload.email,
                User.id != target.id,
            )
        )
        if r.scalar_one_or_none() is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"El email '{payload.email}' ya está en uso en esta organización",
            )

    if payload.username is not None:
        target.username = payload.username
    if payload.email is not None:
        target.email = payload.email
    if payload.password is not None:
        target.hashed_password = hash_password(payload.password)
    if payload.role is not None:
        target.role = payload.role
    if payload.is_active is not None:
        target.is_active = payload.is_active

    await db.commit()
    await db.refresh(target)
    r2 = await db.execute(
        select(User).options(selectinload(User.organization)).where(User.id == target.id)
    )
    target = r2.scalar_one()
    return user_to_out(target)


@router.delete("/{organization_id}/users/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_organization_user(
    organization_id: int,
    user_id: int,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_platform_admin),
) -> None:
    result = await db.execute(
        select(User).where(
            User.id == user_id,
            User.organization_id == organization_id,
        )
    )
    target = result.scalar_one_or_none()
    if target is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Usuario no encontrado")
    if not target.is_active:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Usuario ya deshabilitado")
    if target.role == UserRole.administrador:
        n_admins = await db.execute(
            select(func.count()).select_from(User).where(
                User.role == UserRole.administrador,
                User.organization_id == target.organization_id,
                User.is_active == True,  # noqa: E712
                User.id != target.id,
            )
        )
        if n_admins.scalar_one() <= 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No puede eliminar el último administrador de la organización",
            )
    target.is_active = False
    await db.commit()


@router.get("/{organization_id}/invoices", response_model=list[PlatformInvoiceSummaryOut])
async def list_organization_invoices(
    organization_id: int,
    status_filter: str | None = Query(default=None, alias="status"),
    supplier: str | None = Query(default=None),
    limit: int = Query(default=200, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_platform_admin),
) -> list[PlatformInvoiceSummaryOut]:
    org_res = await db.execute(select(Organization).where(Organization.id == organization_id))
    org = org_res.scalar_one_or_none()
    if not org or org.slug == PLATFORM_SLUG:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Organización no encontrada")

    stmt = select(Invoice).where(Invoice.organization_id == organization_id)
    if status_filter:
        stmt = stmt.where(Invoice.status == status_filter)
    if supplier:
        stmt = stmt.where(Invoice.supplier.ilike(f"%{supplier.strip()}%"))
    stmt = stmt.order_by(Invoice.created_at.desc()).limit(limit)

    invoices = (await db.execute(stmt)).scalars().all()
    return [PlatformInvoiceSummaryOut.model_validate(i) for i in invoices]


async def _delete_organization_cascade(org_id: int, db: AsyncSession) -> None:
    """Elimina todos los datos ligados a la organización antes de borrarla (FK sin CASCADE en BD)."""
    inv_ids_subq = select(Invoice.id).where(Invoice.organization_id == org_id)

    await db.execute(delete(InvoiceEvent).where(InvoiceEvent.organization_id == org_id))
    await db.execute(delete(InvoiceAssignee).where(InvoiceAssignee.invoice_id.in_(inv_ids_subq)))
    await db.execute(delete(Invoice).where(Invoice.organization_id == org_id))
    await db.execute(delete(Payment).where(Payment.organization_id == org_id))
    await db.execute(delete(CheckoutSession).where(CheckoutSession.organization_id == org_id))
    await db.execute(delete(Subscription).where(Subscription.organization_id == org_id))
    await db.execute(delete(OrganizationFiscalProfile).where(OrganizationFiscalProfile.organization_id == org_id))
    await db.execute(delete(User).where(User.organization_id == org_id))
    await db.execute(delete(Organization).where(Organization.id == org_id))


@router.delete("/{organization_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_organization(
    organization_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_platform_admin),
) -> None:
    """Elimina una organización cliente y todos sus datos (usuarios, facturas, facturación, etc.)."""
    result = await db.execute(select(Organization).where(Organization.id == organization_id))
    org = result.scalar_one_or_none()
    if not org:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Organización no encontrada")
    if org.slug == PLATFORM_SLUG:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No se puede eliminar la organización reservada de la plataforma",
        )

    await _delete_organization_cascade(org.id, db)
    await db.commit()

    logger.info(
        "Organization id=%d slug=%s deleted by platform_admin id=%d",
        organization_id,
        org.slug,
        current_user.id,
    )
