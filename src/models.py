"""
SQLAlchemy ORM models.

Design decisions:
- User.role is a global role: "owner" can do anything, "member" can only manage
  tasks they created or are assigned to.
- TaskMember is a join table that assigns users to tasks (task assignment feature).
- Task.status uses a plain string with a CHECK-like enum enforced at the app layer.
"""
import enum
from datetime import datetime, timezone

from sqlalchemy import (
    Boolean,
    DateTime,
    Enum,
    ForeignKey,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.db import Base


class UserRole(str, enum.Enum):
    owner = "owner"
    member = "member"


class TaskStatus(str, enum.Enum):
    todo = "todo"
    in_progress = "in_progress"
    done = "done"


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    username: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[UserRole] = mapped_column(
        Enum(UserRole, name="userrole"), default=UserRole.member, nullable=False
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, nullable=False
    )

    # Relationships
    owned_tasks: Mapped[list["Task"]] = relationship(
        "Task", back_populates="creator", foreign_keys="Task.creator_id"
    )
    task_memberships: Mapped[list["TaskMember"]] = relationship(
        "TaskMember", back_populates="user"
    )

    def __repr__(self) -> str:
        return f"<User id={self.id} username={self.username!r} role={self.role}>"


class Task(Base):
    __tablename__ = "tasks"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[TaskStatus] = mapped_column(
        Enum(TaskStatus, name="taskstatus"), default=TaskStatus.todo, nullable=False
    )
    due_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    creator_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False
    )

    # Relationships
    creator: Mapped["User"] = relationship("User", back_populates="owned_tasks", foreign_keys=[creator_id])
    members: Mapped[list["TaskMember"]] = relationship(
        "TaskMember", back_populates="task", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Task id={self.id} title={self.title!r} status={self.status}>"


class TaskMember(Base):
    """Associates users to tasks (task assignment)."""

    __tablename__ = "task_members"
    __table_args__ = (UniqueConstraint("task_id", "user_id", name="uq_task_member"),)

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    task_id: Mapped[int] = mapped_column(ForeignKey("tasks.id"), nullable=False, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    assigned_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, nullable=False
    )

    # Relationships
    task: Mapped["Task"] = relationship("Task", back_populates="members")
    user: Mapped["User"] = relationship("User", back_populates="task_memberships")

    def __repr__(self) -> str:
        return f"<TaskMember task_id={self.task_id} user_id={self.user_id}>"
