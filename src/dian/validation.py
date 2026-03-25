"""Validaciones básicas para datos fiscales Colombia (preparación DIAN)."""
from decimal import Decimal

from src.models import DianLifecycleStatus

# IVA general Colombia (puede parametrizarse por producto en el futuro)
DEFAULT_IVA_RATE = Decimal("0.19")

# Tolerancia en pesos para comparar totales (redondeo)
COP_TOLERANCE = Decimal("0.02")

LOCKING_DIAN_STATUSES: frozenset[DianLifecycleStatus] = frozenset(
    {
        DianLifecycleStatus.lista_para_envio,
        DianLifecycleStatus.enviada_proveedor,
        DianLifecycleStatus.aceptada_dian,
        DianLifecycleStatus.contingencia,
    }
)


def is_document_editing_locked(status: DianLifecycleStatus, document_locked: bool) -> bool:
    if document_locked:
        return True
    return status in LOCKING_DIAN_STATUSES


def normalize_nit_digits(nit: str) -> str:
    return "".join(c for c in nit.strip() if c.isdigit())


def validate_nit_format(nit: str) -> None:
    """Validación mínima: solo dígitos, longitud típica NIT Colombia 9–10."""
    d = normalize_nit_digits(nit)
    if len(d) < 8 or len(d) > 10:
        raise ValueError("NIT inválido: use 8 a 10 dígitos")


def validate_dv_format(dv: str) -> None:
    s = dv.strip()
    if not s.isdigit() or len(s) > 2 or len(s) < 1:
        raise ValueError("Dígito de verificación inválido")


def expected_total(
    subtotal: Decimal,
    iva_amount: Decimal,
    withholding: Decimal | None,
) -> Decimal:
    w = withholding or Decimal("0")
    return subtotal + iva_amount - w


def totals_match(
    subtotal: Decimal,
    iva_amount: Decimal,
    withholding: Decimal | None,
    total: Decimal,
) -> bool:
    exp = expected_total(subtotal, iva_amount, withholding)
    return abs(exp - total) <= COP_TOLERANCE
