"""
SQLAlchemy ORM models for the Invoice Management System (SGF).

Design decisions:
- User.role defines access level:
    - "administrador" (Gerente): full control over all invoices and users.
    - "contador": can create, view, and update invoices.
    - "asistente": can view and register invoices but cannot delete.
- Invoice tracks: supplier, amount, due date, status (pendiente/pagada/vencida).
- InvoiceAssignee is a join table so multiple users can be associated with an invoice.
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


class UserRole(str, enum.Enum):
    administrador = "administrador"
    contador = "contador"
    asistente = "asistente"


class InvoiceStatus(str, enum.Enum):
    pendiente = "pendiente"
    pagada = "pagada"
    vencida = "vencida"


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    username: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[UserRole] = mapped_column(
        Enum(UserRole, name="userrole"), default=UserRole.asistente, nullable=False
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, nullable=False
    )

    # Relationships
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

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    invoice_number: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)
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

    # Relationships
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

    # Relationships
    invoice: Mapped["Invoice"] = relationship("Invoice", back_populates="assignees")
    user: Mapped["User"] = relationship("User", back_populates="invoice_assignments")

    def __repr__(self) -> str:
        return f"<InvoiceAssignee invoice_id={self.invoice_id} user_id={self.user_id}>"
