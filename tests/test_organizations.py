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
    token = login.json()["access_token"]
    sub_me = await client.get("/api/billing/subscription/me", headers=auth(token))
    assert sub_me.status_code == 200
    assert sub_me.json()["plan_tier"] == "profesional"


@pytest.mark.asyncio
async def test_platform_deletes_organization(client: AsyncClient, platform_token: str):
    create = await client.post(
        "/api/organizations",
        json={
            "name": "To Delete SA",
            "slug": "to-delete-org",
            "plan_tier": "basico",
            "admin_username": "deladmin",
            "admin_email": "del@example.com",
            "admin_password": "secret12",
        },
        headers=auth(platform_token),
    )
    assert create.status_code == 201
    org_id = create.json()["id"]

    del_resp = await client.delete(f"/api/organizations/{org_id}", headers=auth(platform_token))
    assert del_resp.status_code == 204

    lst = await client.get("/api/organizations", headers=auth(platform_token))
    assert lst.status_code == 200
    slugs = [o["slug"] for o in lst.json()]
    assert "to-delete-org" not in slugs


@pytest.mark.asyncio
async def test_tenant_cannot_delete_organization(client: AsyncClient, platform_token: str, admin_token: str):
    create = await client.post(
        "/api/organizations",
        json={
            "name": "Org Tenant Del",
            "slug": "tenant-del-test",
            "plan_tier": "basico",
            "admin_username": "tenantx",
            "admin_email": "tenantx@example.com",
            "admin_password": "secret12",
        },
        headers=auth(platform_token),
    )
    assert create.status_code == 201
    org_id = create.json()["id"]

    resp = await client.delete(f"/api/organizations/{org_id}", headers=auth(admin_token))
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_cannot_delete_platform_organization(client: AsyncClient, platform_token: str, platform_org):
    resp = await client.delete(f"/api/organizations/{platform_org.id}", headers=auth(platform_token))
    assert resp.status_code == 403
