"""notifications

Revision ID: 9b1f0d5a2f31
Revises: 53f0471c5fc0
Create Date: 2026-04-28 10:18:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.types import UserDefinedType


class PGEnumName(UserDefinedType):
    cache_ok = True

    def __init__(self, type_name: str) -> None:
        self.type_name = type_name

    def get_col_spec(self, **kw: object) -> str:
        return self.type_name


def _ensure_pg_enum(name: str, *values: str) -> None:
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


revision: str = "9b1f0d5a2f31"
down_revision: Union[str, Sequence[str], None] = "53f0471c5fc0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    _ensure_pg_enum(
        "notificationtype",
        "invoice_created",
        "invoice_updated",
        "invoice_status_changed",
        "invoice_assigned",
        "invoice_unassigned",
        "invoice_overdue_auto",
    )
    op.create_table(
        "notifications",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("organization_id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("type", PGEnumName("notificationtype"), nullable=False),
        sa.Column("title", sa.String(length=160), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("invoice_id", sa.Integer(), nullable=True),
        sa.Column("payload", sa.JSON(), nullable=True),
        sa.Column("is_read", sa.Boolean(), nullable=False, server_default="0"),
        sa.Column("read_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["invoice_id"], ["invoices.id"]),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_notifications_id"), "notifications", ["id"], unique=False)
    op.create_index(
        op.f("ix_notifications_organization_id"), "notifications", ["organization_id"], unique=False
    )
    op.create_index(op.f("ix_notifications_user_id"), "notifications", ["user_id"], unique=False)
    op.create_index(op.f("ix_notifications_invoice_id"), "notifications", ["invoice_id"], unique=False)
    op.create_index(
        "ix_notifications_user_is_read_created",
        "notifications",
        ["user_id", "is_read", "created_at"],
        unique=False,
    )
    op.create_index(
        "ix_notifications_org_created",
        "notifications",
        ["organization_id", "created_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_notifications_org_created", table_name="notifications")
    op.drop_index("ix_notifications_user_is_read_created", table_name="notifications")
    op.drop_index(op.f("ix_notifications_invoice_id"), table_name="notifications")
    op.drop_index(op.f("ix_notifications_user_id"), table_name="notifications")
    op.drop_index(op.f("ix_notifications_organization_id"), table_name="notifications")
    op.drop_index(op.f("ix_notifications_id"), table_name="notifications")
    op.drop_table("notifications")
    op.execute("DROP TYPE IF EXISTS notificationtype")
