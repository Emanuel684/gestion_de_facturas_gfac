"""
Dashboard y reportes para administradores de plataforma (filtrado por organización)
y ranking de facturación por organización cliente.
"""
from __future__ import annotations

from datetime import date
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession

from src.db import get_db
from src.dependencies import require_platform_admin
from src.models import InvoiceStatus, Organization, User
from src.reporting.exports import build_invoices_pdf_bytes, build_invoices_xlsx_bytes, export_filename_prefix
from src.reporting.fetch import fetch_invoices_for_export
from src.reporting.scope import parse_date_range_bounds
from src.reporting.stats import compute_dashboard_stats, top_organizations_by_billing
from src.schemas import DashboardStatsOut, OrgBillingRankOut

router = APIRouter(prefix="/api/platform", tags=["platform"])

PLATFORM_SLUG = "plataforma"


@router.get("/dashboard", response_model=DashboardStatsOut)
async def platform_dashboard(
    organization_id: Annotated[int, Query(ge=1)],
    date_from: date | None = None,
    date_to: date | None = None,
    _: User = Depends(require_platform_admin),
    db: AsyncSession = Depends(get_db),
) -> DashboardStatsOut:
    org = await db.get(Organization, organization_id)
    if org is None or org.slug == PLATFORM_SLUG:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Organización no encontrada")
    d0, d1 = parse_date_range_bounds(date_from, date_to)
    return await compute_dashboard_stats(
        db,
        org.id,
        None,
        platform_scope=True,
        org_name=org.name,
        date_from=d0,
        date_to=d1,
    )


@router.get("/reports/export")
async def platform_export(
    organization_id: Annotated[int, Query(ge=1)],
    export_format: Annotated[Literal["xlsx", "pdf"], Query(alias="format")],
    date_from: date | None = None,
    date_to: date | None = None,
    status_filter: Annotated[InvoiceStatus | None, Query(alias="status")] = None,
    _: User = Depends(require_platform_admin),
    db: AsyncSession = Depends(get_db),
) -> Response:
    org = await db.get(Organization, organization_id)
    if org is None or org.slug == PLATFORM_SLUG:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Organización no encontrada")
    d0, d1 = parse_date_range_bounds(date_from, date_to)
    invoices = await fetch_invoices_for_export(
        db,
        org.id,
        None,
        platform_scope=True,
        date_from=d0,
        date_to=d1,
        status_filter=status_filter,
    )
    prefix = export_filename_prefix(org.slug)
    if export_format == "xlsx":
        data = build_invoices_xlsx_bytes(invoices, sheet_title="Facturas")
        fn = f"{prefix}_facturas.xlsx"
        return Response(
            content=data,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": f'attachment; filename="{fn}"'},
        )
    title = f"Reporte de facturas — {org.name}"
    sub = f"Periodo: {date_from.isoformat() if date_from else 'inicio'} → {date_to.isoformat() if date_to else 'hoy'}"
    data = build_invoices_pdf_bytes(invoices, title=title, subtitle=sub)
    fn = f"{prefix}_facturas.pdf"
    return Response(
        content=data,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{fn}"'},
    )


@router.get("/analytics/top-organizations", response_model=list[OrgBillingRankOut])
async def platform_top_organizations(
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    date_from: date | None = None,
    date_to: date | None = None,
    _: User = Depends(require_platform_admin),
    db: AsyncSession = Depends(get_db),
) -> list[OrgBillingRankOut]:
    d0, d1 = parse_date_range_bounds(date_from, date_to)
    return await top_organizations_by_billing(
        db,
        limit=limit,
        date_from=d0,
        date_to=d1,
        exclude_org_slugs={PLATFORM_SLUG},
    )
