"""Tenant billing endpoints + mock checkout lifecycle."""
from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

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
from src.dependencies import require_active_tenant_user, require_tenant_user
from src.models import (
    CheckoutSession,
    CheckoutSessionStatus,
    Organization,
    Payment,
    PaymentStatus,
    Subscription,
    SubscriptionStatus,
    User,
)
from src.schemas import (
    CheckoutActionIn,
    CheckoutCreateIn,
    CheckoutCreateOut,
    CheckoutSessionOut,
    PaymentOut,
    SubscriptionOut,
)

router = APIRouter(prefix="/api/billing", tags=["billing"])


async def _get_subscription_for_org(org_id: int, db: AsyncSession) -> Subscription:
    result = await db.execute(
        select(Subscription).where(Subscription.organization_id == org_id).order_by(desc(Subscription.id))
    )
    sub = result.scalars().first()
    if not sub:
        raise HTTPException(status_code=404, detail="Suscripción no encontrada")
    return sub


@router.get("/subscription/me", response_model=SubscriptionOut)
async def get_subscription_me(
    current_user: User = Depends(require_tenant_user),
    db: AsyncSession = Depends(get_db),
) -> SubscriptionOut:
    sub = await _get_subscription_for_org(current_user.organization_id, db)
    recompute_subscription_status(sub)
    await db.commit()
    await db.refresh(sub)
    return SubscriptionOut.model_validate(sub)


@router.get("/payments", response_model=list[PaymentOut])
async def list_payments(
    current_user: User = Depends(require_tenant_user),
    db: AsyncSession = Depends(get_db),
) -> list[PaymentOut]:
    result = await db.execute(
        select(Payment)
        .where(Payment.organization_id == current_user.organization_id)
        .order_by(Payment.created_at.desc())
    )
    return [PaymentOut.model_validate(p) for p in result.scalars().all()]


@router.post("/checkout", response_model=CheckoutCreateOut)
async def create_checkout(
    payload: CheckoutCreateIn,
    current_user: User = Depends(require_tenant_user),
    db: AsyncSession = Depends(get_db),
) -> CheckoutCreateOut:
    token = build_checkout_token()
    now = now_utc()
    session = CheckoutSession(
        organization_id=current_user.organization_id,
        plan_tier=payload.plan_tier,
        amount=PLAN_PRICES_COP[payload.plan_tier],
        currency="COP",
        session_token=token,
        status=CheckoutSessionStatus.created,
        expires_at=now + timedelta(hours=2),
    )
    db.add(session)
    await db.commit()
    return CheckoutCreateOut(
        checkout_url=f"/checkout/mock/{token}",
        session=CheckoutSessionOut.model_validate(session),
    )


@router.get("/checkout/{session_token}", response_model=CheckoutSessionOut)
async def get_checkout(
    session_token: str,
    current_user: User = Depends(require_tenant_user),
    db: AsyncSession = Depends(get_db),
) -> CheckoutSessionOut:
    result = await db.execute(
        select(CheckoutSession).where(
            CheckoutSession.session_token == session_token,
            CheckoutSession.organization_id == current_user.organization_id,
        )
    )
    session = result.scalar_one_or_none()
    if not session:
        raise HTTPException(status_code=404, detail="Checkout no encontrado")
    if session.status == CheckoutSessionStatus.created and ensure_utc(session.expires_at) < now_utc():
        session.status = CheckoutSessionStatus.expired
        await db.commit()
    return CheckoutSessionOut.model_validate(session)


@router.post("/checkout/{session_token}/complete", response_model=SubscriptionOut)
async def complete_checkout(
    session_token: str,
    payload: CheckoutActionIn,
    current_user: User = Depends(require_tenant_user),
    db: AsyncSession = Depends(get_db),
) -> SubscriptionOut:
    result = await db.execute(
        select(CheckoutSession).where(
            CheckoutSession.session_token == session_token,
            CheckoutSession.organization_id == current_user.organization_id,
        )
    )
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

    sub = await _get_subscription_for_org(current_user.organization_id, db)
    payment = Payment(
        organization_id=current_user.organization_id,
        subscription_id=sub.id,
        amount=session.amount,
        currency=session.currency,
        status=payload.outcome,
        provider="mock",
        provider_reference=f"mock_{session.id}_{int(now.timestamp())}",
    )
    db.add(payment)

    if payload.outcome == PaymentStatus.paid:
        start = now
        end = period_end_from(start)
        org_row = await db.execute(select(Organization).where(Organization.id == current_user.organization_id))
        org = org_row.scalar_one()
        org.plan_tier = session.plan_tier
        sub.plan_tier = session.plan_tier
        sub.status = SubscriptionStatus.active
        sub.current_period_start = start
        sub.current_period_end = end
        sub.next_due_date = end
        sub.grace_expires_at = grace_end_from(end)
        sub.last_paid_at = now
        payment.paid_at = now
    else:
        recompute_subscription_status(sub, now)

    session.status = CheckoutSessionStatus.completed
    session.completed_at = now
    await db.commit()
    await db.refresh(sub)
    return SubscriptionOut.model_validate(sub)


@router.get("/access-check")
async def billing_access_check(_: User = Depends(require_active_tenant_user)) -> dict:
    return {"access": "ok"}

