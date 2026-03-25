"""
Tests for POST /api/auth/login — Sistema de Gestión de Facturas.
"""
import pytest
from httpx import AsyncClient

from tests.conftest import TEST_ORG_SLUG


@pytest.mark.asyncio
async def test_login_success(client: AsyncClient, admin_user):
    resp = await client.post(
        "/api/auth/login",
        json={
            "organization_slug": TEST_ORG_SLUG,
            "username": "admin",
            "password": "admin123",
        },
    )
    assert resp.status_code == 200
    body = resp.json()
    assert "access_token" in body
    assert body["token_type"] == "bearer"


@pytest.mark.asyncio
async def test_login_wrong_password(client: AsyncClient, admin_user):
    resp = await client.post(
        "/api/auth/login",
        json={
            "organization_slug": TEST_ORG_SLUG,
            "username": "admin",
            "password": "wrongpassword",
        },
    )
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_login_unknown_user(client: AsyncClient, tenant_org):
    resp = await client.post(
        "/api/auth/login",
        json={
            "organization_slug": TEST_ORG_SLUG,
            "username": "nobody",
            "password": "pass",
        },
    )
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_protected_route_no_token(client: AsyncClient):
    resp = await client.get("/api/invoices")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_protected_route_invalid_token(client: AsyncClient):
    resp = await client.get(
        "/api/invoices",
        headers={"Authorization": "Bearer invalid.token.here"},
    )
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_get_me(client: AsyncClient, admin_token: str):
    resp = await client.get(
        "/api/users/me",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["username"] == "admin"
    assert body["role"] == "administrador"
    assert body["organization"]["slug"] == TEST_ORG_SLUG
