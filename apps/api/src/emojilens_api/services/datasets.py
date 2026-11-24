"""Dataset service: import, freeze, browse, statistics and leakage validation."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from emojilens_api.db import utcnow
from emojilens_api.db.models import Dataset, DatasetVersion, Source, Variant
from emojilens_api.errors import ApiError
from emojilens_core.datasets import (
    SCHEMA_VERSION,
    SPLIT_METHOD,
    LeakageIssue,
    LeakageRow,
    assign_split,
    check_leakage,
    content_hash,
    find_duplicates,
    normalized_key,
    parse_jsonl,
    text_sha256,
)
from emojilens_core.multilingual import identify


def get_dataset(session: Session, slug: str) -> Dataset:
    ds = session.scalar(select(Dataset).where(Dataset.slug == slug))
    if ds is None:
        raise ApiError(404, "dataset_not_found", f"No dataset with slug '{slug}'.")
    return ds


def get_version(session: Session, slug: str, number: int) -> DatasetVersion:
    ds = get_dataset(session, slug)
    version = session.scalar(
        select(DatasetVersion).where(
            DatasetVersion.dataset_id == ds.id, DatasetVersion.number == number
        )
    )
    if version is None:
        raise ApiError(404, "version_not_found", f"Dataset '{slug}' has no version {number}.")
    return version


@dataclass(frozen=True, slots=True)
class ImportOutcome:
    version: DatasetVersion
    duplicates: list[dict[str, Any]]


def import_version(session: Session, ds: Dataset, data: bytes) -> ImportOutcome:
    """Validate a JSONL upload and store it as a new immutable version (all or nothing)."""
    parsed = parse_jsonl(data)
    if parsed.errors:
        raise ApiError(
            422,
            "dataset_validation_failed",
            f"{len(parsed.errors)} line(s) failed validation; nothing was imported.",
            {"errors": [vars_line(e) for e in parsed.errors]},
        )
    if not parsed.records:
        raise ApiError(422, "dataset_empty", "The upload contains no records.")

    number = (
        session.scalar(
            select(func.max(DatasetVersion.number)).where(DatasetVersion.dataset_id == ds.id)
        )
        or 0
    ) + 1
    version = DatasetVersion(
        dataset_id=ds.id,
        number=number,
        content_sha256=content_hash(parsed.records),
        record_count=len(parsed.records),
        schema_version=SCHEMA_VERSION,
    )
    session.add(version)
    session.flush()
    for rec in parsed.records:
        ident = identify(rec.text)
        session.add(
            Source(
                version_id=version.id,
                external_id=rec.id,
                source_group=rec.group,
                text=rec.text,
                text_sha256=text_sha256(rec.text),
                norm_key=normalized_key(rec.text),
                language=rec.language.value,
                detected_language=ident.label.value if ident.label else None,
                detected_confidence=ident.confidence if ident.label else None,
                safety_label=rec.safety_label.value,
                control=rec.control.value if rec.control else None,
                origin=rec.origin,
                license=rec.license,
                meta=rec.meta,
            )
        )
    duplicates = [{"kind": d.kind, "ids": list(d.ids)} for d in find_duplicates(parsed.records)]
    return ImportOutcome(version, duplicates)


def vars_line(e: Any) -> dict[str, Any]:
    return {"line": e.line, "code": e.code, "message": e.message}


def freeze_version(
    session: Session, version: DatasetVersion, seed: int, ratios: tuple[float, float, float]
) -> None:
    """Assign splits by source group, once. Frozen versions are immutable."""
    if version.frozen_at is not None:
        raise ApiError(409, "version_frozen", "This version is already frozen.")
    try:
        sources = session.scalars(select(Source).where(Source.version_id == version.id)).all()
        for s in sources:
            s.split = assign_split(s.source_group, seed, ratios).value
    except ValueError as exc:
        raise ApiError(422, "invalid_split_ratios", str(exc)) from exc
    version.split_seed = seed
    version.split_ratios = list(ratios)
    version.split_method = SPLIT_METHOD
    version.frozen_at = utcnow()


def leakage(session: Session, version: DatasetVersion) -> list[LeakageIssue]:
    rows = session.execute(
        select(Source.external_id, Source.source_group, Source.split, Source.text).where(
            Source.version_id == version.id
        )
    ).all()
    leak_rows = [LeakageRow(r[0], r[1], r[2], r[3]) for r in rows]
    variant_rows = session.execute(
        select(
            Variant.id,
            Source.external_id,
            Source.source_group,
            Variant.split,
            Variant.text,
            Source.split,
        )
        .join(Source, Variant.source_id == Source.id)
        .where(Variant.version_id == version.id)
    ).all()
    mismatches = [
        LeakageIssue("variant_split_mismatch", (f"{ext}#v{vid}",), (str(vsplit), str(ssplit)))
        for vid, ext, _g, vsplit, _t, ssplit in variant_rows
        if vsplit != ssplit
    ]
    leak_rows += [
        LeakageRow(f"{ext}#v{vid}", group, vsplit, text)
        for vid, ext, group, vsplit, text, _ in variant_rows
    ]
    return mismatches + check_leakage(leak_rows)


def _counts(session: Session, version_id: int, column: Any) -> dict[str, int]:
    rows = session.execute(
        select(column, func.count()).where(Source.version_id == version_id).group_by(column)
    ).all()
    return {
        ("(none)" if k is None else str(k)): int(n)
        for k, n in sorted(rows, key=lambda r: str(r[0]))
    }


def stats(session: Session, version: DatasetVersion) -> dict[str, dict[str, int]]:
    return {
        "language": _counts(session, version.id, Source.language),
        "split": _counts(session, version.id, Source.split),
        "safety_label": _counts(session, version.id, Source.safety_label),
        "control": _counts(session, version.id, Source.control),
        "variants_by_split": {
            str(k): int(n)
            for k, n in session.execute(
                select(Variant.split, func.count())
                .where(Variant.version_id == version.id)
                .group_by(Variant.split)
            ).all()
        },
    }


def language_agreement(session: Session, version: DatasetVersion) -> dict[str, int]:
    rows = session.execute(
        select(Source.language, Source.detected_language).where(Source.version_id == version.id)
    ).all()
    agree = sum(1 for lang, det in rows if lang == det)
    undetected = sum(1 for _, det in rows if det is None)
    return {
        "agree": agree,
        "disagree": len(rows) - agree - undetected,
        "undetected": undetected,
    }


def list_sources(
    session: Session,
    version: DatasetVersion,
    *,
    page: int,
    page_size: int,
    language: str | None = None,
    split: str | None = None,
    safety_label: str | None = None,
    control: str | None = None,
    q: str | None = None,
) -> tuple[int, Sequence[Source]]:
    stmt = select(Source).where(Source.version_id == version.id)
    if language:
        stmt = stmt.where(Source.language == language)
    if split:
        stmt = stmt.where(Source.split == split)
    if safety_label:
        stmt = stmt.where(Source.safety_label == safety_label)
    if control:
        stmt = stmt.where(Source.control == control)
    if q:
        stmt = stmt.where(Source.text.contains(q, autoescape=True))
    total = session.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    rows = session.scalars(
        stmt.order_by(Source.external_id).offset((page - 1) * page_size).limit(page_size)
    ).all()
    return total, rows
