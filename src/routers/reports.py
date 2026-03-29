"""
Reportes y dashboard para usuarios de una organización (tenant).
"""
from __future__ import annotations

from datetime import date
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Query
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession

from src.db import get_db
from src.dependencies import require_active_tenant_user
from src.models import InvoiceStatus, Organization, User
from src.reporting.exports import build_invoices_pdf_bytes, build_invoices_xlsx_bytes, export_filename_prefix
from src.reporting.fetch import fetch_invoices_for_export
from src.reporting.scope import parse_date_range_bounds
from src.reporting.stats import compute_dashboard_stats
from src.schemas import DashboardStatsOut

router = APIRouter(prefix="/api/reports", tags=["reports"])


@router.get("/dashboard", response_model=DashboardStatsOut)
async def tenant_dashboard(
    date_from: date | None = None,
    date_to: date | None = None,
    current_user: User = Depends(require_active_tenant_user),
    db: AsyncSession = Depends(get_db),
) -> DashboardStatsOut:
    d0, d1 = parse_date_range_bounds(date_from, date_to)
    return await compute_dashboard_stats(
        db,
        current_user.organization_id,
        current_user,
        platform_scope=False,
        org_name=None,
        date_from=d0,
        date_to=d1,
    )


@router.get("/export")
async def tenant_export(
    export_format: Annotated[Literal["xlsx", "pdf"], Query(alias="format")],
    date_from: date | None = None,
    date_to: date | None = None,
    status_filter: Annotated[InvoiceStatus | None, Query(alias="status")] = None,
    current_user: User = Depends(require_active_tenant_user),
    db: AsyncSession = Depends(get_db),
) -> Response:
    d0, d1 = parse_date_range_bounds(date_from, date_to)
    org = await db.get(Organization, current_user.organization_id)
    slug = org.slug if org else "org"
    invoices = await fetch_invoices_for_export(
        db,
        current_user.organization_id,
        current_user,
        platform_scope=False,
        date_from=d0,
        date_to=d1,
        status_filter=status_filter,
    )
    prefix = export_filename_prefix(slug)
    if export_format == "xlsx":
        data = build_invoices_xlsx_bytes(invoices, sheet_title="Facturas")
        fn = f"{prefix}_facturas.xlsx"
        return Response(
            content=data,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": f'attachment; filename="{fn}"'},
        )
    title = f"Reporte de facturas — {org.name if org else ''}"
    sub = f"Periodo: {date_from.isoformat() if date_from else 'inicio'} → {date_to.isoformat() if date_to else 'hoy'}"
    data = build_invoices_pdf_bytes(invoices, title=title, subtitle=sub)
    fn = f"{prefix}_facturas.pdf"
    return Response(
        content=data,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{fn}"'},
    )
