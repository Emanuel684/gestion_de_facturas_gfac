import pytest
from httpx import AsyncClient


def auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


SAMPLE_INVOICE = {
    "invoice_number": "ORG-PLAT-001",
    "supplier": "Proveedor Org",
    "description": "Factura para pruebas plataforma",
    "amount": 250000,
}


@pytest.mark.asyncio
async def test_platform_admin_can_update_org_invoice(
    client: AsyncClient,
    admin_token: str,
    platform_token: str,
    tenant_org,
):
    created = await client.post("/api/invoices", json=SAMPLE_INVOICE, headers=auth(admin_token))
    assert created.status_code == 201
    invoice_id = created.json()["id"]

    updated = await client.put(
        f"/api/organizations/{tenant_org.id}/invoices/{invoice_id}",
        json={"supplier": "Proveedor Actualizado", "status": "pagada"},
        headers=auth(platform_token),
    )
    assert updated.status_code == 200
    body = updated.json()
    assert body["supplier"] == "Proveedor Actualizado"
    assert body["status"] == "pagada"


@pytest.mark.asyncio
async def test_platform_admin_can_delete_org_invoice(
    client: AsyncClient,
    admin_token: str,
    platform_token: str,
    tenant_org,
):
    created = await client.post(
        "/api/invoices",
        json={**SAMPLE_INVOICE, "invoice_number": "ORG-PLAT-DEL-1"},
        headers=auth(admin_token),
    )
    assert created.status_code == 201
    invoice_id = created.json()["id"]

    deleted = await client.delete(
        f"/api/organizations/{tenant_org.id}/invoices/{invoice_id}",
        headers=auth(platform_token),
    )
    assert deleted.status_code == 204

    listed = await client.get(
        f"/api/organizations/{tenant_org.id}/invoices",
        headers=auth(platform_token),
    )
    assert listed.status_code == 200
    assert all(inv["id"] != invoice_id for inv in listed.json())


@pytest.mark.asyncio
async def test_platform_update_rejects_invoice_from_other_org(
    client: AsyncClient,
    admin_token: str,
    platform_token: str,
    tenant_org,
    platform_org,
):
    created = await client.post(
        "/api/invoices",
        json={**SAMPLE_INVOICE, "invoice_number": "ORG-PLAT-404-1"},
        headers=auth(admin_token),
    )
    assert created.status_code == 201
    invoice_id = created.json()["id"]

    bad = await client.put(
        f"/api/organizations/{platform_org.id}/invoices/{invoice_id}",
        json={"status": "pagada"},
        headers=auth(platform_token),
    )
    assert bad.status_code == 404
