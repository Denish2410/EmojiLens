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
