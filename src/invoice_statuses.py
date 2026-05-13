"""Helpers para definiciones de estado de cobranza por organización."""
import re
from typing import Sequence

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.invoice_status_constants import (
    DEFAULT_STATUS_ROWS,
    RESERVED_INVOICE_STATUS_KEYS,
    STATUS_KEY_PATTERN,
)
from src.models import Invoice, OrganizationInvoiceStatus


async def ensure_default_invoice_statuses(db: AsyncSession, organization_id: int) -> None:
    """Inserta las tres filas por defecto si la organización aún no tiene definiciones."""
    r = await db.execute(
        select(OrganizationInvoiceStatus.id)
        .where(OrganizationInvoiceStatus.organization_id == organization_id)
        .limit(1)
    )
    if r.scalar_one_or_none() is not None:
        return
    for key, label, sort_order, elig in DEFAULT_STATUS_ROWS:
        db.add(
            OrganizationInvoiceStatus(
                organization_id=organization_id,
                key=key,
                label=label,
                sort_order=sort_order,
                auto_overdue_eligible=elig,
            )
        )
    await db.flush()


async def list_status_definitions(
    db: AsyncSession, organization_id: int
) -> Sequence[OrganizationInvoiceStatus]:
    await ensure_default_invoice_statuses(db, organization_id)
    r = await db.execute(
        select(OrganizationInvoiceStatus)
        .where(OrganizationInvoiceStatus.organization_id == organization_id)
        .order_by(OrganizationInvoiceStatus.sort_order, OrganizationInvoiceStatus.id)
    )
    return r.scalars().all()


async def label_map_for_org(db: AsyncSession, organization_id: int) -> dict[str, str]:
    defs = await list_status_definitions(db, organization_id)
    return {d.key: d.label for d in defs}


async def valid_status_keys_for_org(db: AsyncSession, organization_id: int) -> set[str]:
    defs = await list_status_definitions(db, organization_id)
    return {d.key for d in defs}


def validate_status_key_format(key: str) -> None:
    if not key or not re.fullmatch(STATUS_KEY_PATTERN, key):
        raise ValueError(
            "La clave del estado debe ser minúsculas, comenzar con letra y "
            "solo usar letras, números y guión bajo (máx. 64 caracteres)."
        )


async def assert_invoice_status_allowed(
    db: AsyncSession, organization_id: int, status_key: str
) -> None:
    allowed = await valid_status_keys_for_org(db, organization_id)
    if status_key not in allowed:
        raise ValueError(
            f"Estado de cobranza no válido para la organización: {status_key!r}. "
            "Use una clave definida en la configuración de estados."
        )


async def invoice_count_for_status_key(
    db: AsyncSession, organization_id: int, key: str
) -> int:
    r = await db.execute(
        select(func.count())
        .select_from(Invoice)
        .where(Invoice.organization_id == organization_id, Invoice.status == key)
    )
    return int(r.scalar_one() or 0)
