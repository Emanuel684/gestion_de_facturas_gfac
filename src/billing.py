"""Billing helpers for mock checkout and subscription lifecycle."""
from datetime import datetime, timedelta, timezone
from decimal import Decimal
import secrets

from src.models import PlanTier, Subscription, SubscriptionStatus

PLAN_PRICES_COP: dict[PlanTier, Decimal] = {
    PlanTier.basico: Decimal("29000.00"),
    PlanTier.profesional: Decimal("79000.00"),
    PlanTier.empresarial: Decimal("149000.00"),
}

BILLING_CYCLE_DAYS = 30
GRACE_DAYS = 10


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


def ensure_utc(dt: datetime | None) -> datetime | None:
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt


def build_checkout_token() -> str:
    return secrets.token_urlsafe(24)


def period_end_from(start: datetime) -> datetime:
    return start + timedelta(days=BILLING_CYCLE_DAYS)


def grace_end_from(next_due_date: datetime) -> datetime:
    return next_due_date + timedelta(days=GRACE_DAYS)


def recompute_subscription_status(subscription: Subscription, now: datetime | None = None) -> None:
    """Compute status according to due date and grace period."""
    now = now or now_utc()
    if subscription.status == SubscriptionStatus.canceled:
        return
    next_due_date = ensure_utc(subscription.next_due_date)
    grace_expires_at = ensure_utc(subscription.grace_expires_at)
    if next_due_date is None:
        subscription.status = SubscriptionStatus.past_due
        return
    if now <= next_due_date:
        subscription.status = SubscriptionStatus.active
        return
    if grace_expires_at and now <= grace_expires_at:
        subscription.status = SubscriptionStatus.past_due
        return
    subscription.status = SubscriptionStatus.suspended

