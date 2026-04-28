"""
Pydantic schemas for request/response validation — Invoice Management System.
"""
import re
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from src.models import (
    CheckoutSessionStatus,
    DianDocumentType,
    DianLifecycleStatus,
    InvoiceEventType,
    InvoiceStatus,
    NotificationType,
    PaymentStatus,
    PlanTier,
    SubscriptionStatus,
    TaxRegime,
    UserRole,
)


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


class OrganizationUpdate(BaseModel):
    name: str | None = None
    slug: str | None = None
    plan_tier: PlanTier | None = None

    @field_validator("name")
    @classmethod
    def name_strip(cls, v: str | None) -> str | None:
        if v is None:
            return v
        v = v.strip()
        if not v:
            raise ValueError("name must not be empty")
        return v

    @field_validator("slug")
    @classmethod
    def slug_normalize(cls, v: str | None) -> str | None:
        if v is None:
            return v
        v = v.strip().lower()
        if not v or len(v) > 80:
            raise ValueError("invalid slug")
        if not _SLUG_RE.match(v):
            raise ValueError("slug: solo minúsculas, números y guiones")
        if v == "plataforma":
            raise ValueError("slug reservado")
        return v


class PublicSignupIn(BaseModel):
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


class PublicSignupOut(BaseModel):
    organization_id: int
    organization_slug: str
    checkout_session_token: str
    checkout_url: str


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


class UserUpdate(BaseModel):
    """Patch-like update for tenant users (admin-only)."""

    username: str | None = None
    email: EmailStr | None = None
    password: str | None = None
    role: UserRole | None = None
    is_active: bool | None = None

    @field_validator("username")
    @classmethod
    def username_not_empty(cls, v: str | None) -> str | None:
        if v is None:
            return v
        v = v.strip()
        if not v:
            raise ValueError("username must not be empty")
        if len(v) < 3:
            raise ValueError("username must be at least 3 characters")
        return v

    @field_validator("password")
    @classmethod
    def password_min_length(cls, v: str | None) -> str | None:
        if v is None:
            return v
        if len(v) < 6:
            raise ValueError("password must be at least 6 characters")
        return v

    @field_validator("role")
    @classmethod
    def no_platform_role(cls, v: UserRole | None) -> UserRole | None:
        if v is None:
            return v
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
    # Preparación DIAN (opcional; valores por defecto en servidor si no se envían)
    document_type: DianDocumentType | None = None
    issue_date: datetime | None = None
    currency: str | None = None
    buyer_id_type: str | None = None
    buyer_id_number: str | None = None
    buyer_name: str | None = None
    subtotal: Decimal | None = None
    taxable_base: Decimal | None = None
    iva_rate: Decimal | None = None
    iva_amount: Decimal | None = None
    withholding_amount: Decimal | None = None
    total_document: Decimal | None = None
    dian_lifecycle_status: DianLifecycleStatus | None = None

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
    document_type: DianDocumentType | None = None
    issue_date: datetime | None = None
    currency: str | None = None
    buyer_id_type: str | None = None
    buyer_id_number: str | None = None
    buyer_name: str | None = None
    subtotal: Decimal | None = None
    taxable_base: Decimal | None = None
    iva_rate: Decimal | None = None
    iva_amount: Decimal | None = None
    withholding_amount: Decimal | None = None
    total_document: Decimal | None = None
    dian_lifecycle_status: DianLifecycleStatus | None = None

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
    document_type: DianDocumentType
    issue_date: datetime
    currency: str
    buyer_id_type: str | None
    buyer_id_number: str | None
    buyer_name: str | None
    seller_snapshot_nit: str | None
    seller_snapshot_dv: str | None
    seller_snapshot_business_name: str | None
    subtotal: Decimal | None
    taxable_base: Decimal | None
    iva_rate: Decimal | None
    iva_amount: Decimal | None
    withholding_amount: Decimal | None
    total_document: Decimal | None
    dian_lifecycle_status: DianLifecycleStatus
    document_locked: bool


class InvoicePage(BaseModel):
    """Paginated response envelope for invoice list queries."""

    items: list[InvoiceOut]
    has_next: bool
    page: int
    page_size: int


class PlatformInvoiceSummaryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    organization_id: int
    invoice_number: str
    supplier: str
    amount: Decimal
    status: InvoiceStatus
    due_date: datetime | None
    created_at: datetime


class InvoiceEventOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    event_type: InvoiceEventType
    actor_user_id: int | None
    payload: dict | None
    created_at: datetime


class InvoiceTraceResponse(BaseModel):
    invoice: InvoiceOut
    events: list[InvoiceEventOut]


class NotificationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    type: NotificationType
    title: str
    message: str
    invoice_id: int | None
    payload: dict | None
    is_read: bool
    read_at: datetime | None
    created_at: datetime


class NotificationPage(BaseModel):
    items: list[NotificationOut]
    has_next: bool
    page: int
    page_size: int


class NotificationUnreadCount(BaseModel):
    unread: int


class FiscalProfileOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int | None = None
    organization_id: int
    nit: str
    dv: str
    business_name: str
    trade_name: str | None
    department_code: str | None
    city_code: str | None
    tax_regime: TaxRegime
    invoice_prefix_default: str | None
    updated_at: datetime | None = None


class FiscalProfileUpdate(BaseModel):
    nit: str
    dv: str
    business_name: str
    trade_name: str | None = None
    department_code: str | None = None
    city_code: str | None = None
    tax_regime: TaxRegime = TaxRegime.responsable_iva
    invoice_prefix_default: str | None = None

    @field_validator("nit", "dv", "business_name")
    @classmethod
    def strip_required(cls, v: str | None) -> str | None:
        if v is None:
            return v
        return v.strip()


# ── Billing ───────────────────────────────────────────────────────────────────

class CheckoutCreateIn(BaseModel):
    plan_tier: PlanTier


class CheckoutSessionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    session_token: str
    plan_tier: PlanTier
    amount: Decimal
    currency: str
    status: CheckoutSessionStatus
    expires_at: datetime
    completed_at: datetime | None = None


class CheckoutCreateOut(BaseModel):
    checkout_url: str
    session: CheckoutSessionOut


class CheckoutActionIn(BaseModel):
    outcome: PaymentStatus

    @field_validator("outcome")
    @classmethod
    def allowed_outcomes(cls, v: PaymentStatus) -> PaymentStatus:
        if v not in (PaymentStatus.paid, PaymentStatus.failed):
            raise ValueError("outcome must be paid or failed")
        return v


class PaymentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    amount: Decimal
    currency: str
    status: PaymentStatus
    provider: str
    provider_reference: str
    paid_at: datetime | None
    created_at: datetime


class SubscriptionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    organization_id: int
    plan_tier: PlanTier
    status: SubscriptionStatus
    current_period_start: datetime | None
    current_period_end: datetime | None
    next_due_date: datetime | None
    grace_expires_at: datetime | None
    last_paid_at: datetime | None
    created_at: datetime
    updated_at: datetime


# ── Reporting / dashboards ────────────────────────────────────────────────────


class StatusCounts(BaseModel):
    pendiente: int = 0
    pagada: int = 0
    vencida: int = 0


class StatusAmounts(BaseModel):
    pendiente: Decimal = Decimal("0")
    pagada: Decimal = Decimal("0")
    vencida: Decimal = Decimal("0")


class MonthlySeriesPoint(BaseModel):
    month: str
    invoice_count: int
    total_amount: Decimal


class AmountHistogramBin(BaseModel):
    """Cantidad de facturas por rango de monto (COP)."""

    label: str
    invoice_count: int


class DashboardStatsOut(BaseModel):
    organization_id: int
    organization_name: str | None = None
    total_invoices: int
    total_amount: Decimal
    count_by_status: StatusCounts
    amount_by_status: StatusAmounts
    monthly: list[MonthlySeriesPoint]
    histogram_by_amount: list[AmountHistogramBin] = Field(
        default_factory=list,
        description="Distribución de facturas por tramo de monto (COP).",
    )
    pending_due_within_7_days: int
    date_from: datetime | None = None
    date_to: datetime | None = None


class OrgBillingRankOut(BaseModel):
    organization_id: int
    name: str
    slug: str
    invoice_count: int
    total_amount: Decimal


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
