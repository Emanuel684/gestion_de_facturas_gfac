"""User notifications API."""
from datetime import datetime, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from src.db import get_db
from src.dependencies import require_active_tenant_user
from src.models import Notification, User
from src.schemas import NotificationPage, NotificationUnreadCount, NotificationOut

router = APIRouter(prefix="/api/notifications", tags=["notifications"])


@router.get("", response_model=NotificationPage)
async def list_notifications(
    page: Annotated[int, Query(ge=0)] = 0,
    page_size: Annotated[int, Query(ge=1, le=100, alias="page_size")] = 20,
    unread_only: bool = False,
    current_user: User = Depends(require_active_tenant_user),
    db: AsyncSession = Depends(get_db),
) -> NotificationPage:
    query = select(Notification).where(
        Notification.organization_id == current_user.organization_id,
        Notification.user_id == current_user.id,
    )
    if unread_only:
        query = query.where(Notification.is_read == False)  # noqa: E712
    query = query.order_by(Notification.created_at.desc()).offset(page * page_size).limit(page_size + 1)
    result = await db.execute(query)
    rows = result.scalars().all()
    has_next = len(rows) > page_size
    return NotificationPage(
        items=[NotificationOut.model_validate(n) for n in rows[:page_size]],
        has_next=has_next,
        page=page,
        page_size=page_size,
    )


@router.get("/unread-count", response_model=NotificationUnreadCount)
async def get_unread_count(
    current_user: User = Depends(require_active_tenant_user),
    db: AsyncSession = Depends(get_db),
) -> NotificationUnreadCount:
    result = await db.execute(
        select(func.count())
        .select_from(Notification)
        .where(
            Notification.organization_id == current_user.organization_id,
            Notification.user_id == current_user.id,
            Notification.is_read == False,  # noqa: E712
        )
    )
    return NotificationUnreadCount(unread=result.scalar_one())


@router.post("/{notification_id}/read", response_model=NotificationOut)
async def mark_notification_as_read(
    notification_id: int,
    current_user: User = Depends(require_active_tenant_user),
    db: AsyncSession = Depends(get_db),
) -> NotificationOut:
    now = datetime.now(timezone.utc)
    await db.execute(
        update(Notification)
        .where(
            Notification.id == notification_id,
            Notification.organization_id == current_user.organization_id,
            Notification.user_id == current_user.id,
        )
        .values(is_read=True, read_at=now)
    )
    await db.commit()
    row = await db.execute(
        select(Notification).where(
            Notification.id == notification_id,
            Notification.organization_id == current_user.organization_id,
            Notification.user_id == current_user.id,
        )
    )
    notification = row.scalar_one_or_none()
    if notification is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Notificación no encontrada")
    return NotificationOut.model_validate(notification)


@router.post("/read-all", response_model=NotificationUnreadCount)
async def mark_all_notifications_as_read(
    current_user: User = Depends(require_active_tenant_user),
    db: AsyncSession = Depends(get_db),
) -> NotificationUnreadCount:
    now = datetime.now(timezone.utc)
    await db.execute(
        update(Notification)
        .where(
            Notification.organization_id == current_user.organization_id,
            Notification.user_id == current_user.id,
            Notification.is_read == False,  # noqa: E712
        )
        .values(is_read=True, read_at=now)
    )
    await db.commit()
    return NotificationUnreadCount(unread=0)
