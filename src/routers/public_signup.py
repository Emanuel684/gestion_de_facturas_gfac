"""Public signup flow for new tenant customers."""
from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth import hash_password
from src.billing import (
    PLAN_PRICES_COP,
    build_checkout_token,
    ensure_utc,
    grace_end_from,
    now_utc,
    period_end_from,
    recompute_subscription_status,
)
from src.db import get_db
from src.models import (
    CheckoutSession,
    CheckoutSessionStatus,
    Organization,
    Payment,
    PaymentStatus,
    Subscription,
    SubscriptionStatus,
    User,
    UserRole,
)
from src.schemas import CheckoutActionIn, CheckoutSessionOut, PublicSignupIn, PublicSignupOut, SubscriptionOut

router = APIRouter(prefix="/api/public", tags=["public"])


@router.post("/signup", response_model=PublicSignupOut, status_code=status.HTTP_201_CREATED)
async def public_signup(payload: PublicSignupIn, db: AsyncSession = Depends(get_db)) -> PublicSignupOut:
    existing = await db.execute(select(Organization).where(Organization.slug == payload.slug))
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Ya existe una organización con slug '{payload.slug}'",
        )

    org = Organization(name=payload.name, slug=payload.slug, plan_tier=payload.plan_tier)
    db.add(org)
    await db.flush()

    admin = User(
        organization_id=org.id,
        username=payload.admin_username,
        email=str(payload.admin_email),
        hashed_password=hash_password(payload.admin_password),
        role=UserRole.administrador,
    )
    db.add(admin)

    now = now_utc()
    # Allow access for initial 10-day grace before first payment.
    subscription = Subscription(
        organization_id=org.id,
        plan_tier=payload.plan_tier,
        status=SubscriptionStatus.past_due,
        next_due_date=now,
        grace_expires_at=now + timedelta(days=10),
    )
    db.add(subscription)

    token = build_checkout_token()
    session = CheckoutSession(
        organization_id=org.id,
        plan_tier=payload.plan_tier,
        amount=PLAN_PRICES_COP[payload.plan_tier],
        currency="COP",
        session_token=token,
        expires_at=now + timedelta(hours=2),
    )
    db.add(session)
    await db.commit()

    return PublicSignupOut(
        organization_id=org.id,
        organization_slug=org.slug,
        checkout_session_token=token,
        checkout_url=f"/checkout/mock/{token}",
    )


@router.get("/checkout/{session_token}", response_model=CheckoutSessionOut)
async def get_public_checkout(session_token: str, db: AsyncSession = Depends(get_db)) -> CheckoutSessionOut:
    result = await db.execute(select(CheckoutSession).where(CheckoutSession.session_token == session_token))
    session = result.scalar_one_or_none()
    if not session:
        raise HTTPException(status_code=404, detail="Checkout no encontrado")
    if session.status == CheckoutSessionStatus.created and ensure_utc(session.expires_at) < now_utc():
        session.status = CheckoutSessionStatus.expired
        await db.commit()
    return CheckoutSessionOut.model_validate(session)


@router.post("/checkout/{session_token}/complete", response_model=SubscriptionOut)
async def complete_public_checkout(
    session_token: str,
    payload: CheckoutActionIn,
    db: AsyncSession = Depends(get_db),
) -> SubscriptionOut:
    result = await db.execute(select(CheckoutSession).where(CheckoutSession.session_token == session_token))
    session = result.scalar_one_or_none()
    if not session:
        raise HTTPException(status_code=404, detail="Checkout no encontrado")
    if session.status != CheckoutSessionStatus.created:
        raise HTTPException(status_code=400, detail="Checkout ya procesado")

    now = now_utc()
    if ensure_utc(session.expires_at) < now:
        session.status = CheckoutSessionStatus.expired
        await db.commit()
        raise HTTPException(status_code=400, detail="Checkout expirado")

    r_sub = await db.execute(
        select(Subscription).where(Subscription.organization_id == session.organization_id)
    )
    sub = r_sub.scalar_one_or_none()
    if sub is None:
        raise HTTPException(status_code=404, detail="Suscripción no encontrada")

    payment = Payment(
        organization_id=session.organization_id,
        subscription_id=sub.id,
        amount=session.amount,
        currency=session.currency,
        status=payload.outcome,
        provider="mock",
        provider_reference=f"mock_{session.id}_{int(now.timestamp())}",
    )
    db.add(payment)

    if payload.outcome == PaymentStatus.paid:
        period_start = now
        period_end = period_end_from(period_start)
        org_row = await db.execute(select(Organization).where(Organization.id == session.organization_id))
        org = org_row.scalar_one()
        org.plan_tier = session.plan_tier
        sub.plan_tier = session.plan_tier
        sub.status = SubscriptionStatus.active
        sub.current_period_start = period_start
        sub.current_period_end = period_end
        sub.next_due_date = period_end
        sub.grace_expires_at = grace_end_from(period_end)
        sub.last_paid_at = now
        payment.paid_at = now
    else:
        recompute_subscription_status(sub, now)

    session.status = CheckoutSessionStatus.completed
    session.completed_at = now
    await db.commit()
    await db.refresh(sub)
    return SubscriptionOut.model_validate(sub)

