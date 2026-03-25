"""Construcción del paquete de auditoría (JSON) para trazabilidad."""
from datetime import datetime
from decimal import Decimal

from src.models import Invoice, InvoiceEvent, OrganizationFiscalProfile


def _decimal_to_str(v: Decimal | None) -> str | None:
    if v is None:
        return None
    return format(v, "f")


def build_audit_pack(
    invoice: Invoice,
    events: list[InvoiceEvent],
    fiscal_profile: OrganizationFiscalProfile | None,
    generated_at: datetime,
) -> dict:
    """Documento consolidado para revisión contable / trazabilidad."""
    return {
        "generated_at": generated_at.isoformat(),
        "schema_version": 1,
        "organization_id": invoice.organization_id,
        "invoice": {
            "id": invoice.id,
            "invoice_number": invoice.invoice_number,
            "document_type": invoice.document_type.value,
            "issue_date": invoice.issue_date.isoformat() if invoice.issue_date else None,
            "currency": invoice.currency,
            "dian_lifecycle_status": invoice.dian_lifecycle_status.value,
            "document_locked": invoice.document_locked,
            "internal_status": invoice.status.value,
            "supplier": invoice.supplier,
            "description": invoice.description,
            "amount_internal": _decimal_to_str(invoice.amount),
            "buyer": {
                "id_type": invoice.buyer_id_type,
                "id_number": invoice.buyer_id_number,
                "name": invoice.buyer_name,
            },
            "seller_snapshot": {
                "nit": invoice.seller_snapshot_nit,
                "dv": invoice.seller_snapshot_dv,
                "business_name": invoice.seller_snapshot_business_name,
            },
            "totals": {
                "subtotal": _decimal_to_str(invoice.subtotal),
                "taxable_base": _decimal_to_str(invoice.taxable_base),
                "iva_rate": _decimal_to_str(invoice.iva_rate),
                "iva_amount": _decimal_to_str(invoice.iva_amount),
                "withholding_amount": _decimal_to_str(invoice.withholding_amount),
                "total_document": _decimal_to_str(invoice.total_document),
            },
            "due_date": invoice.due_date.isoformat() if invoice.due_date else None,
            "created_at": invoice.created_at.isoformat(),
            "updated_at": invoice.updated_at.isoformat(),
        },
        "fiscal_profile": None
        if fiscal_profile is None
        else {
            "nit": fiscal_profile.nit,
            "dv": fiscal_profile.dv,
            "business_name": fiscal_profile.business_name,
            "trade_name": fiscal_profile.trade_name,
            "department_code": fiscal_profile.department_code,
            "city_code": fiscal_profile.city_code,
            "tax_regime": fiscal_profile.tax_regime.value,
            "invoice_prefix_default": fiscal_profile.invoice_prefix_default,
        },
        "events": [
            {
                "id": e.id,
                "event_type": e.event_type.value,
                "actor_user_id": e.actor_user_id,
                "payload": e.payload,
                "created_at": e.created_at.isoformat(),
            }
            for e in events
        ],
    }
