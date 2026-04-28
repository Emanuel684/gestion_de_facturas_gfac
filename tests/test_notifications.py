from httpx import AsyncClient
import pytest


def auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


SAMPLE_INVOICE = {
    "invoice_number": "NOTIF-001",
    "supplier": "Proveedor Alertas",
    "description": "Prueba de notificaciones",
    "amount": 250000,
}


async def _create_invoice(client: AsyncClient, token: str, payload: dict) -> dict:
    resp = await client.post("/api/invoices", json=payload, headers=auth(token))
    assert resp.status_code == 201
    return resp.json()


async def _list_notifications(client: AsyncClient, token: str) -> list[dict]:
    resp = await client.get("/api/notifications", headers=auth(token))
    assert resp.status_code == 200
    return resp.json()["items"]


async def _unread_count(client: AsyncClient, token: str) -> int:
    resp = await client.get("/api/notifications/unread-count", headers=auth(token))
    assert resp.status_code == 200
    return resp.json()["unread"]


@pytest.mark.asyncio
async def test_invoice_create_notifies_other_users(
    client: AsyncClient,
    admin_token: str,
    contador_token: str,
):
    await _create_invoice(client, admin_token, {**SAMPLE_INVOICE, "invoice_number": "NOTIF-101"})
    assert await _unread_count(client, contador_token) == 1
    notifications = await _list_notifications(client, contador_token)
    assert notifications[0]["type"] == "invoice_created"
    assert "NOTIF-101" in notifications[0]["message"]


@pytest.mark.asyncio
async def test_status_and_assignment_notifications(
    client: AsyncClient,
    admin_token: str,
    contador_token: str,
    asistente_token: str,
    asistente_user,
):
    created = await _create_invoice(
        client,
        admin_token,
        {**SAMPLE_INVOICE, "invoice_number": "NOTIF-201", "assigned_user_ids": [asistente_user.id]},
    )
    invoice_id = created["id"]

    update_resp = await client.put(
        f"/api/invoices/{invoice_id}",
        json={"status": "pagada", "assigned_user_ids": []},
        headers=auth(admin_token),
    )
    assert update_resp.status_code == 200

    contador_notifications = await _list_notifications(client, contador_token)
    assert any(n["type"] == "invoice_status_changed" for n in contador_notifications)
    assert any(n["type"] == "invoice_updated" for n in contador_notifications)

    asistente_notifications = await _list_notifications(client, asistente_token)
    assert any(n["type"] == "invoice_assigned" for n in asistente_notifications)
    assert any(n["type"] == "invoice_unassigned" for n in asistente_notifications)


@pytest.mark.asyncio
async def test_mark_read_and_mark_all(
    client: AsyncClient,
    admin_token: str,
    contador_token: str,
):
    await _create_invoice(client, admin_token, {**SAMPLE_INVOICE, "invoice_number": "NOTIF-301"})
    await _create_invoice(client, admin_token, {**SAMPLE_INVOICE, "invoice_number": "NOTIF-302"})
    items = await _list_notifications(client, contador_token)
    assert len(items) >= 2

    one_id = items[0]["id"]
    one_resp = await client.post(f"/api/notifications/{one_id}/read", headers=auth(contador_token))
    assert one_resp.status_code == 200
    assert one_resp.json()["is_read"] is True

    all_resp = await client.post("/api/notifications/read-all", headers=auth(contador_token))
    assert all_resp.status_code == 200
    assert all_resp.json()["unread"] == 0

    unread_now = await _unread_count(client, contador_token)
    assert unread_now == 0


@pytest.mark.asyncio
async def test_notifications_forbidden_for_platform_admin(
    client: AsyncClient,
    platform_token: str,
):
    resp = await client.get("/api/notifications", headers=auth(platform_token))
    assert resp.status_code == 403
