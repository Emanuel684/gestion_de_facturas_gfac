"""
Pydantic schemas for request/response validation.
"""
from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, field_validator

from src.models import TaskStatus, UserRole


# ── Auth ──────────────────────────────────────────────────────────────────────

class LoginRequest(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


# ── User ──────────────────────────────────────────────────────────────────────

class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    username: str
    email: str
    role: UserRole
    is_active: bool
    created_at: datetime


# ── Task ──────────────────────────────────────────────────────────────────────

class TaskMemberOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    user_id: int
    username: str  # resolved in router

    # class Config:
    #     from_attributes = True


class TaskCreate(BaseModel):
    title: str
    description: str | None = None
    status: TaskStatus = TaskStatus.todo
    due_date: datetime | None = None
    assigned_user_ids: list[int] = []

    @field_validator("title")
    @classmethod
    def title_not_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("title must not be empty")
        return v.strip()


class TaskUpdate(BaseModel):
    title: str | None = None
    description: str | None = None
    status: TaskStatus | None = None
    due_date: datetime | None = None
    assigned_user_ids: list[int] | None = None

    @field_validator("title")
    @classmethod
    def title_not_empty(cls, v: str | None) -> str | None:
        if v is not None and not v.strip():
            raise ValueError("title must not be empty")
        return v.strip() if v else v


class AssignedUser(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    username: str


class TaskOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    description: str | None
    status: TaskStatus
    due_date: datetime | None
    creator_id: int
    created_at: datetime
    updated_at: datetime
    assigned_users: list[AssignedUser] = []
