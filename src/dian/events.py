"""Registro de eventos de trazabilidad en facturas."""
from sqlalchemy.ext.asyncio import AsyncSession

from src.models import Invoice, InvoiceEvent, InvoiceEventType, User


async def record_invoice_event(
    db: AsyncSession,
    *,
    invoice: Invoice,
    event_type: InvoiceEventType,
    actor: User | None,
    payload: dict | None = None,
) -> InvoiceEvent:
    ev = InvoiceEvent(
        invoice_id=invoice.id,
        organization_id=invoice.organization_id,
        event_type=event_type,
        actor_user_id=actor.id if actor else None,
        payload=payload,
    )
    db.add(ev)
    await db.flush()
    return ev
