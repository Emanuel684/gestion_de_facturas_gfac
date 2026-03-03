"""
Pydantic schemas for request/response validation — Invoice Management System.
"""
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, EmailStr, field_validator

from src.models import InvoiceStatus, UserRole


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


# ── Invoice ───────────────────────────────────────────────────────────────────

class AssignedUser(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    username: str


class InvoiceCreate(BaseModel):
    invoice_number: str
    supplier: str
    description: str | None = None
    amount: Decimal
    status: InvoiceStatus = InvoiceStatus.pendiente
    due_date: datetime | None = None
    assigned_user_ids: list[int] = []

    @field_validator("invoice_number")
    @classmethod
    def invoice_number_not_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("invoice_number must not be empty")
        return v.strip()

    @field_validator("supplier")
    @classmethod
    def supplier_not_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("supplier must not be empty")
        return v.strip()

    @field_validator("amount")
    @classmethod
    def amount_positive(cls, v: Decimal) -> Decimal:
        if v <= 0:
            raise ValueError("amount must be greater than zero")
        return v


class InvoiceUpdate(BaseModel):
    invoice_number: str | None = None
    supplier: str | None = None
    description: str | None = None
    amount: Decimal | None = None
    status: InvoiceStatus | None = None
    due_date: datetime | None = None
    assigned_user_ids: list[int] | None = None

    @field_validator("invoice_number")
    @classmethod
    def invoice_number_not_empty(cls, v: str | None) -> str | None:
        if v is not None and not v.strip():
            raise ValueError("invoice_number must not be empty")
        return v.strip() if v else v

    @field_validator("supplier")
    @classmethod
    def supplier_not_empty(cls, v: str | None) -> str | None:
        if v is not None and not v.strip():
            raise ValueError("supplier must not be empty")
        return v.strip() if v else v

    @field_validator("amount")
    @classmethod
    def amount_positive(cls, v: Decimal | None) -> Decimal | None:
        if v is not None and v <= 0:
            raise ValueError("amount must be greater than zero")
        return v


class InvoiceOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    invoice_number: str
    supplier: str
    description: str | None
    amount: Decimal
    status: InvoiceStatus
    due_date: datetime | None
    creator_id: int
    created_at: datetime
    updated_at: datetime
    assigned_users: list[AssignedUser] = []
