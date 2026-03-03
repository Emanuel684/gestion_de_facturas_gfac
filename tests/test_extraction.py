"""
Unit tests for the extraction module — regex-based field extraction.

These tests verify the regex patterns and parsing logic without requiring
tesseract, pdfplumber, or python-docx.
"""
import pytest
from src.extraction import extract_invoice_data, _parse_amount, _parse_date


# ── Invoice number extraction ────────────────────────────────────────────────

class TestInvoiceNumberExtraction:
    def test_factura_no(self):
        text = "Factura No. FAC-001\nProveedor: Acme Corp"
        result = extract_invoice_data(text)
        assert result.get("invoice_number") == "FAC-001"

    def test_factura_numero(self):
        text = "FACTURA NÚMERO: INV-2024-0050\nFecha: 01/01/2025"
        result = extract_invoice_data(text)
        assert result.get("invoice_number") is not None
        assert "INV-2024-0050" in result["invoice_number"]

    def test_fac_pattern(self):
        text = "Detalles de pago\nFAC-12345 emitida el 05/03/2025"
        result = extract_invoice_data(text)
        assert result.get("invoice_number") == "FAC-12345"

    def test_invoice_hash(self):
        text = "Invoice #ABC-789\nAmount: $500.00"
        result = extract_invoice_data(text)
        assert result.get("invoice_number") is not None

    def test_no_invoice_number(self):
        text = "Este es un texto sin número de factura."
        result = extract_invoice_data(text)
        assert "invoice_number" not in result


# ── Supplier extraction ──────────────────────────────────────────────────────

class TestSupplierExtraction:
    def test_proveedor(self):
        text = "Factura No. 001\nProveedor: Distribuciones ABC S.A.S"
        result = extract_invoice_data(text)
        assert result.get("supplier") == "Distribuciones ABC S.A.S"

    def test_empresa(self):
        text = "Empresa: Tech Solutions Ltda.\nTotal: $2.000.000"
        result = extract_invoice_data(text)
        assert result.get("supplier") == "Tech Solutions Ltda."

    def test_razon_social(self):
        text = "Razón Social: Importadora del Caribe\nNIT: 900.123.456-7"
        result = extract_invoice_data(text)
        assert result.get("supplier") == "Importadora del Caribe"

    def test_no_supplier(self):
        text = "Total: $5.000.000\nFecha: 01/01/2025"
        result = extract_invoice_data(text)
        assert "supplier" not in result


# ── Amount extraction ────────────────────────────────────────────────────────

class TestAmountExtraction:
    def test_total_cop_format(self):
        text = "Factura 001\nTotal: $1.500.000,50"
        result = extract_invoice_data(text)
        assert result.get("amount") == 1500000.50

    def test_total_us_format(self):
        text = "Invoice 001\nTotal: $1,500,000.50"
        result = extract_invoice_data(text)
        assert result.get("amount") == 1500000.50

    def test_total_simple(self):
        text = "Factura 001\nTotal: 250000"
        result = extract_invoice_data(text)
        assert result.get("amount") == 250000

    def test_valor_total(self):
        text = "Detalle de productos\nValor Total: $3.200.000"
        result = extract_invoice_data(text)
        assert result.get("amount") == 3200000

    def test_total_a_pagar(self):
        text = "Subtotal: $1.000.000\nIVA: $190.000\nTotal a pagar: $1.190.000"
        result = extract_invoice_data(text)
        assert result.get("amount") == 1190000

    def test_no_amount(self):
        text = "Este documento no tiene montos."
        result = extract_invoice_data(text)
        assert "amount" not in result


# ── Date extraction ──────────────────────────────────────────────────────────

class TestDateExtraction:
    def test_fecha_vencimiento(self):
        text = "Factura 001\nFecha de vencimiento: 15/06/2026"
        result = extract_invoice_data(text)
        assert result.get("due_date") is not None
        assert "2026-06-15" in result["due_date"]

    def test_vencimiento_dash(self):
        text = "Vencimiento: 30-12-2025"
        result = extract_invoice_data(text)
        assert result.get("due_date") is not None
        assert "2025-12-30" in result["due_date"]

    def test_no_due_date(self):
        text = "Factura sin fecha de vencimiento\nTotal: $500.000"
        result = extract_invoice_data(text)
        assert "due_date" not in result


# ── Description extraction ───────────────────────────────────────────────────

class TestDescriptionExtraction:
    def test_descripcion(self):
        text = "Factura 001\nDescripción: Compra de insumos de oficina"
        result = extract_invoice_data(text)
        assert result.get("description") == "Compra de insumos de oficina"

    def test_concepto(self):
        text = "Concepto: Servicio de consultoría técnica\nTotal: $5.000.000"
        result = extract_invoice_data(text)
        assert result.get("description") == "Servicio de consultoría técnica"

    def test_no_description(self):
        text = "Total: $100.000"
        result = extract_invoice_data(text)
        assert "description" not in result


# ── Amount parsing helper ────────────────────────────────────────────────────

class TestParseAmount:
    def test_european_format(self):
        assert _parse_amount("1.500.000,50") == pytest.approx(1500000.50)

    def test_us_format(self):
        assert _parse_amount("1,500,000.50") == pytest.approx(1500000.50)

    def test_simple_integer(self):
        assert _parse_amount("250000") == pytest.approx(250000)

    def test_simple_decimal(self):
        assert _parse_amount("1500.75") == pytest.approx(1500.75)

    def test_empty(self):
        assert _parse_amount("") is None

    def test_none(self):
        assert _parse_amount(None) is None

    def test_zero(self):
        assert _parse_amount("0") is None

    def test_negative_not_matched(self):
        # Regex won't capture negative, but if raw somehow gets here
        assert _parse_amount("-100") is None


# ── Date parsing helper ──────────────────────────────────────────────────────

class TestParseDate:
    def test_dd_mm_yyyy_slash(self):
        dt = _parse_date("15/06/2026")
        assert dt is not None
        assert dt.day == 15
        assert dt.month == 6
        assert dt.year == 2026

    def test_dd_mm_yyyy_dash(self):
        dt = _parse_date("31-12-2025")
        assert dt is not None
        assert dt.day == 31
        assert dt.month == 12

    def test_yyyy_mm_dd(self):
        dt = _parse_date("2025-03-15")
        assert dt is not None
        assert dt.year == 2025
        assert dt.month == 3
        assert dt.day == 15

    def test_invalid(self):
        assert _parse_date("not-a-date") is None

    def test_empty(self):
        assert _parse_date("") is None

    def test_none(self):
        assert _parse_date(None) is None


# ── Full text extraction ─────────────────────────────────────────────────────

class TestFullExtraction:
    def test_complete_invoice_text(self):
        text = """
        FACTURA DE VENTA
        Factura No. FAC-2025-0042
        Proveedor: Distribuidora Nacional S.A.S
        NIT: 900.456.789-0

        Descripción: Compra de materiales de construcción
        Subtotal: $8.500.000
        IVA (19%): $1.615.000
        Total a pagar: $10.115.000

        Fecha de vencimiento: 30/04/2026
        """
        result = extract_invoice_data(text)
        assert result.get("invoice_number") is not None
        assert result.get("supplier") is not None
        assert result.get("amount") is not None
        assert result.get("due_date") is not None
        assert result.get("description") is not None

    def test_minimal_text(self):
        text = "Hello world, no invoice data here."
        result = extract_invoice_data(text)
        # Should return empty dict (no fields matched)
        assert "invoice_number" not in result
        assert "supplier" not in result
        assert "amount" not in result
