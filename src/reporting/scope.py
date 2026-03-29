"""Filtros de visibilidad de facturas (misma lógica que el listado)."""
from __future__ import annotations

from datetime import date, datetime, time, timezone
from typing import Any

from sqlalchemy import and_, or_, select

from src.models import Invoice, InvoiceAssignee, User, UserRole


def invoice_visibility_conditions(org_id: int, user: User | None, *, platform_scope: bool) -> list[Any]:
    """
    platform_scope=True: vista de auditoría (admin plataforma) — todas las facturas de la org.
    """
    conds: list[Any] = [Invoice.organization_id == org_id]
    if platform_scope:
        return conds
    assert user is not None
    if user.role == UserRole.asistente:
        assigned_subq = select(InvoiceAssignee.invoice_id).where(InvoiceAssignee.user_id == user.id)
        conds.append(or_(Invoice.creator_id == user.id, Invoice.id.in_(assigned_subq)))
    return conds


def append_date_range(
    conds: list[Any],
    date_from: datetime | None,
    date_to: datetime | None,
) -> None:
    if date_from is not None:
        conds.append(Invoice.created_at >= date_from)
    if date_to is not None:
        conds.append(Invoice.created_at <= date_to)


def parse_date_range_bounds(
    date_from: Any | None,
    date_to: Any | None,
) -> tuple[datetime | None, datetime | None]:
    """Convierte date/datetime a inicio/fin UTC para filtrar created_at."""
    start: datetime | None = None
    end: datetime | None = None
    if date_from is None and date_to is None:
        return None, None
    if date_from is not None:
        if isinstance(date_from, datetime):
            d = date_from
            if d.tzinfo is None:
                d = d.replace(tzinfo=timezone.utc)
            start = d
        elif isinstance(date_from, date):
            start = datetime.combine(date_from, time.min, tzinfo=timezone.utc)
    if date_to is not None:
        if isinstance(date_to, datetime):
            d = date_to
            if d.tzinfo is None:
                d = d.replace(tzinfo=timezone.utc)
            end = d
        elif isinstance(date_to, date):
            end = datetime.combine(date_to, time.max, tzinfo=timezone.utc)
    return start, end
