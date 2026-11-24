"""M5: consistency metric results.

Revision ID: 0006_m5_metrics
Revises: 0005_m4_experiments
Create Date: 2026-11-25
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0006_m5_metrics"
down_revision: str | None = "0005_m4_experiments"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "metric_results",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column(
            "experiment_id",
            sa.Integer,
            sa.ForeignKey("experiments.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("crsc_version", sa.String(16), nullable=False),
        sa.Column("metric", sa.String(16), nullable=False),
        sa.Column("model", sa.String(64), nullable=False),
        sa.Column("stratum", sa.String(32), nullable=False),
        sa.Column("stratum_value", sa.String(128), nullable=False),
        sa.Column("value", sa.Float, nullable=True),
        sa.Column("ci_low", sa.Float, nullable=True),
        sa.Column("ci_high", sa.Float, nullable=True),
        sa.Column("n", sa.Integer, nullable=False),
        sa.Column("n_groups", sa.Integer, nullable=False),
        sa.Column("details", sa.JSON, nullable=False),
        sa.Column("resamples", sa.Integer, nullable=False),
        sa.Column("seed", sa.Integer, nullable=False),
        sa.Column("computed_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index(
        "ix_metric_results_experiment", "metric_results", ["experiment_id", "crsc_version"]
    )


def downgrade() -> None:
    op.drop_index("ix_metric_results_experiment", "metric_results")
    op.drop_table("metric_results")
