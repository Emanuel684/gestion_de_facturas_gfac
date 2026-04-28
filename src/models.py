"""
SQLAlchemy ORM models for the Invoice Management System (SGF).

Multi-tenant: each Organization has isolated users and invoices.
- plataforma_admin: manages organizations (lives in the reserved "plataforma" org).
- administrador / contador / asistente: tenant roles inside an organization.
"""
import enum
from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import (
    Boolean,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    JSON,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.db import Base


class PlanTier(str, enum.Enum):
    """Commercial plan shown on the public landing (pricing differentiation)."""

    basico = "basico"
    profesional = "profesional"
    empresarial = "empresarial"


class UserRole(str, enum.Enum):
    plataforma_admin = "plataforma_admin"
    administrador = "administrador"
    contador = "contador"
    asistente = "asistente"


class InvoiceStatus(str, enum.Enum):
    pendiente = "pendiente"
    pagada = "pagada"
    vencida = "vencida"


class TaxRegime(str, enum.Enum):
    """Régimen tributario (preparación DIAN)."""

    responsable_iva = "responsable_iva"
    no_iva = "no_iva"
    simple = "simple"


class DianDocumentType(str, enum.Enum):
    factura_venta = "factura_venta"
    nota_credito = "nota_credito"
    nota_debito = "nota_debito"


class DianLifecycleStatus(str, enum.Enum):
    """Estado del documento frente al flujo DIAN (trazabilidad)."""

    borrador = "borrador"
    lista_para_envio = "lista_para_envio"
    enviada_proveedor = "enviada_proveedor"
    aceptada_dian = "aceptada_dian"
    rechazada_dian = "rechazada_dian"
    contingencia = "contingencia"


class InvoiceEventType(str, enum.Enum):
    created = "created"
    updated = "updated"
    status_changed = "status_changed"
    document_locked = "document_locked"
    export_generated = "export_generated"
    external_note = "external_note"


class NotificationType(str, enum.Enum):
    invoice_created = "invoice_created"
    invoice_updated = "invoice_updated"
    invoice_status_changed = "invoice_status_changed"
    invoice_assigned = "invoice_assigned"
    invoice_unassigned = "invoice_unassigned"
    invoice_overdue_auto = "invoice_overdue_auto"


class SubscriptionStatus(str, enum.Enum):
    active = "active"
    past_due = "past_due"
    suspended = "suspended"
    canceled = "canceled"


class PaymentStatus(str, enum.Enum):
    pending = "pending"
    paid = "paid"
    failed = "failed"


class CheckoutSessionStatus(str, enum.Enum):
    created = "created"
    completed = "completed"
    expired = "expired"


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Organization(Base):
    __tablename__ = "organizations"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    slug: Mapped[str] = mapped_column(String(80), unique=True, index=True, nullable=False)
    plan_tier: Mapped[PlanTier] = mapped_column(
        Enum(PlanTier, name="plantier"), default=PlanTier.basico, nullable=False
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, nullable=False
    )

    users: Mapped[list["User"]] = relationship("User", back_populates="organization")
    invoices: Mapped[list["Invoice"]] = relationship("Invoice", back_populates="organization")
    subscriptions: Mapped[list["Subscription"]] = relationship(
        "Subscription", back_populates="organization"
    )
    payments: Mapped[list["Payment"]] = relationship("Payment", back_populates="organization")
    checkout_sessions: Mapped[list["CheckoutSession"]] = relationship(
        "CheckoutSession", back_populates="organization"
    )
    fiscal_profile: Mapped["OrganizationFiscalProfile | None"] = relationship(
        "OrganizationFiscalProfile",
        back_populates="organization",
        uselist=False,
    )

    def __repr__(self) -> str:
        return f"<Organization id={self.id} slug={self.slug!r}>"


class OrganizationFiscalProfile(Base):
    """Datos fiscales del emisor (tenant) para preparación de documentos DIAN."""

    __tablename__ = "organization_fiscal_profiles"
    __table_args__ = (UniqueConstraint("organization_id", name="uq_fiscal_profile_org"),)

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    organization_id: Mapped[int] = mapped_column(
        ForeignKey("organizations.id"), nullable=False, index=True
    )
    nit: Mapped[str] = mapped_column(String(20), nullable=False, default="")
    dv: Mapped[str] = mapped_column(String(2), nullable=False, default="")
    business_name: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    trade_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    department_code: Mapped[str | None] = mapped_column(String(10), nullable=True)
    city_code: Mapped[str | None] = mapped_column(String(10), nullable=True)
    tax_regime: Mapped[TaxRegime] = mapped_column(
        Enum(TaxRegime, name="taxregime"),
        nullable=False,
        default=TaxRegime.responsable_iva,
    )
    invoice_prefix_default: Mapped[str | None] = mapped_column(String(20), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False
    )

    organization: Mapped["Organization"] = relationship("Organization", back_populates="fiscal_profile")


class User(Base):
    __tablename__ = "users"
    __table_args__ = (
        UniqueConstraint("organization_id", "username", name="uq_user_org_username"),
        UniqueConstraint("organization_id", "email", name="uq_user_org_email"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    organization_id: Mapped[int] = mapped_column(
        ForeignKey("organizations.id"), nullable=False, index=True
    )
    username: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    email: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[UserRole] = mapped_column(
        Enum(UserRole, name="userrole"), default=UserRole.asistente, nullable=False
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, nullable=False
    )

    organization: Mapped["Organization"] = relationship("Organization", back_populates="users")
    created_invoices: Mapped[list["Invoice"]] = relationship(
        "Invoice", back_populates="creator", foreign_keys="Invoice.creator_id"
    )
    invoice_assignments: Mapped[list["InvoiceAssignee"]] = relationship(
        "InvoiceAssignee", back_populates="user"
    )

    def __repr__(self) -> str:
        return f"<User id={self.id} username={self.username!r} role={self.role}>"


class Invoice(Base):
    __tablename__ = "invoices"
    __table_args__ = (
        UniqueConstraint("organization_id", "invoice_number", name="uq_org_invoice_number"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    organization_id: Mapped[int] = mapped_column(
        ForeignKey("organizations.id"), nullable=False, index=True
    )
    invoice_number: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    supplier: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    status: Mapped[InvoiceStatus] = mapped_column(
        Enum(InvoiceStatus, name="invoicestatus"), default=InvoiceStatus.pendiente, nullable=False
    )
    due_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    creator_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False
    )

    # ── Preparación DIAN / FEV (trazabilidad) ─────────────────────────────────
    document_type: Mapped[DianDocumentType] = mapped_column(
        Enum(DianDocumentType, name="diandocumenttype"),
        nullable=False,
        default=DianDocumentType.factura_venta,
    )
    issue_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    currency: Mapped[str] = mapped_column(String(8), nullable=False, default="COP")
    buyer_id_type: Mapped[str | None] = mapped_column(String(20), nullable=True)
    buyer_id_number: Mapped[str | None] = mapped_column(String(32), nullable=True)
    buyer_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    seller_snapshot_nit: Mapped[str | None] = mapped_column(String(20), nullable=True)
    seller_snapshot_dv: Mapped[str | None] = mapped_column(String(2), nullable=True)
    seller_snapshot_business_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    subtotal: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    taxable_base: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    iva_rate: Mapped[Decimal | None] = mapped_column(Numeric(5, 4), nullable=True)
    iva_amount: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    withholding_amount: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    total_document: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    dian_lifecycle_status: Mapped[DianLifecycleStatus] = mapped_column(
        Enum(DianLifecycleStatus, name="dianlifecyclestatus"),
        nullable=False,
        default=DianLifecycleStatus.borrador,
    )
    document_locked: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    organization: Mapped["Organization"] = relationship("Organization", back_populates="invoices")
    creator: Mapped["User"] = relationship(
        "User", back_populates="created_invoices", foreign_keys=[creator_id]
    )
    assignees: Mapped[list["InvoiceAssignee"]] = relationship(
        "InvoiceAssignee", back_populates="invoice", cascade="all, delete-orphan"
    )
    trace_events: Mapped[list["InvoiceEvent"]] = relationship(
        "InvoiceEvent", back_populates="invoice", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Invoice id={self.id} number={self.invoice_number!r} status={self.status}>"


class InvoiceEvent(Base):
    """Bitácora append-only de trazabilidad por factura."""

    __tablename__ = "invoice_events"
    __table_args__ = (Index("ix_invoice_events_org_inv_created", "organization_id", "invoice_id", "created_at"),)

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    invoice_id: Mapped[int] = mapped_column(ForeignKey("invoices.id"), nullable=False, index=True)
    organization_id: Mapped[int] = mapped_column(
        ForeignKey("organizations.id"), nullable=False, index=True
    )
    event_type: Mapped[InvoiceEventType] = mapped_column(
        Enum(InvoiceEventType, name="invoiceeventtype"), nullable=False
    )
    actor_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True, index=True)
    payload: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)

    invoice: Mapped["Invoice"] = relationship("Invoice", back_populates="trace_events")
    organization: Mapped["Organization"] = relationship("Organization")
    actor: Mapped["User | None"] = relationship("User", foreign_keys=[actor_user_id])


class InvoiceAssignee(Base):
    """Associates users to invoices (responsibility tracking)."""

    __tablename__ = "invoice_assignees"
    __table_args__ = (UniqueConstraint("invoice_id", "user_id", name="uq_invoice_assignee"),)

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    invoice_id: Mapped[int] = mapped_column(ForeignKey("invoices.id"), nullable=False, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    assigned_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, nullable=False
    )

    invoice: Mapped["Invoice"] = relationship("Invoice", back_populates="assignees")
    user: Mapped["User"] = relationship("User", back_populates="invoice_assignments")

    def __repr__(self) -> str:
        return f"<InvoiceAssignee invoice_id={self.invoice_id} user_id={self.user_id}>"


class Notification(Base):
    __tablename__ = "notifications"
    __table_args__ = (
        Index("ix_notifications_user_is_read_created", "user_id", "is_read", "created_at"),
        Index("ix_notifications_org_created", "organization_id", "created_at"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    organization_id: Mapped[int] = mapped_column(
        ForeignKey("organizations.id"), nullable=False, index=True
    )
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    type: Mapped[NotificationType] = mapped_column(
        Enum(NotificationType, name="notificationtype"), nullable=False
    )
    title: Mapped[str] = mapped_column(String(160), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    invoice_id: Mapped[int | None] = mapped_column(ForeignKey("invoices.id"), nullable=True, index=True)
    payload: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    is_read: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    read_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, nullable=False
    )

    organization: Mapped["Organization"] = relationship("Organization")
    user: Mapped["User"] = relationship("User")
    invoice: Mapped["Invoice | None"] = relationship("Invoice")


class Subscription(Base):
    __tablename__ = "subscriptions"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    organization_id: Mapped[int] = mapped_column(
        ForeignKey("organizations.id"), nullable=False, index=True
    )
    plan_tier: Mapped[PlanTier] = mapped_column(
        Enum(PlanTier, name="plantier"), nullable=False, default=PlanTier.basico
    )
    status: Mapped[SubscriptionStatus] = mapped_column(
        Enum(SubscriptionStatus, name="subscriptionstatus"),
        nullable=False,
        default=SubscriptionStatus.past_due,
    )
    current_period_start: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    current_period_end: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    next_due_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    grace_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_paid_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow
    )

    organization: Mapped["Organization"] = relationship("Organization", back_populates="subscriptions")
    payments: Mapped[list["Payment"]] = relationship("Payment", back_populates="subscription")


class Payment(Base):
    __tablename__ = "payments"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    organization_id: Mapped[int] = mapped_column(
        ForeignKey("organizations.id"), nullable=False, index=True
    )
    subscription_id: Mapped[int] = mapped_column(
        ForeignKey("subscriptions.id"), nullable=False, index=True
    )
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(8), nullable=False, default="COP")
    status: Mapped[PaymentStatus] = mapped_column(
        Enum(PaymentStatus, name="paymentstatus"), nullable=False, default=PaymentStatus.pending
    )
    provider: Mapped[str] = mapped_column(String(50), nullable=False, default="mock")
    provider_reference: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    paid_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    organization: Mapped["Organization"] = relationship("Organization", back_populates="payments")
    subscription: Mapped["Subscription"] = relationship("Subscription", back_populates="payments")


class CheckoutSession(Base):
    __tablename__ = "checkout_sessions"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    organization_id: Mapped[int] = mapped_column(
        ForeignKey("organizations.id"), nullable=False, index=True
    )
    plan_tier: Mapped[PlanTier] = mapped_column(Enum(PlanTier, name="plantier"), nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(8), nullable=False, default="COP")
    session_token: Mapped[str] = mapped_column(String(64), nullable=False, unique=True, index=True)
    status: Mapped[CheckoutSessionStatus] = mapped_column(
        Enum(CheckoutSessionStatus, name="checkoutsessionstatus"),
        nullable=False,
        default=CheckoutSessionStatus.created,
    )
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    organization: Mapped["Organization"] = relationship("Organization", back_populates="checkout_sessions")
