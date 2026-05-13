"""Add organizations.portal_path for tenant login URLs.

Revision ID: e3a1c0d9b2e5
Revises: c8e4a1b2d3f4
Create Date: 2026-05-14

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "e3a1c0d9b2e5"
down_revision: Union[str, None] = "c8e4a1b2d3f4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("organizations", sa.Column("portal_path", sa.String(length=80), nullable=True))
    op.execute(sa.text("UPDATE organizations SET portal_path = slug"))
    op.alter_column("organizations", "portal_path", nullable=False)
    op.create_index(
        op.f("ix_organizations_portal_path"),
        "organizations",
        ["portal_path"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_organizations_portal_path"), table_name="organizations")
    op.drop_column("organizations", "portal_path")
