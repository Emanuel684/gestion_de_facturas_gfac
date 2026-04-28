"""Helpers to create user-facing notifications."""
from __future__ import annotations

from collections.abc import Iterable

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models import Notification, NotificationType, User


async def create_notification_for_users(
    db: AsyncSession,
    *,
    organization_id: int,
    user_ids: Iterable[int],
    notification_type: NotificationType,
    title: str,
    message: str,
    invoice_id: int | None = None,
    payload: dict | None = None,
) -> None:
    unique_user_ids = {int(uid) for uid in user_ids}
    if not unique_user_ids:
        return
    rows = await db.execute(
        select(User.id).where(
            User.organization_id == organization_id,
            User.is_active == True,  # noqa: E712
            User.id.in_(unique_user_ids),
        )
    )
    valid_user_ids = rows.scalars().all()
    for uid in valid_user_ids:
        db.add(
            Notification(
                organization_id=organization_id,
                user_id=uid,
                type=notification_type,
                title=title,
                message=message,
                invoice_id=invoice_id,
                payload=payload,
            )
        )
    await db.flush()


async def create_notification_for_org(
    db: AsyncSession,
    *,
    organization_id: int,
    exclude_user_id: int | None,
    notification_type: NotificationType,
    title: str,
    message: str,
    invoice_id: int | None = None,
    payload: dict | None = None,
) -> None:
    q = select(User.id).where(
        User.organization_id == organization_id,
        User.is_active == True,  # noqa: E712
    )
    if exclude_user_id is not None:
        q = q.where(User.id != exclude_user_id)
    rows = await db.execute(q)
    user_ids = rows.scalars().all()
    await create_notification_for_users(
        db,
        organization_id=organization_id,
        user_ids=user_ids,
        notification_type=notification_type,
        title=title,
        message=message,
        invoice_id=invoice_id,
        payload=payload,
    )
