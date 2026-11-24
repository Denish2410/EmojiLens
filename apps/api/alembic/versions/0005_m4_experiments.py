"""M4: model versions, experiments and model outputs.

Revision ID: 0005_m4_experiments
Revises: 0004_m3_annotation
Create Date: 2026-11-25
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0005_m4_experiments"
down_revision: str | None = "0004_m3_annotation"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

TS = sa.DateTime(timezone=True)
STATES = "('queued', 'running', 'cancelling', 'cancelled', 'completed', 'failed', 'interrupted')"


def upgrade() -> None:
    op.create_table(
        "model_versions",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("fingerprint", sa.String(64), nullable=False, unique=True),
        sa.Column("key", sa.String(64), nullable=False),
        sa.Column("model_id", sa.String(200), nullable=False),
        sa.Column("revision", sa.String(64), nullable=True),
        sa.Column("tokenizer_revision", sa.String(64), nullable=True),
        sa.Column("adapter", sa.String(32), nullable=False),
        sa.Column("adapter_version", sa.String(16), nullable=False),
        sa.Column("device", sa.String(16), nullable=False),
        sa.Column("dtype", sa.String(32), nullable=True),
        sa.Column("library_versions", sa.JSON, nullable=False),
        sa.Column("test_double", sa.Boolean, nullable=False),
        sa.Column("created_at", TS, nullable=False),
    )
    op.create_table(
        "experiments",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("config", sa.JSON, nullable=False),
        sa.Column("config_hash", sa.String(64), nullable=False),
        sa.Column("total_items", sa.Integer, nullable=False),
        sa.Column("done_items", sa.Integer, nullable=False),
        sa.Column("failed_items", sa.Integer, nullable=False),
        sa.Column("cancel_requested", sa.Boolean, nullable=False),
        sa.Column("error", sa.Text, nullable=True),
        sa.Column("created_at", TS, nullable=False),
        sa.Column("started_at", TS, nullable=True),
        sa.Column("finished_at", TS, nullable=True),
        sa.CheckConstraint(f"status IN {STATES}", name="ck_experiments_status"),
    )
    op.create_index("ix_experiments_status", "experiments", ["status"])
    op.create_table(
        "model_outputs",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column(
            "experiment_id",
            sa.Integer,
            sa.ForeignKey("experiments.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "model_version_id",
            sa.Integer,
            sa.ForeignKey("model_versions.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "source_id", sa.Integer, sa.ForeignKey("sources.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column(
            "variant_id",
            sa.Integer,
            sa.ForeignKey("variants.id", ondelete="CASCADE"),
            nullable=True,
        ),
        sa.Column("variant_key", sa.Integer, nullable=False),
        sa.Column("capability", sa.String(16), nullable=False),
        sa.Column("modality", sa.String(8), nullable=False),
        sa.Column("input_sha256", sa.String(64), nullable=False),
        sa.Column("raw", sa.JSON, nullable=True),
        sa.Column("normalized", sa.JSON, nullable=False),
        sa.Column("tokenization", sa.JSON, nullable=True),
        sa.Column("params", sa.JSON, nullable=False),
        sa.Column("latency_ms", sa.Float, nullable=False),
        sa.Column("error", sa.JSON, nullable=True),
        sa.Column("behavior", sa.String(16), nullable=True),
        sa.Column("safety", sa.String(16), nullable=True),
        sa.Column("created_at", TS, nullable=False),
        sa.UniqueConstraint(
            "experiment_id",
            "model_version_id",
            "source_id",
            "variant_key",
            "capability",
            "modality",
            name="uq_model_outputs_item",
        ),
    )
    op.create_index("ix_model_outputs_experiment", "model_outputs", ["experiment_id"])


def downgrade() -> None:
    op.drop_index("ix_model_outputs_experiment", "model_outputs")
    op.drop_table("model_outputs")
    op.drop_index("ix_experiments_status", "experiments")
    op.drop_table("experiments")
    op.drop_table("model_versions")
