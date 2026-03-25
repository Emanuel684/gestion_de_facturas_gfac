"""
Tests for /api/users — user listing and creation for SGF.
"""
import pytest
from httpx import AsyncClient


def auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


# ── List ─────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_list_users(client: AsyncClient, admin_token: str):
    resp = await client.get("/api/users", headers=auth(admin_token))
    assert resp.status_code == 200
    users = resp.json()
    assert isinstance(users, list)
    assert len(users) >= 1
    assert users[0]["username"] == "admin"


@pytest.mark.asyncio
async def test_list_users_unauthenticated(client: AsyncClient):
    resp = await client.get("/api/users")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_get_me(client: AsyncClient, admin_token: str):
    resp = await client.get("/api/users/me", headers=auth(admin_token))
    assert resp.status_code == 200
    body = resp.json()
    assert body["username"] == "admin"
    assert body["role"] == "administrador"
    assert body["organization"]["slug"] == "test-org"


# ── Create ────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_create_user_as_admin(client: AsyncClient, admin_token: str):
    resp = await client.post(
        "/api/users",
        json={
            "username": "nuevo_usuario",
            "email": "nuevo@example.com",
            "password": "secret123",
            "role": "contador",
        },
        headers=auth(admin_token),
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["username"] == "nuevo_usuario"
    assert body["email"] == "nuevo@example.com"
    assert body["role"] == "contador"
    assert body["is_active"] is True
    assert "id" in body


@pytest.mark.asyncio
async def test_create_user_default_role(client: AsyncClient, admin_token: str):
    resp = await client.post(
        "/api/users",
        json={
            "username": "default_role",
            "email": "default@example.com",
            "password": "secret123",
        },
        headers=auth(admin_token),
    )
    assert resp.status_code == 201
    assert resp.json()["role"] == "asistente"


@pytest.mark.asyncio
async def test_create_user_duplicate_username(client: AsyncClient, admin_token: str):
    await client.post(
        "/api/users",
        json={
            "username": "duplicado",
            "email": "dup1@example.com",
            "password": "secret123",
        },
        headers=auth(admin_token),
    )
    resp = await client.post(
        "/api/users",
        json={
            "username": "duplicado",
            "email": "dup2@example.com",
            "password": "secret123",
        },
        headers=auth(admin_token),
    )
    assert resp.status_code == 409


@pytest.mark.asyncio
async def test_create_user_duplicate_email(client: AsyncClient, admin_token: str):
    await client.post(
        "/api/users",
        json={
            "username": "user_a",
            "email": "same@example.com",
            "password": "secret123",
        },
        headers=auth(admin_token),
    )
    resp = await client.post(
        "/api/users",
        json={
            "username": "user_b",
            "email": "same@example.com",
            "password": "secret123",
        },
        headers=auth(admin_token),
    )
    assert resp.status_code == 409


@pytest.mark.asyncio
async def test_create_user_short_password(client: AsyncClient, admin_token: str):
    resp = await client.post(
        "/api/users",
        json={
            "username": "shortpw",
            "email": "short@example.com",
            "password": "123",
        },
        headers=auth(admin_token),
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_create_user_short_username(client: AsyncClient, admin_token: str):
    resp = await client.post(
        "/api/users",
        json={
            "username": "ab",
            "email": "short_user@example.com",
            "password": "secret123",
        },
        headers=auth(admin_token),
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_create_user_invalid_email(client: AsyncClient, admin_token: str):
    resp = await client.post(
        "/api/users",
        json={
            "username": "bad_email",
            "email": "not-an-email",
            "password": "secret123",
        },
        headers=auth(admin_token),
    )
    assert resp.status_code == 422


# ── Permission checks ────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_contador_cannot_create_user(client: AsyncClient, contador_token: str):
    resp = await client.post(
        "/api/users",
        json={
            "username": "forbidden",
            "email": "forbidden@example.com",
            "password": "secret123",
        },
        headers=auth(contador_token),
    )
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_asistente_cannot_create_user(client: AsyncClient, asistente_token: str):
    resp = await client.post(
        "/api/users",
        json={
            "username": "forbidden2",
            "email": "forbidden2@example.com",
            "password": "secret123",
        },
        headers=auth(asistente_token),
    )
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_created_user_can_login(client: AsyncClient, admin_token: str):
    """Verify that a newly created user can actually authenticate."""
    await client.post(
        "/api/users",
        json={
            "username": "login_test",
            "email": "login_test@example.com",
            "password": "mypassword",
            "role": "asistente",
        },
        headers=auth(admin_token),
    )

    login_resp = await client.post(
        "/api/auth/login",
        json={
            "organization_slug": "test-org",
            "username": "login_test",
            "password": "mypassword",
        },
    )
    assert login_resp.status_code == 200
    assert "access_token" in login_resp.json()


# ── Delete ────────────────────────────────────────────────────────────────────

SAMPLE_INVOICE = {
    "invoice_number": "FAC-DEL-USER",
    "supplier": "Proveedor X",
    "description": "Test",
    "amount": 100.0,
}


@pytest.mark.asyncio
async def test_delete_user_as_admin_cascades_created_invoices(client: AsyncClient, admin_token: str):
    """Deleting a user removes every invoice they created."""
    await client.post(
        "/api/users",
        json={
            "username": "user_to_delete",
            "email": "del_user@example.com",
            "password": "secret123",
            "role": "asistente",
        },
        headers=auth(admin_token),
    )
    login = await client.post(
        "/api/auth/login",
        json={
            "organization_slug": "test-org",
            "username": "user_to_delete",
            "password": "secret123",
        },
    )
    user_token = login.json()["access_token"]

    create_inv = await client.post(
        "/api/invoices",
        json=SAMPLE_INVOICE,
        headers=auth(user_token),
    )
    assert create_inv.status_code == 201

    users_resp = await client.get("/api/users", headers=auth(admin_token))
    uid = next(u["id"] for u in users_resp.json() if u["username"] == "user_to_delete")

    del_resp = await client.delete(f"/api/users/{uid}", headers=auth(admin_token))
    assert del_resp.status_code == 204

    list_resp = await client.get("/api/invoices", headers=auth(admin_token))
    assert list_resp.status_code == 200
    numbers = [item["invoice_number"] for item in list_resp.json()["items"]]
    assert "FAC-DEL-USER" not in numbers


@pytest.mark.asyncio
async def test_delete_user_removes_assignee_rows(client: AsyncClient, admin_token: str, contador_user):
    """User deleted only as assignee: invoice remains, assignment row is gone."""
    create = await client.post(
        "/api/invoices",
        json={
            **SAMPLE_INVOICE,
            "invoice_number": "FAC-KEEP-1",
            "assigned_user_ids": [contador_user.id],
        },
        headers=auth(admin_token),
    )
    assert create.status_code == 201
    inv_id = create.json()["id"]
    assert any(a["id"] == contador_user.id for a in create.json()["assigned_users"])

    del_resp = await client.delete(f"/api/users/{contador_user.id}", headers=auth(admin_token))
    assert del_resp.status_code == 204

    get_inv = await client.get(f"/api/invoices/{inv_id}", headers=auth(admin_token))
    assert get_inv.status_code == 200
    assert get_inv.json()["assigned_users"] == []


@pytest.mark.asyncio
async def test_delete_user_cannot_delete_self(client: AsyncClient, admin_token: str, admin_user):
    resp = await client.delete(f"/api/users/{admin_user.id}", headers=auth(admin_token))
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_delete_second_administrator_succeeds(client: AsyncClient, admin_token: str):
    """With two admins, the seed admin can delete the other."""
    await client.post(
        "/api/users",
        json={
            "username": "admin_extra",
            "email": "admin_extra@example.com",
            "password": "secret123",
            "role": "administrador",
        },
        headers=auth(admin_token),
    )
    users = await client.get("/api/users", headers=auth(admin_token))
    extra_id = next(u["id"] for u in users.json() if u["username"] == "admin_extra")
    resp = await client.delete(f"/api/users/{extra_id}", headers=auth(admin_token))
    assert resp.status_code == 204


@pytest.mark.asyncio
async def test_delete_user_not_found(client: AsyncClient, admin_token: str):
    resp = await client.delete("/api/users/999999", headers=auth(admin_token))
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_contador_cannot_delete_user(client: AsyncClient, contador_token: str, asistente_user):
    resp = await client.delete(f"/api/users/{asistente_user.id}", headers=auth(contador_token))
    assert resp.status_code == 403
