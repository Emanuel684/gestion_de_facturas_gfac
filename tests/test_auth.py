"""
Tests for POST /api/auth/login
"""
import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_login_success(client: AsyncClient, owner_user):
    resp = await client.post(
        "/api/auth/login",
        data={"username": "admin", "password": "admin123"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert "access_token" in body
    assert body["token_type"] == "bearer"


@pytest.mark.asyncio
async def test_login_wrong_password(client: AsyncClient, owner_user):
    resp = await client.post(
        "/api/auth/login",
        data={"username": "admin", "password": "wrongpassword"},
    )
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_login_unknown_user(client: AsyncClient):
    resp = await client.post(
        "/api/auth/login",
        data={"username": "nobody", "password": "pass"},
    )
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_protected_route_no_token(client: AsyncClient):
    resp = await client.get("/api/tasks")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_protected_route_invalid_token(client: AsyncClient):
    resp = await client.get(
        "/api/tasks",
        headers={"Authorization": "Bearer invalid.token.here"},
    )
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_get_me(client: AsyncClient, owner_token: str):
    resp = await client.get(
        "/api/users/me",
        headers={"Authorization": f"Bearer {owner_token}"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["username"] == "admin"
    assert body["role"] == "owner"
