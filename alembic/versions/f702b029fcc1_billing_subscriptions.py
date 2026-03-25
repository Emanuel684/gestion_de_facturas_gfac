"""billing_subscriptions

Revision ID: f702b029fcc1
Revises: f72dc0a687f8
Create Date: 2026-03-25 10:59:26.534339

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


# revision identifiers, used by Alembic.
revision: str = 'f702b029fcc1'
down_revision: Union[str, Sequence[str], None] = 'f72dc0a687f8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # plantier exists from initial_schema (organizations.plan_tier).
    _ensure_pg_enum("subscriptionstatus", "active", "past_due", "suspended", "canceled")
    _ensure_pg_enum("paymentstatus", "pending", "paid", "failed")
    _ensure_pg_enum("checkoutsessionstatus", "created", "completed", "expired")

    op.create_table(
        "subscriptions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("organization_id", sa.Integer(), nullable=False),
        sa.Column("plan_tier", PGEnumName("plantier"), nullable=False),
        sa.Column("status", PGEnumName("subscriptionstatus"), nullable=False),
        sa.Column("current_period_start", sa.DateTime(timezone=True), nullable=True),
        sa.Column("current_period_end", sa.DateTime(timezone=True), nullable=True),
        sa.Column("next_due_date", sa.DateTime(timezone=True), nullable=True),
        sa.Column("grace_expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_paid_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_subscriptions_id"), "subscriptions", ["id"], unique=False)
    op.create_index(
        op.f("ix_subscriptions_organization_id"), "subscriptions", ["organization_id"], unique=False
    )

    op.create_table(
        "payments",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("organization_id", sa.Integer(), nullable=False),
        sa.Column("subscription_id", sa.Integer(), nullable=False),
        sa.Column("amount", sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column("currency", sa.String(length=8), nullable=False),
        sa.Column("status", PGEnumName("paymentstatus"), nullable=False),
        sa.Column("provider", sa.String(length=50), nullable=False),
        sa.Column("provider_reference", sa.String(length=120), nullable=False),
        sa.Column("paid_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"]),
        sa.ForeignKeyConstraint(["subscription_id"], ["subscriptions.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_payments_id"), "payments", ["id"], unique=False)
    op.create_index(op.f("ix_payments_organization_id"), "payments", ["organization_id"], unique=False)
    op.create_index(op.f("ix_payments_provider_reference"), "payments", ["provider_reference"], unique=False)
    op.create_index(op.f("ix_payments_subscription_id"), "payments", ["subscription_id"], unique=False)

    op.create_table(
        "checkout_sessions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("organization_id", sa.Integer(), nullable=False),
        sa.Column("plan_tier", PGEnumName("plantier"), nullable=False),
        sa.Column("amount", sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column("currency", sa.String(length=8), nullable=False),
        sa.Column("session_token", sa.String(length=64), nullable=False),
        sa.Column("status", PGEnumName("checkoutsessionstatus"), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_checkout_sessions_id"), "checkout_sessions", ["id"], unique=False)
    op.create_index(
        op.f("ix_checkout_sessions_organization_id"), "checkout_sessions", ["organization_id"], unique=False
    )
    op.create_index(
        op.f("ix_checkout_sessions_session_token"), "checkout_sessions", ["session_token"], unique=True
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f("ix_checkout_sessions_session_token"), table_name="checkout_sessions")
    op.drop_index(op.f("ix_checkout_sessions_organization_id"), table_name="checkout_sessions")
    op.drop_index(op.f("ix_checkout_sessions_id"), table_name="checkout_sessions")
    op.drop_table("checkout_sessions")

    op.drop_index(op.f("ix_payments_subscription_id"), table_name="payments")
    op.drop_index(op.f("ix_payments_provider_reference"), table_name="payments")
    op.drop_index(op.f("ix_payments_organization_id"), table_name="payments")
    op.drop_index(op.f("ix_payments_id"), table_name="payments")
    op.drop_table("payments")

    op.drop_index(op.f("ix_subscriptions_organization_id"), table_name="subscriptions")
    op.drop_index(op.f("ix_subscriptions_id"), table_name="subscriptions")
    op.drop_table("subscriptions")

    op.execute("DROP TYPE IF EXISTS checkoutsessionstatus")
    op.execute("DROP TYPE IF EXISTS paymentstatus")
    op.execute("DROP TYPE IF EXISTS subscriptionstatus")
