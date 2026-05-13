"""organization_invoice_statuses + invoices.status as varchar

Revision ID: c8e4a1b2d3f4
Revises: 9b1f0d5a2f31
Create Date: 2026-05-13

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "c8e4a1b2d3f4"
down_revision: Union[str, Sequence[str], None] = "9b1f0d5a2f31"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    dialect = bind.dialect.name

    op.create_table(
        "organization_invoice_statuses",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("organization_id", sa.Integer(), nullable=False),
        sa.Column("key", sa.String(length=64), nullable=False),
        sa.Column("label", sa.String(length=200), nullable=False),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("auto_overdue_eligible", sa.Boolean(), nullable=False, server_default="0"),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("organization_id", "key", name="uq_org_invoice_status_key"),
    )
    op.create_index(
        op.f("ix_organization_invoice_statuses_organization_id"),
        "organization_invoice_statuses",
        ["organization_id"],
        unique=False,
    )

    conn = op.get_bind()
    org_rows = conn.execute(sa.text("SELECT id FROM organizations")).fetchall()
    for (org_id,) in org_rows:
        for key, label, sort_order, elig in (
            ("pendiente", "Pendiente", 0, True),
            ("pagada", "Pagada", 1, False),
            ("vencida", "Vencida", 2, False),
        ):
            conn.execute(
                sa.text(
                    "INSERT INTO organization_invoice_statuses "
                    "(organization_id, key, label, sort_order, auto_overdue_eligible) "
                    "VALUES (:oid, :k, :l, :s, :e)"
                ),
                {"oid": org_id, "k": key, "l": label, "s": sort_order, "e": elig},
            )

    invoicestatus_enum = postgresql.ENUM(
        "pendiente", "pagada", "vencida", name="invoicestatus", create_type=False
    )

    if dialect == "postgresql":
        op.alter_column(
            "invoices",
            "status",
            existing_type=invoicestatus_enum,
            type_=sa.String(length=64),
            existing_nullable=False,
            postgresql_using="status::text",
        )
        op.execute(sa.text("DROP TYPE IF EXISTS invoicestatus"))
    else:
        op.alter_column(
            "invoices",
            "status",
            type_=sa.String(length=64),
            existing_nullable=False,
        )


def downgrade() -> None:
    bind = op.get_bind()
    dialect = bind.dialect.name

    if dialect == "postgresql":
        invoicestatus_enum = postgresql.ENUM(
            "pendiente", "pagada", "vencida", name="invoicestatus", create_type=True
        )
        invoicestatus_enum.create(bind, checkfirst=True)
        op.alter_column(
            "invoices",
            "status",
            existing_type=sa.String(length=64),
            type_=invoicestatus_enum,
            existing_nullable=False,
            postgresql_using="status::invoicestatus",
        )
    else:
        op.alter_column(
            "invoices",
            "status",
            type_=sa.String(length=32),
            existing_nullable=False,
        )

    op.drop_index(
        op.f("ix_organization_invoice_statuses_organization_id"),
        table_name="organization_invoice_statuses",
    )
    op.drop_table("organization_invoice_statuses")
