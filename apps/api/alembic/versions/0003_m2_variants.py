"""M2: variants and transformation provenance.

Revision ID: 0003_m2_variants
Revises: 0002_m1_datasets
Create Date: 2026-11-24
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0003_m2_variants"
down_revision: str | None = "0002_m1_datasets"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "variants",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column(
            "source_id", sa.Integer, sa.ForeignKey("sources.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column(
            "version_id",
            sa.Integer,
            sa.ForeignKey("dataset_versions.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("recipe_hash", sa.String(64), nullable=False),
        sa.Column("chain_hash", sa.String(64), nullable=False),
        sa.Column("recipe", sa.JSON, nullable=False),
        sa.Column("families", sa.String(256), nullable=False),
        sa.Column("text", sa.Text, nullable=False),
        sa.Column("text_sha256", sa.String(64), nullable=False),
        sa.Column("pieces", sa.JSON, nullable=False),
        sa.Column("steps", sa.JSON, nullable=False),
        sa.Column("valid", sa.Boolean, nullable=False),
        sa.Column("split", sa.String(16), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("source_id", "recipe_hash", name="uq_variants_source_recipe"),
    )
    op.create_index("ix_variants_version_recipe", "variants", ["version_id", "recipe_hash"])
    op.create_index("ix_variants_version_split", "variants", ["version_id", "split"])


def downgrade() -> None:
    op.drop_index("ix_variants_version_split", "variants")
    op.drop_index("ix_variants_version_recipe", "variants")
    op.drop_table("variants")
