"""M1: datasets, dataset versions and sources.

Revision ID: 0002_m1_datasets
Revises: 0001_m0_foundation
Create Date: 2026-11-24
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0002_m1_datasets"
down_revision: str | None = "0001_m0_foundation"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "datasets",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("slug", sa.String(64), nullable=False, unique=True),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("description", sa.Text, nullable=False),
        sa.Column("kind", sa.String(32), nullable=False),
        sa.Column("license", sa.String(128), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("kind IN ('evaluation', 'synthetic_fixture')", name="ck_datasets_kind"),
    )
    op.create_table(
        "dataset_versions",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column(
            "dataset_id",
            sa.Integer,
            sa.ForeignKey("datasets.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("number", sa.Integer, nullable=False),
        sa.Column("content_sha256", sa.String(64), nullable=False),
        sa.Column("record_count", sa.Integer, nullable=False),
        sa.Column("schema_version", sa.Integer, nullable=False),
        sa.Column("split_seed", sa.Integer, nullable=True),
        sa.Column("split_ratios", sa.JSON, nullable=True),
        sa.Column("split_method", sa.String(64), nullable=True),
        sa.Column("frozen_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("dataset_id", "number", name="uq_dataset_versions_number"),
    )
    op.create_table(
        "sources",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column(
            "version_id",
            sa.Integer,
            sa.ForeignKey("dataset_versions.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("external_id", sa.String(128), nullable=False),
        sa.Column("source_group", sa.String(128), nullable=False),
        sa.Column("text", sa.Text, nullable=False),
        sa.Column("text_sha256", sa.String(64), nullable=False),
        sa.Column("norm_key", sa.String(64), nullable=False),
        sa.Column("language", sa.String(16), nullable=False),
        sa.Column("detected_language", sa.String(16), nullable=True),
        sa.Column("detected_confidence", sa.Float, nullable=True),
        sa.Column("safety_label", sa.String(16), nullable=False),
        sa.Column("control", sa.String(32), nullable=True),
        sa.Column("origin", sa.String(256), nullable=False),
        sa.Column("license", sa.String(128), nullable=False),
        sa.Column("meta", sa.JSON, nullable=False),
        sa.Column("split", sa.String(16), nullable=True),
        sa.UniqueConstraint("version_id", "external_id", name="uq_sources_external_id"),
    )
    op.create_index("ix_sources_version_split", "sources", ["version_id", "split"])
    op.create_index("ix_sources_version_group", "sources", ["version_id", "source_group"])
    op.create_index("ix_sources_text_sha256", "sources", ["text_sha256"])


def downgrade() -> None:
    op.drop_index("ix_sources_text_sha256", "sources")
    op.drop_index("ix_sources_version_group", "sources")
    op.drop_index("ix_sources_version_split", "sources")
    op.drop_table("sources")
    op.drop_table("dataset_versions")
    op.drop_table("datasets")
