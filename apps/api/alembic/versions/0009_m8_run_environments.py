"""M8: record the environment each experiment run started in.

Revision ID: 0009_m8_run_environments
Revises: 0008_m7_guard
Create Date: 2026-11-26
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0009_m8_run_environments"
down_revision: str | None = "0008_m7_guard"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("experiments") as batch:
        batch.add_column(sa.Column("run_environments", sa.JSON, nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("experiments") as batch:
        batch.drop_column("run_environments")
