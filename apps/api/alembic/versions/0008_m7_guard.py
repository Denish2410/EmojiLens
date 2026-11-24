"""M7: guard evaluations and detector artifacts.

Revision ID: 0008_m7_guard
Revises: 0007_m6_render_artifacts
Create Date: 2026-11-25
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0008_m7_guard"
down_revision: str | None = "0007_m6_render_artifacts"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

TS = sa.DateTime(timezone=True)


def upgrade() -> None:
    op.create_table(
        "detector_artifacts",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("version", sa.String(64), nullable=False),
        sa.Column("rel_path", sa.String(256), nullable=False),
        sa.Column("sha256", sa.String(64), nullable=False),
        sa.Column("feature_schema", sa.JSON, nullable=False),
        sa.Column("training_config", sa.JSON, nullable=False),
        sa.Column("evaluation", sa.JSON, nullable=False),
        sa.Column("created_at", TS, nullable=False),
    )
    op.create_table(
        "guard_evaluations",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("config", sa.JSON, nullable=False),
        sa.Column("results", sa.JSON, nullable=False),
        sa.Column("created_at", TS, nullable=False),
    )


def downgrade() -> None:
    op.drop_table("guard_evaluations")
    op.drop_table("detector_artifacts")
