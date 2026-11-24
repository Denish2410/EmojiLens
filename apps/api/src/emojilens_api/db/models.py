"""ORM models, added migration by migration (M1: datasets and sources)."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import (
    JSON,
    Boolean,
    CheckConstraint,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from emojilens_api.db import Base, utcnow

DATASET_KINDS = ("evaluation", "synthetic_fixture")


class Dataset(Base):
    __tablename__ = "datasets"
    __table_args__ = (CheckConstraint(f"kind IN {DATASET_KINDS!r}", name="ck_datasets_kind"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    slug: Mapped[str] = mapped_column(String(64), unique=True)
    name: Mapped[str] = mapped_column(String(200))
    description: Mapped[str] = mapped_column(Text, default="")
    kind: Mapped[str] = mapped_column(String(32))
    license: Mapped[str] = mapped_column(String(128))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    versions: Mapped[list[DatasetVersion]] = relationship(
        back_populates="dataset", cascade="all, delete-orphan", order_by="DatasetVersion.number"
    )


class DatasetVersion(Base):
    __tablename__ = "dataset_versions"
    __table_args__ = (UniqueConstraint("dataset_id", "number", name="uq_dataset_versions_number"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    dataset_id: Mapped[int] = mapped_column(ForeignKey("datasets.id", ondelete="CASCADE"))
    number: Mapped[int] = mapped_column(Integer)
    content_sha256: Mapped[str] = mapped_column(String(64))
    record_count: Mapped[int] = mapped_column(Integer)
    schema_version: Mapped[int] = mapped_column(Integer)
    split_seed: Mapped[int | None] = mapped_column(Integer, nullable=True)
    split_ratios: Mapped[list[float] | None] = mapped_column(JSON, nullable=True)
    split_method: Mapped[str | None] = mapped_column(String(64), nullable=True)
    frozen_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    dataset: Mapped[Dataset] = relationship(back_populates="versions")


class Source(Base):
    __tablename__ = "sources"
    __table_args__ = (
        UniqueConstraint("version_id", "external_id", name="uq_sources_external_id"),
        Index("ix_sources_version_split", "version_id", "split"),
        Index("ix_sources_version_group", "version_id", "source_group"),
        Index("ix_sources_text_sha256", "text_sha256"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    version_id: Mapped[int] = mapped_column(ForeignKey("dataset_versions.id", ondelete="CASCADE"))
    external_id: Mapped[str] = mapped_column(String(128))
    source_group: Mapped[str] = mapped_column(String(128))
    text: Mapped[str] = mapped_column(Text)
    text_sha256: Mapped[str] = mapped_column(String(64))
    norm_key: Mapped[str] = mapped_column(String(64))
    language: Mapped[str] = mapped_column(String(16))
    detected_language: Mapped[str | None] = mapped_column(String(16), nullable=True)
    detected_confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    safety_label: Mapped[str] = mapped_column(String(16))
    control: Mapped[str | None] = mapped_column(String(32), nullable=True)
    origin: Mapped[str] = mapped_column(String(256))
    license: Mapped[str] = mapped_column(String(128))
    meta: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    split: Mapped[str | None] = mapped_column(String(16), nullable=True)


class Variant(Base):
    """M2: a transformed variant of a source. Inherits the source's split (never re-assigned)."""

    __tablename__ = "variants"
    __table_args__ = (
        UniqueConstraint("source_id", "recipe_hash", name="uq_variants_source_recipe"),
        Index("ix_variants_version_recipe", "version_id", "recipe_hash"),
        Index("ix_variants_version_split", "version_id", "split"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    source_id: Mapped[int] = mapped_column(ForeignKey("sources.id", ondelete="CASCADE"))
    version_id: Mapped[int] = mapped_column(ForeignKey("dataset_versions.id", ondelete="CASCADE"))
    recipe_hash: Mapped[str] = mapped_column(String(64))
    chain_hash: Mapped[str] = mapped_column(String(64))
    recipe: Mapped[dict[str, Any]] = mapped_column(JSON)
    families: Mapped[str] = mapped_column(String(256))
    text: Mapped[str] = mapped_column(Text)
    text_sha256: Mapped[str] = mapped_column(String(64))
    pieces: Mapped[list[Any]] = mapped_column(JSON)
    steps: Mapped[list[Any]] = mapped_column(JSON)
    valid: Mapped[bool] = mapped_column(Boolean)
    split: Mapped[str] = mapped_column(String(16))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    source: Mapped[Source] = relationship()


# ----------------------------------------------------------------------------- M3: annotation


class Annotator(Base):
    __tablename__ = "annotators"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    pseudonym: Mapped[str] = mapped_column(String(64), unique=True)
    proficiency: Mapped[dict[str, str]] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class Guideline(Base):
    __tablename__ = "guidelines"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    version: Mapped[str] = mapped_column(String(32), unique=True)
    title: Mapped[str] = mapped_column(String(200))
    body: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class AnnotationTask(Base):
    __tablename__ = "annotation_tasks"
    __table_args__ = (
        UniqueConstraint("variant_id", "guideline_id", name="uq_tasks_variant_guideline"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    variant_id: Mapped[int] = mapped_column(ForeignKey("variants.id", ondelete="CASCADE"))
    guideline_id: Mapped[int] = mapped_column(ForeignKey("guidelines.id", ondelete="RESTRICT"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class Annotation(Base):
    __tablename__ = "annotations"
    __table_args__ = (
        UniqueConstraint("task_id", "annotator_id", name="uq_annotations_task_annotator"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    task_id: Mapped[int] = mapped_column(ForeignKey("annotation_tasks.id", ondelete="CASCADE"))
    annotator_id: Mapped[int] = mapped_column(ForeignKey("annotators.id", ondelete="RESTRICT"))
    semantic_label: Mapped[str] = mapped_column(String(16))
    safety_label: Mapped[str] = mapped_column(String(16))
    note: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class Adjudication(Base):
    __tablename__ = "adjudications"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    task_id: Mapped[int] = mapped_column(
        ForeignKey("annotation_tasks.id", ondelete="CASCADE"), unique=True
    )
    semantic_label: Mapped[str] = mapped_column(String(16))
    safety_label: Mapped[str] = mapped_column(String(16))
    adjudicator: Mapped[str] = mapped_column(String(64))
    rationale: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


# ------------------------------------------------------------------ M4: models, experiments

EXPERIMENT_STATES = (
    "queued",
    "running",
    "cancelling",
    "cancelled",
    "completed",
    "failed",
    "interrupted",
)


class ModelVersion(Base):
    """One concrete model build used for inference (fingerprint over all identifying fields)."""

    __tablename__ = "model_versions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    fingerprint: Mapped[str] = mapped_column(String(64), unique=True)
    key: Mapped[str] = mapped_column(String(64))
    model_id: Mapped[str] = mapped_column(String(200))
    revision: Mapped[str | None] = mapped_column(String(64), nullable=True)
    tokenizer_revision: Mapped[str | None] = mapped_column(String(64), nullable=True)
    adapter: Mapped[str] = mapped_column(String(32))
    adapter_version: Mapped[str] = mapped_column(String(16))
    device: Mapped[str] = mapped_column(String(16))
    dtype: Mapped[str | None] = mapped_column(String(32), nullable=True)
    library_versions: Mapped[dict[str, str]] = mapped_column(JSON)
    test_double: Mapped[bool] = mapped_column(Boolean)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class Experiment(Base):
    __tablename__ = "experiments"
    __table_args__ = (
        CheckConstraint(f"status IN {EXPERIMENT_STATES!r}", name="ck_experiments_status"),
        Index("ix_experiments_status", "status"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(200))
    status: Mapped[str] = mapped_column(String(16), default="queued")
    config: Mapped[dict[str, Any]] = mapped_column(JSON)
    config_hash: Mapped[str] = mapped_column(String(64))
    total_items: Mapped[int] = mapped_column(Integer, default=0)
    done_items: Mapped[int] = mapped_column(Integer, default=0)
    failed_items: Mapped[int] = mapped_column(Integer, default=0)
    cancel_requested: Mapped[bool] = mapped_column(Boolean, default=False)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class ModelOutput(Base):
    __tablename__ = "model_outputs"
    __table_args__ = (
        UniqueConstraint(
            "experiment_id",
            "model_version_id",
            "source_id",
            "variant_key",
            "capability",
            "modality",
            name="uq_model_outputs_item",
        ),
        Index("ix_model_outputs_experiment", "experiment_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    experiment_id: Mapped[int] = mapped_column(ForeignKey("experiments.id", ondelete="CASCADE"))
    model_version_id: Mapped[int] = mapped_column(
        ForeignKey("model_versions.id", ondelete="RESTRICT")
    )
    source_id: Mapped[int] = mapped_column(ForeignKey("sources.id", ondelete="CASCADE"))
    variant_id: Mapped[int | None] = mapped_column(
        ForeignKey("variants.id", ondelete="CASCADE"), nullable=True
    )
    variant_key: Mapped[int] = mapped_column(Integer)  # variant id, or 0 for the source itself
    capability: Mapped[str] = mapped_column(String(16))
    modality: Mapped[str] = mapped_column(String(8))
    input_sha256: Mapped[str] = mapped_column(String(64))
    raw: Mapped[Any] = mapped_column(JSON, nullable=True)
    normalized: Mapped[dict[str, Any]] = mapped_column(JSON)
    tokenization: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    params: Mapped[dict[str, Any]] = mapped_column(JSON)
    latency_ms: Mapped[float] = mapped_column(Float)
    error: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    behavior: Mapped[str | None] = mapped_column(String(16), nullable=True)
    safety: Mapped[str | None] = mapped_column(String(16), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


# ------------------------------------------------------------------ M5: consistency metrics


class MetricResult(Base):
    """Stored CRSC results; each row traces to an experiment's stored model outputs."""

    __tablename__ = "metric_results"
    __table_args__ = (Index("ix_metric_results_experiment", "experiment_id", "crsc_version"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    experiment_id: Mapped[int] = mapped_column(ForeignKey("experiments.id", ondelete="CASCADE"))
    crsc_version: Mapped[str] = mapped_column(String(16))
    metric: Mapped[str] = mapped_column(String(16))
    model: Mapped[str] = mapped_column(String(64))
    stratum: Mapped[str] = mapped_column(String(32))
    stratum_value: Mapped[str] = mapped_column(String(128))
    value: Mapped[float | None] = mapped_column(Float, nullable=True)
    ci_low: Mapped[float | None] = mapped_column(Float, nullable=True)
    ci_high: Mapped[float | None] = mapped_column(Float, nullable=True)
    n: Mapped[int] = mapped_column(Integer)
    n_groups: Mapped[int] = mapped_column(Integer)
    details: Mapped[dict[str, Any]] = mapped_column(JSON)
    resamples: Mapped[int] = mapped_column(Integer)
    seed: Mapped[int] = mapped_column(Integer)
    computed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
