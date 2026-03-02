"""
Tasks router — full CRUD with role-based access control.

Permission rules:
  - owner role: can see ALL tasks, create/edit/delete any task.
  - member role: can only see tasks they created or are assigned to;
                 can create tasks; can edit/delete only tasks they created.
"""
import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.db import get_db
from src.dependencies import get_current_user
from src.models import Task, TaskMember, TaskStatus, User, UserRole
from src.schemas import AssignedUser, TaskCreate, TaskOut, TaskUpdate

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/tasks", tags=["tasks"])


def _task_to_out(task: Task) -> TaskOut:
    assigned = [AssignedUser(id=m.user.id, username=m.user.username) for m in task.members]
    return TaskOut(
        id=task.id,
        title=task.title,
        description=task.description,
        status=task.status,
        due_date=task.due_date,
        creator_id=task.creator_id,
        created_at=task.created_at,
        updated_at=task.updated_at,
        assigned_users=assigned,
    )


async def _get_task_or_404(task_id: int, db: AsyncSession) -> Task:
    result = await db.execute(
        select(Task)
        .options(selectinload(Task.members).selectinload(TaskMember.user))
        .where(Task.id == task_id)
    )
    task = result.scalar_one_or_none()
    if not task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")
    return task


def _check_task_access(task: Task, user: User) -> None:
    """Raise 403 if a member-role user does not own or is not assigned to the task."""
    if user.role == UserRole.owner:
        return
    is_assigned = any(m.user_id == user.id for m in task.members)
    if task.creator_id != user.id and not is_assigned:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")


def _check_task_edit(task: Task, user: User) -> None:
    """Raise 403 if a member-role user does not own the task."""
    if user.role == UserRole.owner:
        return
    if task.creator_id != user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the task creator or an owner can modify this task",
        )


# ── List ─────────────────────────────────────────────────────────────────────

@router.get("", response_model=list[TaskOut])
async def list_tasks(
    status_filter: Annotated[TaskStatus | None, Query(alias="status")] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[TaskOut]:
    """
    List tasks.
    - Owners see all tasks.
    - Members see only tasks they created or are assigned to.
    Supports optional ?status= filter.
    """
    query = select(Task).options(
        selectinload(Task.members).selectinload(TaskMember.user)
    )

    if current_user.role != UserRole.owner:
        # tasks created by user OR user is a member
        assigned_subq = select(TaskMember.task_id).where(TaskMember.user_id == current_user.id)
        query = query.where(
            or_(Task.creator_id == current_user.id, Task.id.in_(assigned_subq))
        )

    if status_filter:
        query = query.where(Task.status == status_filter)

    query = query.order_by(Task.created_at.desc())
    result = await db.execute(query)
    tasks = result.scalars().all()
    return [_task_to_out(t) for t in tasks]


# ── Create ────────────────────────────────────────────────────────────────────

@router.post("", response_model=TaskOut, status_code=status.HTTP_201_CREATED)
async def create_task(
    payload: TaskCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> TaskOut:
    task = Task(
        title=payload.title,
        description=payload.description,
        status=payload.status,
        due_date=payload.due_date,
        creator_id=current_user.id,
    )
    db.add(task)
    await db.flush()  # get task.id before adding members

    for user_id in set(payload.assigned_user_ids):
        # validate user exists
        u = await db.get(User, user_id)
        if not u:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"User with id={user_id} not found",
            )
        db.add(TaskMember(task_id=task.id, user_id=user_id))

    await db.commit()

    # Re-fetch with relationships
    task = await _get_task_or_404(task.id, db)
    logger.info("Task id=%d created by user id=%d", task.id, current_user.id)
    return _task_to_out(task)


# ── Read ──────────────────────────────────────────────────────────────────────

@router.get("/{task_id}", response_model=TaskOut)
async def get_task(
    task_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> TaskOut:
    task = await _get_task_or_404(task_id, db)
    _check_task_access(task, current_user)
    return _task_to_out(task)


# ── Update ────────────────────────────────────────────────────────────────────

@router.put("/{task_id}", response_model=TaskOut)
async def update_task(
    task_id: int,
    payload: TaskUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> TaskOut:
    task = await _get_task_or_404(task_id, db)
    _check_task_edit(task, current_user)

    if payload.title is not None:
        task.title = payload.title
    if payload.description is not None:
        task.description = payload.description
    if payload.status is not None:
        task.status = payload.status
    if payload.due_date is not None:
        task.due_date = payload.due_date

    # Sync assigned members if provided
    if payload.assigned_user_ids is not None:
        # Remove existing members not in the new list
        existing_user_ids = {m.user_id for m in task.members}
        new_user_ids = set(payload.assigned_user_ids)

        to_remove = existing_user_ids - new_user_ids
        for m in list(task.members):
            if m.user_id in to_remove:
                await db.delete(m)

        to_add = new_user_ids - existing_user_ids
        for user_id in to_add:
            u = await db.get(User, user_id)
            if not u:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail=f"User with id={user_id} not found",
                )
            db.add(TaskMember(task_id=task.id, user_id=user_id))

    await db.commit()
    task = await _get_task_or_404(task_id, db)
    logger.info("Task id=%d updated by user id=%d", task.id, current_user.id)
    return _task_to_out(task)


# ── Delete ────────────────────────────────────────────────────────────────────

@router.delete("/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_task(
    task_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    task = await _get_task_or_404(task_id, db)
    _check_task_edit(task, current_user)
    await db.delete(task)
    await db.commit()
    logger.info("Task id=%d deleted by user id=%d", task_id, current_user.id)
