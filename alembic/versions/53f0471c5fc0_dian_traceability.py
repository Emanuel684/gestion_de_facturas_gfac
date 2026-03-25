"""dian_traceability

Revision ID: 53f0471c5fc0
Revises: f702b029fcc1
Create Date: 2026-03-25 11:25:33.342865

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.types import UserDefinedType


class PGEnumName(UserDefinedType):
    """Reference an existing PostgreSQL ENUM by name — never emits CREATE TYPE (asyncpg-safe)."""

    cache_ok = True

    def __init__(self, type_name: str) -> None:
        self.type_name = type_name

    def get_col_spec(self, **kw: object) -> str:
        return self.type_name


def _ensure_pg_enum(name: str, *values: str) -> None:
    """Idempotent CREATE TYPE for PostgreSQL (safe on docker restarts / retries)."""
    labels = ", ".join(f"'{v}'" for v in values)
    op.execute(
        sa.text(
            f"""
            DO $$ BEGIN
                CREATE TYPE {name} AS ENUM ({labels});
            EXCEPTION
                WHEN duplicate_object THEN NULL;
            END $$;
            """
        )
    )


revision: str = "53f0471c5fc0"
down_revision: Union[str, Sequence[str], None] = "f702b029fcc1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Ensure enum types exist (idempotent). Columns use PGEnumName so Alembic never emits CREATE TYPE.
    _ensure_pg_enum("taxregime", "responsable_iva", "no_iva", "simple")
    _ensure_pg_enum("diandocumenttype", "factura_venta", "nota_credito", "nota_debito")
    _ensure_pg_enum(
        "dianlifecyclestatus",
        "borrador",
        "lista_para_envio",
        "enviada_proveedor",
        "aceptada_dian",
        "rechazada_dian",
        "contingencia",
    )
    _ensure_pg_enum(
        "invoiceeventtype",
        "created",
        "updated",
        "status_changed",
        "document_locked",
        "export_generated",
        "external_note",
    )

    op.create_table(
        "organization_fiscal_profiles",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("organization_id", sa.Integer(), nullable=False),
        sa.Column("nit", sa.String(length=20), nullable=False),
        sa.Column("dv", sa.String(length=2), nullable=False),
        sa.Column("business_name", sa.String(length=255), nullable=False),
        sa.Column("trade_name", sa.String(length=255), nullable=True),
        sa.Column("department_code", sa.String(length=10), nullable=True),
        sa.Column("city_code", sa.String(length=10), nullable=True),
        sa.Column("tax_regime", PGEnumName("taxregime"), nullable=False),
        sa.Column("invoice_prefix_default", sa.String(length=20), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("organization_id", name="uq_fiscal_profile_org"),
    )
    op.create_index(
        op.f("ix_organization_fiscal_profiles_id"), "organization_fiscal_profiles", ["id"], unique=False
    )
    op.create_index(
        op.f("ix_organization_fiscal_profiles_organization_id"),
        "organization_fiscal_profiles",
        ["organization_id"],
        unique=False,
    )

    op.add_column(
        "invoices",
        sa.Column(
            "document_type",
            PGEnumName("diandocumenttype"),
            nullable=False,
            server_default=sa.text("'factura_venta'::diandocumenttype"),
        ),
    )
    op.add_column("invoices", sa.Column("issue_date", sa.DateTime(timezone=True), nullable=True))
    op.add_column(
        "invoices",
        sa.Column("currency", sa.String(length=8), nullable=False, server_default="COP"),
    )
    op.add_column("invoices", sa.Column("buyer_id_type", sa.String(length=20), nullable=True))
    op.add_column("invoices", sa.Column("buyer_id_number", sa.String(length=32), nullable=True))
    op.add_column("invoices", sa.Column("buyer_name", sa.String(length=255), nullable=True))
    op.add_column("invoices", sa.Column("seller_snapshot_nit", sa.String(length=20), nullable=True))
    op.add_column("invoices", sa.Column("seller_snapshot_dv", sa.String(length=2), nullable=True))
    op.add_column("invoices", sa.Column("seller_snapshot_business_name", sa.String(length=255), nullable=True))
    op.add_column("invoices", sa.Column("subtotal", sa.Numeric(precision=12, scale=2), nullable=True))
    op.add_column("invoices", sa.Column("taxable_base", sa.Numeric(precision=12, scale=2), nullable=True))
    op.add_column("invoices", sa.Column("iva_rate", sa.Numeric(precision=5, scale=4), nullable=True))
    op.add_column("invoices", sa.Column("iva_amount", sa.Numeric(precision=12, scale=2), nullable=True))
    op.add_column("invoices", sa.Column("withholding_amount", sa.Numeric(precision=12, scale=2), nullable=True))
    op.add_column("invoices", sa.Column("total_document", sa.Numeric(precision=12, scale=2), nullable=True))
    op.add_column(
        "invoices",
        sa.Column(
            "dian_lifecycle_status",
            PGEnumName("dianlifecyclestatus"),
            nullable=False,
            server_default=sa.text("'borrador'::dianlifecyclestatus"),
        ),
    )
    op.add_column(
        "invoices",
        sa.Column("document_locked", sa.Boolean(), nullable=False, server_default="0"),
    )

    op.execute("UPDATE invoices SET issue_date = created_at WHERE issue_date IS NULL")
    op.alter_column("invoices", "issue_date", nullable=False)

    op.create_table(
        "invoice_events",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("invoice_id", sa.Integer(), nullable=False),
        sa.Column("organization_id", sa.Integer(), nullable=False),
        sa.Column("event_type", PGEnumName("invoiceeventtype"), nullable=False),
        sa.Column("actor_user_id", sa.Integer(), nullable=True),
        sa.Column("payload", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["actor_user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["invoice_id"], ["invoices.id"]),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_invoice_events_actor_user_id"), "invoice_events", ["actor_user_id"], unique=False)
    op.create_index(op.f("ix_invoice_events_id"), "invoice_events", ["id"], unique=False)
    op.create_index(op.f("ix_invoice_events_invoice_id"), "invoice_events", ["invoice_id"], unique=False)
    op.create_index(op.f("ix_invoice_events_organization_id"), "invoice_events", ["organization_id"], unique=False)
    op.create_index(
        "ix_invoice_events_org_inv_created",
        "invoice_events",
        ["organization_id", "invoice_id", "created_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_invoice_events_org_inv_created", table_name="invoice_events")
    op.drop_index(op.f("ix_invoice_events_organization_id"), table_name="invoice_events")
    op.drop_index(op.f("ix_invoice_events_invoice_id"), table_name="invoice_events")
    op.drop_index(op.f("ix_invoice_events_id"), table_name="invoice_events")
    op.drop_index(op.f("ix_invoice_events_actor_user_id"), table_name="invoice_events")
    op.drop_table("invoice_events")

    op.drop_column("invoices", "document_locked")
    op.drop_column("invoices", "dian_lifecycle_status")
    op.drop_column("invoices", "total_document")
    op.drop_column("invoices", "withholding_amount")
    op.drop_column("invoices", "iva_amount")
    op.drop_column("invoices", "iva_rate")
    op.drop_column("invoices", "taxable_base")
    op.drop_column("invoices", "subtotal")
    op.drop_column("invoices", "seller_snapshot_business_name")
    op.drop_column("invoices", "seller_snapshot_dv")
    op.drop_column("invoices", "seller_snapshot_nit")
    op.drop_column("invoices", "buyer_name")
    op.drop_column("invoices", "buyer_id_number")
    op.drop_column("invoices", "buyer_id_type")
    op.drop_column("invoices", "currency")
    op.drop_column("invoices", "issue_date")
    op.drop_column("invoices", "document_type")

    op.drop_index(
        op.f("ix_organization_fiscal_profiles_organization_id"), table_name="organization_fiscal_profiles"
    )
    op.drop_index(op.f("ix_organization_fiscal_profiles_id"), table_name="organization_fiscal_profiles")
    op.drop_table("organization_fiscal_profiles")

    op.execute("DROP TYPE IF EXISTS invoiceeventtype")
    op.execute("DROP TYPE IF EXISTS dianlifecyclestatus")
    op.execute("DROP TYPE IF EXISTS diandocumenttype")
    op.execute("DROP TYPE IF EXISTS taxregime")
