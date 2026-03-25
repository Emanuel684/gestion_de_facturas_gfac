"""Perfil fiscal del tenant (preparación DIAN)."""
import logging

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.db import get_db
from src.dependencies import require_admin, require_active_tenant_user
from src.dian.validation import validate_dv_format, validate_nit_format
from src.models import OrganizationFiscalProfile, TaxRegime, User
from src.schemas import FiscalProfileOut, FiscalProfileUpdate

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/fiscal", tags=["fiscal"])


@router.get("/profile", response_model=FiscalProfileOut)
async def get_fiscal_profile(
    current_user: User = Depends(require_active_tenant_user),
    db: AsyncSession = Depends(get_db),
) -> FiscalProfileOut:
    r = await db.execute(
        select(OrganizationFiscalProfile).where(
            OrganizationFiscalProfile.organization_id == current_user.organization_id
        )
    )
    fp = r.scalar_one_or_none()
    if fp is None:
        return FiscalProfileOut(
            id=None,
            organization_id=current_user.organization_id,
            nit="",
            dv="",
            business_name="",
            trade_name=None,
            department_code=None,
            city_code=None,
            tax_regime=TaxRegime.responsable_iva,
            invoice_prefix_default=None,
            updated_at=None,
        )
    return FiscalProfileOut.model_validate(fp)


@router.put("/profile", response_model=FiscalProfileOut)
async def put_fiscal_profile(
    payload: FiscalProfileUpdate,
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> FiscalProfileOut:
    try:
        validate_nit_format(payload.nit)
        validate_dv_format(payload.dv)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e))

    r = await db.execute(
        select(OrganizationFiscalProfile).where(
            OrganizationFiscalProfile.organization_id == current_user.organization_id
        )
    )
    fp = r.scalar_one_or_none()
    if fp is None:
        fp = OrganizationFiscalProfile(organization_id=current_user.organization_id)
        db.add(fp)

    fp.nit = payload.nit.strip()
    fp.dv = payload.dv.strip()
    fp.business_name = payload.business_name.strip()
    fp.trade_name = payload.trade_name.strip() if payload.trade_name else None
    fp.department_code = payload.department_code
    fp.city_code = payload.city_code
    fp.tax_regime = payload.tax_regime
    fp.invoice_prefix_default = payload.invoice_prefix_default

    await db.commit()
    await db.refresh(fp)
    logger.info("Fiscal profile updated for org id=%d", current_user.organization_id)
    return FiscalProfileOut.model_validate(fp)
