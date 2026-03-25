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
        json={**SAMPLE_INVOICE, "invoice_number": "FAC-101"},        headers=auth(admin_token),
    )

    resp = await client.get("/api/invoices", headers=auth(admin_token))
    assert resp.status_code == 200
    assert len(resp.json()["items"]) == 2


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
    assert len(resp.json()["items"]) == 2


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
    invoices = resp.json()["items"]
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
    invoices = resp.json()["items"]
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
    invoices = resp.json()["items"]
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


# ── Pagination ────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_pagination_response_shape(client: AsyncClient, admin_token: str):
    """Response must include items, has_next, page, page_size."""
    await client.post(
        "/api/invoices",
        json={**SAMPLE_INVOICE, "invoice_number": "PAG-001"},
        headers=auth(admin_token),
    )
    resp = await client.get("/api/invoices", headers=auth(admin_token))
    assert resp.status_code == 200
    body = resp.json()
    assert "items" in body
    assert "has_next" in body
    assert "page" in body
    assert "page_size" in body


@pytest.mark.asyncio
async def test_pagination_first_page_no_next(client: AsyncClient, admin_token: str):
    """With fewer items than page_size, has_next must be False."""
    for i in range(3):
        await client.post(
            "/api/invoices",
            json={**SAMPLE_INVOICE, "invoice_number": f"PAG-1{i:02d}"},
            headers=auth(admin_token),
        )
    resp = await client.get("/api/invoices?page=0&page_size=10", headers=auth(admin_token))
    assert resp.status_code == 200
    body = resp.json()
    assert body["has_next"] is False
    assert len(body["items"]) == 3


@pytest.mark.asyncio
async def test_pagination_has_next_when_more_items(client: AsyncClient, admin_token: str):
    """With 11 items and page_size=10, page 0 must have has_next=True."""
    for i in range(11):
        await client.post(
            "/api/invoices",
            json={**SAMPLE_INVOICE, "invoice_number": f"PAG-2{i:02d}"},
            headers=auth(admin_token),
        )
    resp = await client.get("/api/invoices?page=0&page_size=10", headers=auth(admin_token))
    body = resp.json()
    assert body["has_next"] is True
    assert len(body["items"]) == 10


@pytest.mark.asyncio
async def test_pagination_second_page(client: AsyncClient, admin_token: str):
    """Page 1 returns remaining items and has_next=False."""
    for i in range(11):
        await client.post(
            "/api/invoices",
            json={**SAMPLE_INVOICE, "invoice_number": f"PAG-3{i:02d}"},
            headers=auth(admin_token),
        )
    resp = await client.get("/api/invoices?page=1&page_size=10", headers=auth(admin_token))
    body = resp.json()
    assert len(body["items"]) == 1
    assert body["has_next"] is False
    assert body["page"] == 1


@pytest.mark.asyncio
async def test_pagination_empty_page_beyond_data(client: AsyncClient, admin_token: str):
    """Requesting a page well beyond the data returns an empty items list."""
    await client.post(
        "/api/invoices",
        json={**SAMPLE_INVOICE, "invoice_number": "PAG-400"},
        headers=auth(admin_token),
    )    
    resp = await client.get("/api/invoices?page=99&page_size=10", headers=auth(admin_token))
    body = resp.json()
    assert resp.status_code == 200
    assert body["items"] == []
    assert body["has_next"] is False


# ── Overdue ───────────────────────────────────────────────────────────────────

PAST_DATE   = "2020-01-01T00:00:00"   # always in the past
FUTURE_DATE = "2099-12-31T00:00:00"   # always in the future


@pytest.mark.asyncio
async def test_overdue_returns_only_past_due_pendiente(client: AsyncClient, admin_token: str):
    """Only pendiente invoices with a past due_date must appear."""
    # past-due pendiente → should appear
    await client.post(
        "/api/invoices",
        json={**SAMPLE_INVOICE, "invoice_number": "OVD-001",
              "status": "pendiente", "due_date": PAST_DATE},
        headers=auth(admin_token),
    )
    # future-due pendiente → should NOT appear
    await client.post(
        "/api/invoices",
        json={**SAMPLE_INVOICE, "invoice_number": "OVD-002",
              "status": "pendiente", "due_date": FUTURE_DATE},
        headers=auth(admin_token),
    )
    # past-due but already pagada → should NOT appear
    await client.post(
        "/api/invoices",
        json={**SAMPLE_INVOICE, "invoice_number": "OVD-003",
              "status": "pagada", "due_date": PAST_DATE},
        headers=auth(admin_token),
    )
    # no due_date → should NOT appear
    await client.post(
        "/api/invoices",
        json={**SAMPLE_INVOICE, "invoice_number": "OVD-004", "status": "pendiente"},
        headers=auth(admin_token),
    )

    resp = await client.get("/api/invoices/overdue", headers=auth(admin_token))
    assert resp.status_code == 200
    numbers = [inv["invoice_number"] for inv in resp.json()]
    assert "OVD-001" in numbers
    assert "OVD-002" not in numbers
    assert "OVD-003" not in numbers
    assert "OVD-004" not in numbers


@pytest.mark.asyncio
async def test_overdue_empty_when_none(client: AsyncClient, admin_token: str):
    """Returns an empty list when no invoices are overdue."""
    await client.post(
        "/api/invoices",
        json={**SAMPLE_INVOICE, "invoice_number": "OVD-100",
              "status": "pendiente", "due_date": FUTURE_DATE},
        headers=auth(admin_token),
    )
    resp = await client.get("/api/invoices/overdue", headers=auth(admin_token))
    assert resp.status_code == 200
    assert resp.json() == []


@pytest.mark.asyncio
async def test_overdue_requires_auth(client: AsyncClient):
    """Unauthenticated requests must be rejected."""
    resp = await client.get("/api/invoices/overdue")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_overdue_asistente_sees_only_own(
    client: AsyncClient, admin_token: str, asistente_token: str, asistente_user
):
    """Asistente only sees overdue invoices they created or are assigned to."""
    # created by admin — should NOT be visible to asistente
    await client.post(
        "/api/invoices",
        json={**SAMPLE_INVOICE, "invoice_number": "OVD-200",
              "status": "pendiente", "due_date": PAST_DATE},
        headers=auth(admin_token),
    )
    # created by asistente — should be visible
    await client.post(
        "/api/invoices",
        json={**SAMPLE_INVOICE, "invoice_number": "OVD-201",
              "status": "pendiente", "due_date": PAST_DATE},
        headers=auth(asistente_token),
    )

    resp = await client.get("/api/invoices/overdue", headers=auth(asistente_token))
    assert resp.status_code == 200
    numbers = [inv["invoice_number"] for inv in resp.json()]
    assert "OVD-201" in numbers
    assert "OVD-200" not in numbers


@pytest.mark.asyncio
async def test_overdue_ordered_by_due_date_asc(client: AsyncClient, admin_token: str):
    """Overdue invoices must be ordered oldest due_date first."""
    await client.post(
        "/api/invoices",
        json={**SAMPLE_INVOICE, "invoice_number": "OVD-300",
              "status": "pendiente", "due_date": "2022-06-01T00:00:00"},
        headers=auth(admin_token),
    )
    await client.post(
        "/api/invoices",
        json={**SAMPLE_INVOICE, "invoice_number": "OVD-301",
              "status": "pendiente", "due_date": "2021-01-01T00:00:00"},
        headers=auth(admin_token),
    )

    resp = await client.get("/api/invoices/overdue", headers=auth(admin_token))
    assert resp.status_code == 200
    numbers = [inv["invoice_number"] for inv in resp.json()]
    assert numbers.index("OVD-301") < numbers.index("OVD-300")


# ── DIAN traceability / fiscal ────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_create_invoice_emits_created_event(client: AsyncClient, admin_token: str):
    r = await client.post(
        "/api/invoices",
        json={**SAMPLE_INVOICE, "invoice_number": "DIAN-EV-1"},
        headers=auth(admin_token),
    )
    assert r.status_code == 201
    iid = r.json()["id"]
    tr = await client.get(f"/api/invoices/{iid}/trace", headers=auth(admin_token))
    assert tr.status_code == 200
    types = [e["event_type"] for e in tr.json()["events"]]
    assert "created" in types


@pytest.mark.asyncio
async def test_audit_pack_json_and_export_event(client: AsyncClient, admin_token: str):
    r = await client.post(
        "/api/invoices",
        json={**SAMPLE_INVOICE, "invoice_number": "DIAN-AUD-1"},
        headers=auth(admin_token),
    )
    assert r.status_code == 201
    iid = r.json()["id"]

    ap = await client.get(f"/api/invoices/{iid}/audit-pack", headers=auth(admin_token))
    assert ap.status_code == 200
    body = ap.json()
    assert body["schema_version"] == 1
    assert body["invoice"]["invoice_number"] == "DIAN-AUD-1"
    assert "events" in body

    tr = await client.get(f"/api/invoices/{iid}/trace", headers=auth(admin_token))
    types = [e["event_type"] for e in tr.json()["events"]]
    assert "export_generated" in types


@pytest.mark.asyncio
async def test_locked_invoice_rejects_fiscal_field_update(client: AsyncClient, admin_token: str):
    r = await client.post(
        "/api/invoices",
        json={**SAMPLE_INVOICE, "invoice_number": "DIAN-LOCK-1"},
        headers=auth(admin_token),
    )
    assert r.status_code == 201
    iid = r.json()["id"]

    up = await client.put(
        f"/api/invoices/{iid}",
        json={"dian_lifecycle_status": "lista_para_envio"},
        headers=auth(admin_token),
    )
    assert up.status_code == 200
    assert up.json()["document_locked"] is True

    bad = await client.put(
        f"/api/invoices/{iid}",
        json={"supplier": "Otro proveedor"},
        headers=auth(admin_token),
    )
    assert bad.status_code == 400


@pytest.mark.asyncio
async def test_create_invoice_rejects_incoherent_totals(client: AsyncClient, admin_token: str):
    resp = await client.post(
        "/api/invoices",
        json={
            **SAMPLE_INVOICE,
            "invoice_number": "DIAN-TOT-BAD",
            "subtotal": 100,
            "iva_amount": 0,
            "total_document": 50,
        },
        headers=auth(admin_token),
    )
    assert resp.status_code == 422
    assert "total" in resp.json()["detail"].lower() or "totales" in resp.json()["detail"].lower()


@pytest.mark.asyncio
async def test_fiscal_profile_get_returns_for_tenant(client: AsyncClient, admin_token: str):
    r = await client.get("/api/fiscal/profile", headers=auth(admin_token))
    assert r.status_code == 200
    data = r.json()
    assert "organization_id" in data
    assert data["nit"] == ""
