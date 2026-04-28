import pytest

from src.config import settings
from src.extraction import extract_from_file


def _login_payload(password: str = "bad") -> dict:
    return {"organization_slug": "test-org", "username": "admin", "password": password}


@pytest.mark.asyncio
async def test_login_rate_limit(client):
    original = settings.login_rate_limit_max_attempts
    settings.login_rate_limit_max_attempts = 2
    try:
        r1 = await client.post("/api/auth/login", json=_login_payload())
        assert r1.status_code == 401
        r2 = await client.post("/api/auth/login", json=_login_payload())
        assert r2.status_code == 401
        r3 = await client.post("/api/auth/login", json=_login_payload())
        assert r3.status_code == 429
    finally:
        settings.login_rate_limit_max_attempts = original


@pytest.mark.asyncio
async def test_security_headers_present(client):
    resp = await client.get("/health")
    assert resp.status_code == 200
    assert resp.headers.get("x-content-type-options") == "nosniff"
    assert resp.headers.get("x-frame-options") == "DENY"
    assert "default-src 'self'" in (resp.headers.get("content-security-policy") or "")


@pytest.mark.asyncio
async def test_public_checkout_disabled_in_secure_mode(client):
    original = settings.enable_mock_checkout
    settings.enable_mock_checkout = False
    try:
        resp = await client.post(
            "/api/public/signup",
            json={
                "name": "Nueva Org",
                "slug": "org-secure-test",
                "plan_tier": "basico",
                "admin_username": "nuevoadmin",
                "admin_email": "nuevoadmin@example.com",
                "admin_password": "secret123",
            },
        )
        assert resp.status_code == 503
    finally:
        settings.enable_mock_checkout = original


def test_extract_from_file_hides_raw_text_by_default(monkeypatch):
    monkeypatch.setattr(settings, "return_raw_text_in_upload", False)
    monkeypatch.setattr("src.extraction.extract_text_from_image", lambda _: "Factura No FAC-1 Proveedor ACME")
    result = extract_from_file(b"\xff\xd8\xff\xe0fake", "image/jpeg", "f.jpg")
    assert "raw_text" not in result
    assert result["extraction_method"] == "regex"
