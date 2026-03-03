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


# ── Create ────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_create_user_as_admin(client: AsyncClient, admin_token: str):
    resp = await client.post(
        "/api/users",
        json={
            "username": "nuevo_usuario",
            "email": "nuevo@sgf.local",
            "password": "secret123",
            "role": "contador",
        },
        headers=auth(admin_token),
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["username"] == "nuevo_usuario"
    assert body["email"] == "nuevo@sgf.local"
    assert body["role"] == "contador"
    assert body["is_active"] is True
    assert "id" in body


@pytest.mark.asyncio
async def test_create_user_default_role(client: AsyncClient, admin_token: str):
    resp = await client.post(
        "/api/users",
        json={
            "username": "default_role",
            "email": "default@sgf.local",
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
            "email": "dup1@sgf.local",
            "password": "secret123",
        },
        headers=auth(admin_token),
    )
    resp = await client.post(
        "/api/users",
        json={
            "username": "duplicado",
            "email": "dup2@sgf.local",
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
            "email": "same@sgf.local",
            "password": "secret123",
        },
        headers=auth(admin_token),
    )
    resp = await client.post(
        "/api/users",
        json={
            "username": "user_b",
            "email": "same@sgf.local",
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
            "email": "short@sgf.local",
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
            "email": "short_user@sgf.local",
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
            "email": "forbidden@sgf.local",
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
            "email": "forbidden2@sgf.local",
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
            "email": "login_test@sgf.local",
            "password": "mypassword",
            "role": "asistente",
        },
        headers=auth(admin_token),
    )

    login_resp = await client.post(
        "/api/auth/login",
        data={"username": "login_test", "password": "mypassword"},
    )
    assert login_resp.status_code == 200
    assert "access_token" in login_resp.json()
