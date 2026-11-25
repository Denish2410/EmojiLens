"""Experiment provenance: eligibility facts and reproducibility manifests from stored rows only."""

from __future__ import annotations

import hashlib
import json
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from emojilens_api.db.models import (
    Dataset,
    DatasetVersion,
    Experiment,
    MetricResult,
    ModelOutput,
    ModelVersion,
    Variant,
)
from emojilens_core.models import ModelRegistry
from emojilens_core.repro.eligibility import (
    Eligibility,
    ExperimentFacts,
    ModelProvenance,
    assess,
)

MANIFEST_SCHEMA = "emojilens.manifest/1"


def _versions_used(session: Session, exp_id: int) -> list[ModelVersion]:
    ids = select(ModelOutput.model_version_id).where(ModelOutput.experiment_id == exp_id).distinct()
    return list(session.scalars(select(ModelVersion).where(ModelVersion.id.in_(ids))).all())


def facts(session: Session, registry: ModelRegistry, exp: Experiment) -> ExperimentFacts:
    version = session.get(DatasetVersion, exp.config.get("version_id"))
    used = _versions_used(session, exp.id)
    if used:
        models = tuple(ModelProvenance(v.key, v.revision, v.test_double) for v in used)
    else:  # no outputs yet: fall back to the registry's current view of the configured models
        known = {c.key: c for c in registry.configs()}
        models = tuple(
            ModelProvenance(k, known[k].revision, known[k].test_double)
            for k in exp.config.get("model_keys", [])
            if k in known
        )
    return ExperimentFacts(
        status=exp.status,
        dataset_kind=str(exp.config.get("dataset_kind", "unknown")),
        dataset_frozen=bool(version and version.frozen_at),
        total_items=exp.total_items,
        done_items=exp.done_items,
        failed_items=exp.failed_items,
        models=models,
        config_hash=exp.config_hash,
        environment_recorded=bool(exp.run_environments),
    )


def eligibility(session: Session, registry: ModelRegistry, exp: Experiment) -> Eligibility:
    return assess(facts(session, registry, exp))


def outputs_digest(session: Session, exp_id: int) -> tuple[int, str]:
    """Order-independent SHA-256 over every stored output's identity and content."""
    rows = session.execute(
        select(
            ModelVersion.fingerprint,
            ModelOutput.source_id,
            ModelOutput.variant_key,
            ModelOutput.capability,
            ModelOutput.modality,
            ModelOutput.input_sha256,
            ModelOutput.raw,
            ModelOutput.normalized,
            ModelOutput.error,
        )
        .join(ModelVersion, ModelVersion.id == ModelOutput.model_version_id)
        .where(ModelOutput.experiment_id == exp_id)
    ).all()
    lines = sorted(
        json.dumps(list(r), sort_keys=True, ensure_ascii=False, default=repr) for r in rows
    )
    h = hashlib.sha256()
    for line in lines:
        h.update(line.encode("utf-8"))
        h.update(b"\n")
    return len(lines), h.hexdigest()


def manifest(session: Session, registry: ModelRegistry, exp: Experiment) -> dict[str, Any]:
    version = session.get(DatasetVersion, exp.config.get("version_id"))
    dataset = session.get(Dataset, version.dataset_id) if version else None
    recipes = []
    for rh in exp.config.get("recipe_hashes", []):
        v = session.scalar(select(Variant).where(Variant.recipe_hash == rh).limit(1))
        recipes.append({"recipe_hash": rh, "recipe": v.recipe if v else None})
    n_outputs, digest = outputs_digest(session, exp.id)
    metric_rows = int(
        session.scalar(
            select(func.count())
            .select_from(MetricResult)
            .where(MetricResult.experiment_id == exp.id)
        )
        or 0
    )
    return {
        "schema": MANIFEST_SCHEMA,
        "experiment": {
            "id": exp.id,
            "name": exp.name,
            "status": exp.status,
            "config": exp.config,
            "config_hash": exp.config_hash,
            "total_items": exp.total_items,
            "done_items": exp.done_items,
            "failed_items": exp.failed_items,
            "created_at": exp.created_at.isoformat() if exp.created_at else None,
            "started_at": exp.started_at.isoformat() if exp.started_at else None,
            "finished_at": exp.finished_at.isoformat() if exp.finished_at else None,
        },
        "dataset": None
        if version is None or dataset is None
        else {
            "slug": dataset.slug,
            "kind": dataset.kind,
            "license": dataset.license,
            "version": version.number,
            "content_sha256": version.content_sha256,
            "record_count": version.record_count,
            "schema_version": version.schema_version,
            "split_seed": version.split_seed,
            "split_ratios": version.split_ratios,
            "split_method": version.split_method,
            "frozen_at": version.frozen_at.isoformat() if version.frozen_at else None,
        },
        "recipes": recipes,
        "models": [
            {
                "fingerprint": v.fingerprint,
                "key": v.key,
                "model_id": v.model_id,
                "revision": v.revision,
                "tokenizer_revision": v.tokenizer_revision,
                "adapter": v.adapter,
                "adapter_version": v.adapter_version,
                "device": v.device,
                "dtype": v.dtype,
                "library_versions": v.library_versions,
                "test_double": v.test_double,
            }
            for v in sorted(_versions_used(session, exp.id), key=lambda v: v.key)
        ],
        "run_environments": exp.run_environments or [],
        "outputs": {"count": n_outputs, "sha256": digest},
        "metric_rows": metric_rows,
        "eligibility": eligibility(session, registry, exp).to_dict(),
    }
