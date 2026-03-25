from datetime import timedelta

import pytest
from httpx import AsyncClient

from src.billing import now_utc, recompute_subscription_status
from src.models import PlanTier, Subscription, SubscriptionStatus


def auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


@pytest.mark.asyncio
async def test_public_signup_and_mock_checkout_paid(client: AsyncClient):
    signup = await client.post(
        "/api/public/signup",
        json={
            "name": "Cliente Uno",
            "slug": "cliente-uno",
            "plan_tier": "profesional",
            "admin_username": "owner",
            "admin_email": "owner@example.com",
            "admin_password": "secret123",
        },
    )
    assert signup.status_code == 201
    token = signup.json()["checkout_session_token"]

    checkout = await client.get(f"/api/public/checkout/{token}")
    assert checkout.status_code == 200
    assert checkout.json()["status"] == "created"

    complete = await client.post(
        f"/api/public/checkout/{token}/complete",
        json={"outcome": "paid"},
    )
    assert complete.status_code == 200
    assert complete.json()["status"] == "active"

    login = await client.post(
        "/api/auth/login",
        json={
            "organization_slug": "cliente-uno",
            "username": "owner",
            "password": "secret123",
        },
    )
    assert login.status_code == 200


@pytest.mark.asyncio
async def test_billing_payment_history_for_tenant(client: AsyncClient, admin_token: str):
    checkout = await client.post(
        "/api/billing/checkout",
        json={"plan_tier": "basico"},
        headers=auth(admin_token),
    )
    assert checkout.status_code == 200
    session_token = checkout.json()["session"]["session_token"]

    complete = await client.post(
        f"/api/billing/checkout/{session_token}/complete",
        json={"outcome": "failed"},
        headers=auth(admin_token),
    )
    assert complete.status_code == 200

    payments = await client.get("/api/billing/payments", headers=auth(admin_token))
    assert payments.status_code == 200
    assert len(payments.json()) >= 1


def test_recompute_subscription_within_grace_is_past_due():
    now = now_utc()
    sub = Subscription(
        organization_id=1,
        plan_tier=PlanTier.basico,
        status=SubscriptionStatus.active,
        next_due_date=now - timedelta(days=5),
        grace_expires_at=now + timedelta(days=5),
    )
    recompute_subscription_status(sub, now)
    assert sub.status == SubscriptionStatus.past_due


def test_recompute_subscription_after_grace_is_suspended():
    now = now_utc()
    sub = Subscription(
        organization_id=1,
        plan_tier=PlanTier.basico,
        status=SubscriptionStatus.active,
        next_due_date=now - timedelta(days=5),
        grace_expires_at=now - timedelta(days=1),
    )
    recompute_subscription_status(sub, now)
    assert sub.status == SubscriptionStatus.suspended

