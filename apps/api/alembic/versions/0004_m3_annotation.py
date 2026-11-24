"""M3: annotators, guidelines, annotation tasks, annotations, adjudications.

Revision ID: 0004_m3_annotation
Revises: 0003_m2_variants
Create Date: 2026-11-24
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0004_m3_annotation"
down_revision: str | None = "0003_m2_variants"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

TS = sa.DateTime(timezone=True)


def upgrade() -> None:
    op.create_table(
        "annotators",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("pseudonym", sa.String(64), nullable=False, unique=True),
        sa.Column("proficiency", sa.JSON, nullable=False),
        sa.Column("created_at", TS, nullable=False),
    )
    op.create_table(
        "guidelines",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("version", sa.String(32), nullable=False, unique=True),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("body", sa.Text, nullable=False),
        sa.Column("created_at", TS, nullable=False),
    )
    op.create_table(
        "annotation_tasks",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column(
            "variant_id",
            sa.Integer,
            sa.ForeignKey("variants.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "guideline_id",
            sa.Integer,
            sa.ForeignKey("guidelines.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("created_at", TS, nullable=False),
        sa.UniqueConstraint("variant_id", "guideline_id", name="uq_tasks_variant_guideline"),
    )
    op.create_table(
        "annotations",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column(
            "task_id",
            sa.Integer,
            sa.ForeignKey("annotation_tasks.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "annotator_id",
            sa.Integer,
            sa.ForeignKey("annotators.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("semantic_label", sa.String(16), nullable=False),
        sa.Column("safety_label", sa.String(16), nullable=False),
        sa.Column("note", sa.Text, nullable=False),
        sa.Column("created_at", TS, nullable=False),
        sa.UniqueConstraint("task_id", "annotator_id", name="uq_annotations_task_annotator"),
    )
    op.create_table(
        "adjudications",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column(
            "task_id",
            sa.Integer,
            sa.ForeignKey("annotation_tasks.id", ondelete="CASCADE"),
            nullable=False,
            unique=True,
        ),
        sa.Column("semantic_label", sa.String(16), nullable=False),
        sa.Column("safety_label", sa.String(16), nullable=False),
        sa.Column("adjudicator", sa.String(64), nullable=False),
        sa.Column("rationale", sa.Text, nullable=False),
        sa.Column("created_at", TS, nullable=False),
    )


def downgrade() -> None:
    for table in ("adjudications", "annotations", "annotation_tasks", "guidelines", "annotators"):
        op.drop_table(table)
