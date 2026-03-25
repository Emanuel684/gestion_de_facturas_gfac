"""
Tests for /api/organizations — platform admin only.
"""
import pytest
from httpx import AsyncClient


def auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


@pytest.mark.asyncio
async def test_tenant_cannot_list_organizations(client: AsyncClient, admin_token: str):
    resp = await client.get("/api/organizations", headers=auth(admin_token))
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_platform_lists_organizations(client: AsyncClient, platform_token: str):
    resp = await client.get("/api/organizations", headers=auth(platform_token))
    assert resp.status_code == 200
    assert resp.json() == []


@pytest.mark.asyncio
async def test_platform_creates_organization(client: AsyncClient, platform_token: str):
    resp = await client.post(
        "/api/organizations",
        json={
            "name": "Nueva Empresa SA",
            "slug": "nueva-empresa",
            "plan_tier": "profesional",
            "admin_username": "orgadmin",
            "admin_email": "org@nueva.example.com",
            "admin_password": "secret12",
        },
        headers=auth(platform_token),
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["slug"] == "nueva-empresa"
    assert body["plan_tier"] == "profesional"

    login = await client.post(
        "/api/auth/login",
        json={
            "organization_slug": "nueva-empresa",
            "username": "orgadmin",
            "password": "secret12",
        },
    )
    assert login.status_code == 200
