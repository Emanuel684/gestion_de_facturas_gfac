"""
Pydantic schemas for request/response validation — Invoice Management System.
"""
import re
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, EmailStr, field_validator

from src.models import InvoiceStatus, PlanTier, UserRole


# ── Auth ──────────────────────────────────────────────────────────────────────

class LoginJSON(BaseModel):
    organization_slug: str
    username: str
    password: str

    @field_validator("organization_slug", "username")
    @classmethod
    def strip_required(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("must not be empty")
        return v


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


# ── Organization ──────────────────────────────────────────────────────────────

class OrganizationBrief(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    slug: str
    plan_tier: PlanTier


class OrganizationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    slug: str
    plan_tier: PlanTier
    is_active: bool
    created_at: datetime


_SLUG_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")


class OrganizationCreate(BaseModel):
    name: str
    slug: str
    plan_tier: PlanTier = PlanTier.basico
    admin_username: str
    admin_email: EmailStr
    admin_password: str

    @field_validator("name")
    @classmethod
    def name_strip(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("name must not be empty")
        return v

    @field_validator("slug")
    @classmethod
    def slug_normalize(cls, v: str) -> str:
        v = v.strip().lower()
        if not v or len(v) > 80:
            raise ValueError("invalid slug")
        if not _SLUG_RE.match(v):
            raise ValueError("slug: solo minúsculas, números y guiones")
        if v == "plataforma":
            raise ValueError("slug reservado")
        return v

    @field_validator("admin_username")
    @classmethod
    def admin_username_ok(cls, v: str) -> str:
        v = v.strip()
        if len(v) < 3:
            raise ValueError("admin_username must be at least 3 characters")
        return v

    @field_validator("admin_password")
    @classmethod
    def admin_password_ok(cls, v: str) -> str:
        if len(v) < 6:
            raise ValueError("admin_password must be at least 6 characters")
        return v


# ── User ──────────────────────────────────────────────────────────────────────

class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    username: str
    email: str
    role: UserRole
    is_active: bool
    created_at: datetime
    organization_id: int
    organization: OrganizationBrief


class UserCreate(BaseModel):
    username: str
    email: EmailStr
    password: str
    role: UserRole = UserRole.asistente

    @field_validator("username")
    @classmethod
    def username_not_empty(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("username must not be empty")
        if len(v) < 3:
            raise ValueError("username must be at least 3 characters")
        return v

    @field_validator("password")
    @classmethod
    def password_min_length(cls, v: str) -> str:
        if len(v) < 6:
            raise ValueError("password must be at least 6 characters")
        return v

    @field_validator("role")
    @classmethod
    def no_platform_role(cls, v: UserRole) -> UserRole:
        if v == UserRole.plataforma_admin:
            raise ValueError("cannot assign plataforma_admin via tenant API")
        return v


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


class InvoicePage(BaseModel):
    """Paginated response envelope for invoice list queries."""

    items: list[InvoiceOut]
    has_next: bool
    page: int
    page_size: int


def user_to_out(user) -> UserOut:
    """Build UserOut; `user` must have `.organization` loaded."""
    return UserOut(
        id=user.id,
        username=user.username,
        email=user.email,
        role=user.role,
        is_active=user.is_active,
        created_at=user.created_at,
        organization_id=user.organization_id,
        organization=OrganizationBrief.model_validate(user.organization),
    )
