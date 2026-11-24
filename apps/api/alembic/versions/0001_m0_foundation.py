"""M0: database foundation (app_meta).

Revision ID: 0001_m0_foundation
Revises:
Create Date: 2026-11-24
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0001_m0_foundation"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = ("m0",)
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "app_meta",
        sa.Column("key", sa.String(64), primary_key=True),
        sa.Column("value", sa.String(1024), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.execute(
        "INSERT INTO app_meta (key, value, updated_at) "
        "VALUES ('schema_initialized_at', datetime('now'), datetime('now'))"
    )


def downgrade() -> None:
    op.drop_table("app_meta")
