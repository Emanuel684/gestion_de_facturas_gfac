"""Carga de facturas para exportación."""
from __future__ import annotations

from sqlalchemy import Select, and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models import Invoice, InvoiceStatus
from src.reporting.scope import append_date_range, invoice_visibility_conditions


def invoices_export_select(
    org_id: int,
    user,
    *,
    platform_scope: bool,
    date_from,
    date_to,
    status_filter: InvoiceStatus | None,
) -> Select[tuple[Invoice]]:
    conds = invoice_visibility_conditions(org_id, user, platform_scope=platform_scope)
    append_date_range(conds, date_from, date_to)
    if status_filter is not None:
        conds.append(Invoice.status == status_filter)
    return (
        select(Invoice)
        .where(and_(*conds))
        .order_by(Invoice.created_at.desc())
    )


async def fetch_invoices_for_export(
    db: AsyncSession,
    org_id: int,
    user,
    *,
    platform_scope: bool,
    date_from,
    date_to,
    status_filter: InvoiceStatus | None,
    limit: int = 10_000,
) -> list[Invoice]:
    stmt = invoices_export_select(
        org_id, user, platform_scope=platform_scope, date_from=date_from, date_to=date_to, status_filter=status_filter
    ).limit(limit)
    result = await db.execute(stmt)
    return list(result.scalars().all())
