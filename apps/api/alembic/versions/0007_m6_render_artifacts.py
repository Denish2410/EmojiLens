"""M6: render artifacts and multimodal metadata.

Revision ID: 0007_m6_render_artifacts
Revises: 0006_m5_metrics
Create Date: 2026-11-25
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0007_m6_render_artifacts"
down_revision: str | None = "0006_m5_metrics"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "render_artifacts",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("text_sha256", sa.String(64), nullable=False),
        sa.Column("config_hash", sa.String(64), nullable=False),
        sa.Column("renderer", sa.String(16), nullable=False),
        sa.Column("renderer_version", sa.String(16), nullable=False),
        sa.Column("rel_path", sa.String(256), nullable=False),
        sa.Column("image_sha256", sa.String(64), nullable=False),
        sa.Column("width", sa.Integer, nullable=False),
        sa.Column("height", sa.Integer, nullable=False),
        sa.Column("provenance", sa.JSON, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint(
            "text_sha256", "config_hash", "renderer", name="uq_render_artifacts_input"
        ),
    )


def downgrade() -> None:
    op.drop_table("render_artifacts")
