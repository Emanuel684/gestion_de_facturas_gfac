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

    def __repr__(self) -> str:
        return f"<Organization id={self.id} slug={self.slug!r}>"


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

    organization: Mapped["Organization"] = relationship("Organization", back_populates="invoices")
    creator: Mapped["User"] = relationship(
        "User", back_populates="created_invoices", foreign_keys=[creator_id]
    )
    assignees: Mapped[list["InvoiceAssignee"]] = relationship(
        "InvoiceAssignee", back_populates="invoice", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Invoice id={self.id} number={self.invoice_number!r} status={self.status}>"


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
