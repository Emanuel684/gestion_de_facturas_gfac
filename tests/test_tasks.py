"""
Tests for /api/invoices — CRUD and permission rules for SGF.
"""
import pytest
from httpx import AsyncClient


def auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


SAMPLE_INVOICE = {
    "invoice_number": "FAC-001",
    "supplier": "Proveedor ABC",
    "description": "Compra de materiales",
    "amount": 1500000.50,
}


# ── Create ────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_create_invoice_admin(client: AsyncClient, admin_token: str):
    resp = await client.post(
        "/api/invoices",
        json=SAMPLE_INVOICE,
        headers=auth(admin_token),
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["invoice_number"] == "FAC-001"
    assert body["supplier"] == "Proveedor ABC"
    assert body["status"] == "pendiente"
    assert float(body["amount"]) == 1500000.50


@pytest.mark.asyncio
async def test_create_invoice_contador(client: AsyncClient, contador_token: str):
    resp = await client.post(
        "/api/invoices",
        json={**SAMPLE_INVOICE, "invoice_number": "FAC-002"},
        headers=auth(contador_token),
    )
    assert resp.status_code == 201


@pytest.mark.asyncio
async def test_create_invoice_asistente(client: AsyncClient, asistente_token: str):
    resp = await client.post(
        "/api/invoices",
        json={**SAMPLE_INVOICE, "invoice_number": "FAC-003"},
        headers=auth(asistente_token),
    )
    assert resp.status_code == 201


@pytest.mark.asyncio
async def test_create_invoice_duplicate_number(client: AsyncClient, admin_token: str):
    await client.post(
        "/api/invoices",
        json=SAMPLE_INVOICE,
        headers=auth(admin_token),
    )
    resp = await client.post(
        "/api/invoices",
        json=SAMPLE_INVOICE,
        headers=auth(admin_token),
    )
    assert resp.status_code == 409


@pytest.mark.asyncio
async def test_create_invoice_empty_supplier(client: AsyncClient, admin_token: str):
    resp = await client.post(
        "/api/invoices",
        json={**SAMPLE_INVOICE, "invoice_number": "FAC-X", "supplier": "   "},
        headers=auth(admin_token),
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_create_invoice_negative_amount(client: AsyncClient, admin_token: str):
    resp = await client.post(
        "/api/invoices",
        json={**SAMPLE_INVOICE, "invoice_number": "FAC-X", "amount": -100},
        headers=auth(admin_token),
    )
    assert resp.status_code == 422


# ── List ─────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_admin_sees_all_invoices(
    client: AsyncClient, admin_token: str, contador_token: str
):
    await client.post(
        "/api/invoices",
        json={**SAMPLE_INVOICE, "invoice_number": "FAC-100"},
        headers=auth(contador_token),
    )
    await client.post(
        "/api/invoices",
        json={**SAMPLE_INVOICE, "invoice_number": "FAC-101"},
        headers=auth(admin_token),
    )

    resp = await client.get("/api/invoices", headers=auth(admin_token))
    assert resp.status_code == 200
    assert len(resp.json()) == 2


@pytest.mark.asyncio
async def test_contador_sees_all_invoices(
    client: AsyncClient, admin_token: str, contador_token: str
):
    await client.post(
        "/api/invoices",
        json={**SAMPLE_INVOICE, "invoice_number": "FAC-200"},
        headers=auth(admin_token),
    )
    await client.post(
        "/api/invoices",
        json={**SAMPLE_INVOICE, "invoice_number": "FAC-201"},
        headers=auth(contador_token),
    )

    resp = await client.get("/api/invoices", headers=auth(contador_token))
    assert resp.status_code == 200
    assert len(resp.json()) == 2


@pytest.mark.asyncio
async def test_asistente_sees_only_own_invoices(
    client: AsyncClient, admin_token: str, asistente_token: str
):
    await client.post(
        "/api/invoices",
        json={**SAMPLE_INVOICE, "invoice_number": "FAC-300"},
        headers=auth(admin_token),
    )
    await client.post(
        "/api/invoices",
        json={**SAMPLE_INVOICE, "invoice_number": "FAC-301"},
        headers=auth(asistente_token),
    )

    resp = await client.get("/api/invoices", headers=auth(asistente_token))
    assert resp.status_code == 200
    invoices = resp.json()
    assert len(invoices) == 1
    assert invoices[0]["invoice_number"] == "FAC-301"


@pytest.mark.asyncio
async def test_filter_by_status(client: AsyncClient, admin_token: str):
    await client.post(
        "/api/invoices",
        json={**SAMPLE_INVOICE, "invoice_number": "FAC-400", "status": "pendiente"},
        headers=auth(admin_token),
    )
    await client.post(
        "/api/invoices",
        json={**SAMPLE_INVOICE, "invoice_number": "FAC-401", "status": "pagada"},
        headers=auth(admin_token),
    )

    resp = await client.get("/api/invoices?status=pagada", headers=auth(admin_token))
    assert resp.status_code == 200
    invoices = resp.json()
    assert len(invoices) == 1
    assert invoices[0]["invoice_number"] == "FAC-401"


@pytest.mark.asyncio
async def test_filter_by_supplier(client: AsyncClient, admin_token: str):
    await client.post(
        "/api/invoices",
        json={**SAMPLE_INVOICE, "invoice_number": "FAC-500", "supplier": "Acme Corp"},
        headers=auth(admin_token),
    )
    await client.post(
        "/api/invoices",
        json={**SAMPLE_INVOICE, "invoice_number": "FAC-501", "supplier": "Beta Ltd"},
        headers=auth(admin_token),
    )

    resp = await client.get("/api/invoices?supplier=acme", headers=auth(admin_token))
    assert resp.status_code == 200
    invoices = resp.json()
    assert len(invoices) == 1
    assert invoices[0]["supplier"] == "Acme Corp"


# ── Read ──────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_get_invoice_by_id(client: AsyncClient, admin_token: str):
    create_resp = await client.post(
        "/api/invoices",
        json={**SAMPLE_INVOICE, "invoice_number": "FAC-600"},
        headers=auth(admin_token),
    )
    invoice_id = create_resp.json()["id"]

    resp = await client.get(f"/api/invoices/{invoice_id}", headers=auth(admin_token))
    assert resp.status_code == 200
    assert resp.json()["id"] == invoice_id


@pytest.mark.asyncio
async def test_get_invoice_not_found(client: AsyncClient, admin_token: str):
    resp = await client.get("/api/invoices/99999", headers=auth(admin_token))
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_asistente_cannot_access_others_invoice(
    client: AsyncClient, admin_token: str, asistente_token: str, asistente_user
):
    create_resp = await client.post(
        "/api/invoices",
        json={**SAMPLE_INVOICE, "invoice_number": "FAC-700"},
        headers=auth(admin_token),
    )
    invoice_id = create_resp.json()["id"]

    resp = await client.get(f"/api/invoices/{invoice_id}", headers=auth(asistente_token))
    assert resp.status_code == 403


# ── Update ────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_update_invoice_status(client: AsyncClient, admin_token: str):
    create_resp = await client.post(
        "/api/invoices",
        json={**SAMPLE_INVOICE, "invoice_number": "FAC-800"},
        headers=auth(admin_token),
    )
    invoice_id = create_resp.json()["id"]

    resp = await client.put(
        f"/api/invoices/{invoice_id}",
        json={"status": "pagada"},
        headers=auth(admin_token),
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "pagada"


@pytest.mark.asyncio
async def test_asistente_cannot_update_invoice(
    client: AsyncClient, asistente_token: str
):
    create_resp = await client.post(
        "/api/invoices",
        json={**SAMPLE_INVOICE, "invoice_number": "FAC-850"},
        headers=auth(asistente_token),
    )
    invoice_id = create_resp.json()["id"]

    resp = await client.put(
        f"/api/invoices/{invoice_id}",
        json={"status": "pagada"},
        headers=auth(asistente_token),
    )
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_contador_cannot_update_others_invoice(
    client: AsyncClient, admin_token: str, contador_token: str
):
    create_resp = await client.post(
        "/api/invoices",
        json={**SAMPLE_INVOICE, "invoice_number": "FAC-860"},
        headers=auth(admin_token),
    )
    invoice_id = create_resp.json()["id"]

    resp = await client.put(
        f"/api/invoices/{invoice_id}",
        json={"status": "pagada"},
        headers=auth(contador_token),
    )
    assert resp.status_code == 403


# ── Delete ────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_delete_invoice_admin(client: AsyncClient, admin_token: str):
    create_resp = await client.post(
        "/api/invoices",
        json={**SAMPLE_INVOICE, "invoice_number": "FAC-900"},
        headers=auth(admin_token),
    )
    invoice_id = create_resp.json()["id"]

    resp = await client.delete(f"/api/invoices/{invoice_id}", headers=auth(admin_token))
    assert resp.status_code == 204

    resp = await client.get(f"/api/invoices/{invoice_id}", headers=auth(admin_token))
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_contador_cannot_delete_invoice(
    client: AsyncClient, contador_token: str
):
    create_resp = await client.post(
        "/api/invoices",
        json={**SAMPLE_INVOICE, "invoice_number": "FAC-950"},
        headers=auth(contador_token),
    )
    invoice_id = create_resp.json()["id"]

    resp = await client.delete(f"/api/invoices/{invoice_id}", headers=auth(contador_token))
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_asistente_cannot_delete_invoice(
    client: AsyncClient, asistente_token: str
):
    create_resp = await client.post(
        "/api/invoices",
        json={**SAMPLE_INVOICE, "invoice_number": "FAC-960"},
        headers=auth(asistente_token),
    )
    invoice_id = create_resp.json()["id"]

    resp = await client.delete(f"/api/invoices/{invoice_id}", headers=auth(asistente_token))
    assert resp.status_code == 403


# ── Assignment ────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_assign_user_to_invoice(
    client: AsyncClient, admin_token: str, contador_user
):
    create_resp = await client.post(
        "/api/invoices",
        json={**SAMPLE_INVOICE, "invoice_number": "FAC-970", "assigned_user_ids": [contador_user.id]},
        headers=auth(admin_token),
    )
    assert create_resp.status_code == 201
    body = create_resp.json()
    assert any(u["id"] == contador_user.id for u in body["assigned_users"])


@pytest.mark.asyncio
async def test_assigned_asistente_can_see_invoice(
    client: AsyncClient, admin_token: str, asistente_token: str, asistente_user
):
    create_resp = await client.post(
        "/api/invoices",
        json={**SAMPLE_INVOICE, "invoice_number": "FAC-980", "assigned_user_ids": [asistente_user.id]},
        headers=auth(admin_token),
    )
    invoice_id = create_resp.json()["id"]

    resp = await client.get(f"/api/invoices/{invoice_id}", headers=auth(asistente_token))
    assert resp.status_code == 200
