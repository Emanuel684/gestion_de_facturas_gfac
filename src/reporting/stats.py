"""Agregados para dashboards."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from decimal import Decimal

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models import Invoice, InvoiceStatus, Organization
from src.reporting.scope import append_date_range, invoice_visibility_conditions
from src.schemas import DashboardStatsOut, MonthlySeriesPoint, OrgBillingRankOut, StatusAmounts, StatusCounts


async def compute_dashboard_stats(
    db: AsyncSession,
    org_id: int,
    user,
    *,
    platform_scope: bool,
    org_name: str | None,
    date_from: datetime | None,
    date_to: datetime | None,
) -> DashboardStatsOut:
    conds = invoice_visibility_conditions(org_id, user, platform_scope=platform_scope)
    append_date_range(conds, date_from, date_to)

    # Por estado: conteo y suma de montos
    stmt = (
        select(Invoice.status, func.count(Invoice.id), func.coalesce(func.sum(Invoice.amount), 0))
        .where(and_(*conds))
        .group_by(Invoice.status)
    )
    result = await db.execute(stmt)
    rows = result.all()

    counts = StatusCounts()
    amounts = StatusAmounts()
    total_n = 0
    total_amt = Decimal("0")
    for st, cnt, sm in rows:
        total_n += int(cnt)
        amt = sm if isinstance(sm, Decimal) else Decimal(str(sm))
        total_amt += amt
        if st == InvoiceStatus.pendiente:
            counts.pendiente = int(cnt)
            amounts.pendiente = amt
        elif st == InvoiceStatus.pagada:
            counts.pagada = int(cnt)
            amounts.pagada = amt
        elif st == InvoiceStatus.vencida:
            counts.vencida = int(cnt)
            amounts.vencida = amt

    # Serie mensual (PostgreSQL)
    conds_m = list(conds)
    ym = func.to_char(func.date_trunc("month", Invoice.created_at), "YYYY-MM").label("ym")
    stmt_m = (
        select(ym, func.count(Invoice.id), func.coalesce(func.sum(Invoice.amount), 0))
        .where(and_(*conds_m))
        .group_by(ym)
        .order_by(ym)
    )
    r_m = await db.execute(stmt_m)
    monthly: list[MonthlySeriesPoint] = []
    for row in r_m.all():
        yms, cnt, sm = row[0], row[1], row[2]
        amt = sm if isinstance(sm, Decimal) else Decimal(str(sm))
        monthly.append(
            MonthlySeriesPoint(month=yms, invoice_count=int(cnt), total_amount=amt)
        )

    # Pendientes con vencimiento en los próximos 7 días
    now = datetime.now(timezone.utc)
    week_end = now + timedelta(days=7)
    conds_due = invoice_visibility_conditions(org_id, user, platform_scope=platform_scope)
    append_date_range(conds_due, date_from, date_to)
    conds_due.extend(
        [
            Invoice.status == InvoiceStatus.pendiente,
            Invoice.due_date.isnot(None),
            Invoice.due_date >= now,
            Invoice.due_date <= week_end,
        ]
    )
    r_due = await db.execute(select(func.count()).select_from(Invoice).where(and_(*conds_due)))
    pending_due_7 = int(r_due.scalar() or 0)

    name = org_name
    if name is None:
        r_org = await db.execute(select(Organization.name).where(Organization.id == org_id))
        name = r_org.scalar_one_or_none()

    return DashboardStatsOut(
        organization_id=org_id,
        organization_name=name,
        total_invoices=total_n,
        total_amount=total_amt,
        count_by_status=counts,
        amount_by_status=amounts,
        monthly=monthly,
        pending_due_within_7_days=pending_due_7,
        date_from=date_from,
        date_to=date_to,
    )


async def top_organizations_by_billing(
    db: AsyncSession,
    *,
    limit: int,
    date_from: datetime | None,
    date_to: datetime | None,
    exclude_org_slugs: set[str],
) -> list[OrgBillingRankOut]:
    conds = [Organization.slug.not_in(list(exclude_org_slugs))]
    join_cond = Invoice.organization_id == Organization.id
    stmt = (
        select(
            Organization.id,
            Organization.name,
            Organization.slug,
            func.count(Invoice.id),
            func.coalesce(func.sum(Invoice.amount), 0),
        )
        .join(Invoice, join_cond)
        .where(and_(*conds))
    )
    if date_from is not None:
        stmt = stmt.where(Invoice.created_at >= date_from)
    if date_to is not None:
        stmt = stmt.where(Invoice.created_at <= date_to)
    stmt = (
        stmt.group_by(Organization.id, Organization.name, Organization.slug)
        .order_by(func.coalesce(func.sum(Invoice.amount), 0).desc())
        .limit(limit)
    )
    result = await db.execute(stmt)
    out: list[OrgBillingRankOut] = []
    for oid, name, slug, cnt, sm in result.all():
        amt = sm if isinstance(sm, Decimal) else Decimal(str(sm))
        out.append(
            OrgBillingRankOut(
                organization_id=oid,
                name=name,
                slug=slug,
                invoice_count=int(cnt),
                total_amount=amt,
            )
        )
    return out
