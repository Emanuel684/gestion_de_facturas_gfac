"""
Tests for POST /api/invoices/upload — document upload & data extraction.

Uses unittest.mock to patch the extraction module so tests don't depend
on tesseract, pdfplumber, or python-docx being installed.
"""
import pytest
from unittest.mock import patch, MagicMock
from httpx import AsyncClient


def auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


# ── Helpers ───────────────────────────────────────────────────────────────────

FAKE_EXTRACTED = {
    "invoice_number": "FAC-001",
    "supplier": "Proveedor Test S.A.",
    "amount": 1500000.50,
    "description": "Compra de materiales",
    "due_date": "2026-06-15T00:00:00+00:00",
    "raw_text": "Factura No. FAC-001\nProveedor: Proveedor Test S.A.\nTotal: $1.500.000,50",
}


def _make_upload_file(content: bytes = b"fake file content", filename: str = "factura.pdf", content_type: str = "application/pdf"):
    """Build the (filename, content, content_type) tuple for httpx file upload."""
    return {"file": (filename, content, content_type)}


# ── Success cases ─────────────────────────────────────────────────────────────

@pytest.mark.asyncio
@patch("src.routers.invoices.extract_from_file", return_value=FAKE_EXTRACTED)
async def test_upload_pdf_success(mock_extract, client: AsyncClient, admin_token: str):
    resp = await client.post(
        "/api/invoices/upload",
        files=_make_upload_file(),
        headers=auth(admin_token),
    )
    assert resp.status_code == 200
    body = resp.json()
    assert "extracted" in body
    assert body["extracted"]["invoice_number"] == "FAC-001"
    assert body["extracted"]["supplier"] == "Proveedor Test S.A."
    assert body["extracted"]["amount"] == 1500000.50
    assert body["filename"] == "factura.pdf"
    mock_extract.assert_called_once()


@pytest.mark.asyncio
@patch("src.routers.invoices.extract_from_file", return_value=FAKE_EXTRACTED)
async def test_upload_image_success(mock_extract, client: AsyncClient, admin_token: str):
    resp = await client.post(
        "/api/invoices/upload",
        files=_make_upload_file(filename="factura.jpg", content_type="image/jpeg"),
        headers=auth(admin_token),
    )
    assert resp.status_code == 200
    assert resp.json()["extracted"]["invoice_number"] == "FAC-001"


@pytest.mark.asyncio
@patch("src.routers.invoices.extract_from_file", return_value=FAKE_EXTRACTED)
async def test_upload_docx_success(mock_extract, client: AsyncClient, admin_token: str):
    resp = await client.post(
        "/api/invoices/upload",
        files=_make_upload_file(
            filename="factura.docx",
            content_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        ),
        headers=auth(admin_token),
    )
    assert resp.status_code == 200
    assert resp.json()["extracted"]["invoice_number"] == "FAC-001"


@pytest.mark.asyncio
@patch("src.routers.invoices.extract_from_file", return_value={"raw_text": "some text"})
async def test_upload_partial_extraction(mock_extract, client: AsyncClient, admin_token: str):
    """When extraction finds raw_text but no structured fields."""
    resp = await client.post(
        "/api/invoices/upload",
        files=_make_upload_file(),
        headers=auth(admin_token),
    )
    assert resp.status_code == 200
    body = resp.json()
    assert "revise los datos" in body["message"]


# ── All roles can upload ─────────────────────────────────────────────────────

@pytest.mark.asyncio
@patch("src.routers.invoices.extract_from_file", return_value=FAKE_EXTRACTED)
async def test_upload_contador(mock_extract, client: AsyncClient, contador_token: str):
    resp = await client.post(
        "/api/invoices/upload",
        files=_make_upload_file(),
        headers=auth(contador_token),
    )
    assert resp.status_code == 200


@pytest.mark.asyncio
@patch("src.routers.invoices.extract_from_file", return_value=FAKE_EXTRACTED)
async def test_upload_asistente(mock_extract, client: AsyncClient, asistente_token: str):
    resp = await client.post(
        "/api/invoices/upload",
        files=_make_upload_file(),
        headers=auth(asistente_token),
    )
    assert resp.status_code == 200


# ── Auth required ─────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_upload_unauthenticated(client: AsyncClient):
    resp = await client.post(
        "/api/invoices/upload",
        files=_make_upload_file(),
    )
    assert resp.status_code == 401


# ── Validation errors ────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_upload_unsupported_type(client: AsyncClient, admin_token: str):
    resp = await client.post(
        "/api/invoices/upload",
        files=_make_upload_file(filename="data.csv", content_type="text/csv"),
        headers=auth(admin_token),
    )
    assert resp.status_code == 415


@pytest.mark.asyncio
async def test_upload_empty_file(client: AsyncClient, admin_token: str):
    resp = await client.post(
        "/api/invoices/upload",
        files=_make_upload_file(content=b"", filename="empty.pdf"),
        headers=auth(admin_token),
    )
    assert resp.status_code == 422
    assert "vacío" in resp.json()["detail"]


# ── Extraction errors ────────────────────────────────────────────────────────

@pytest.mark.asyncio
@patch("src.routers.invoices.extract_from_file", side_effect=ValueError("Tipo de archivo no soportado"))
async def test_upload_extraction_value_error(mock_extract, client: AsyncClient, admin_token: str):
    resp = await client.post(
        "/api/invoices/upload",
        files=_make_upload_file(),
        headers=auth(admin_token),
    )
    assert resp.status_code == 415


@pytest.mark.asyncio
@patch("src.routers.invoices.extract_from_file", side_effect=RuntimeError("pytesseract not installed"))
async def test_upload_extraction_runtime_error(mock_extract, client: AsyncClient, admin_token: str):
    resp = await client.post(
        "/api/invoices/upload",
        files=_make_upload_file(),
        headers=auth(admin_token),
    )
    assert resp.status_code == 501


@pytest.mark.asyncio
@patch("src.routers.invoices.extract_from_file", side_effect=Exception("Unexpected crash"))
async def test_upload_extraction_unexpected_error(mock_extract, client: AsyncClient, admin_token: str):
    resp = await client.post(
        "/api/invoices/upload",
        files=_make_upload_file(),
        headers=auth(admin_token),
    )
    assert resp.status_code == 500


# ── Extension-based fallback ─────────────────────────────────────────────────

@pytest.mark.asyncio
@patch("src.routers.invoices.extract_from_file", return_value=FAKE_EXTRACTED)
async def test_upload_fallback_by_extension(mock_extract, client: AsyncClient, admin_token: str):
    """When content_type is generic but extension is valid, should still work."""
    resp = await client.post(
        "/api/invoices/upload",
        files=_make_upload_file(filename="factura.png", content_type="application/octet-stream"),
        headers=auth(admin_token),
    )
    assert resp.status_code == 200
