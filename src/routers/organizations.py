"""
Organizations router — administradores de plataforma crean tenants (organizaciones).
"""
import logging

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth import hash_password
from src.db import get_db
from src.dependencies import require_platform_admin
from src.models import Organization, User, UserRole
from src.schemas import OrganizationCreate, OrganizationOut

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
