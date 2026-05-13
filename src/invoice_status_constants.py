"""Claves reservadas de estado de cobranza (factura). El valor en BD es siempre la clave (slug)."""

KEY_PENDIENTE = "pendiente"
KEY_PAGADA = "pagada"
KEY_VENCIDA = "vencida"

RESERVED_INVOICE_STATUS_KEYS = frozenset({KEY_PENDIENTE, KEY_PAGADA, KEY_VENCIDA})

DEFAULT_STATUS_ROWS: tuple[tuple[str, str, int, bool], ...] = (
    (KEY_PENDIENTE, "Pendiente", 0, True),
    (KEY_PAGADA, "Pagada", 1, False),
    (KEY_VENCIDA, "Vencida", 2, False),
)

STATUS_KEY_PATTERN = r"^[a-z][a-z0-9_]{0,63}$"
