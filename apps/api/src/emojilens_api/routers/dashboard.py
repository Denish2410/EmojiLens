"""Dashboard summary: counts of what is actually stored, plus research-readiness checks.

Every number here is a count or status read from the database or the model registry at request
time. Nothing is estimated or projected. Results from synthetic fixtures or test doubles are counted
separately and are never called reportable.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Request
from pydantic import BaseModel
from sqlalchemy import distinct, func, select
from sqlalchemy.orm import Session

from emojilens_api.db.models import (
    Adjudication,
    Annotation,
    Annotator,
    Dataset,
    DatasetVersion,
    DetectorArtifact,
    Experiment,
    GuardEvaluation,
    MetricResult,
    ModelOutput,
    ModelVersion,
    RenderArtifact,
    Source,
    Variant,
)

router = APIRouter(prefix="/dashboard", tags=["dashboard"])

EXPERIMENT_STATES = (
    "queued",
    "running",
    "cancelling",
    "completed",
    "failed",
    "cancelled",
    "interrupted",
)


class ReadinessItem(BaseModel):
    key: str
    label: str
    ok: bool
    detail: str


class DashboardSummary(BaseModel):
    datasets: dict[str, Any]
    languages: dict[str, int]
    transforms: dict[str, Any]
    annotation: dict[str, int]
    models: dict[str, Any]
    experiments: dict[str, Any]
    crsc: dict[str, int]
    multimodal: dict[str, int]
    guard: dict[str, int]
    readiness: list[ReadinessItem]
    reportable: bool


def _grouped(session: Session, stmt: Any) -> dict[str, int]:
    return {str(k): int(v) for k, v in session.execute(stmt).all()}


def _count(session: Session, stmt: Any) -> int:
    return int(session.scalar(stmt) or 0)


def _reportable_experiment_ids(session: Session) -> set[int]:
    """Completed runs on evaluation datasets whose stored outputs include no test double."""
    completed = session.scalars(select(Experiment).where(Experiment.status == "completed")).all()
    on_eval = {e.id for e in completed if e.config.get("dataset_kind") == "evaluation"}
    if not on_eval:
        return set()
    tainted = set(
        session.scalars(
            select(distinct(ModelOutput.experiment_id))
            .join(ModelVersion, ModelVersion.id == ModelOutput.model_version_id)
            .where(ModelOutput.experiment_id.in_(on_eval), ModelVersion.test_double.is_(True))
        ).all()
    )
    with_outputs = set(
        session.scalars(
            select(distinct(ModelOutput.experiment_id)).where(
                ModelOutput.experiment_id.in_(on_eval)
            )
        ).all()
    )
    return with_outputs - tainted


@router.get("/summary", response_model=DashboardSummary)
def summary(request: Request) -> DashboardSummary:
    reg = request.app.state.registry
    with request.app.state.sessionmaker() as s:
        by_kind = _grouped(s, select(Dataset.kind, func.count()).group_by(Dataset.kind))
        versions = _count(s, select(func.count()).select_from(DatasetVersion))
        frozen = _count(
            s,
            select(func.count())
            .select_from(DatasetVersion)
            .where(DatasetVersion.frozen_at.isnot(None)),
        )
        frozen_eval = _count(
            s,
            select(func.count())
            .select_from(DatasetVersion)
            .join(Dataset, Dataset.id == DatasetVersion.dataset_id)
            .where(DatasetVersion.frozen_at.isnot(None), Dataset.kind == "evaluation"),
        )
        sources = _count(s, select(func.count()).select_from(Source))
        languages = _grouped(s, select(Source.language, func.count()).group_by(Source.language))
        variants = _count(s, select(func.count()).select_from(Variant))
        invalid_variants = _count(
            s, select(func.count()).select_from(Variant).where(Variant.valid.is_(False))
        )
        family_rows = s.scalars(select(distinct(Variant.families))).all()
        families = sorted({f for row in family_rows for f in row.split("+") if f})
        recipes = _count(s, select(func.count(distinct(Variant.recipe_hash))))
        annotators = _count(s, select(func.count()).select_from(Annotator))
        annotations = _count(s, select(func.count()).select_from(Annotation))
        adjudications = _count(s, select(func.count()).select_from(Adjudication))

        exp_status = _grouped(
            s, select(Experiment.status, func.count()).group_by(Experiment.status)
        )
        outputs = _count(s, select(func.count()).select_from(ModelOutput))
        failed_outputs = _count(
            s, select(func.count()).select_from(ModelOutput).where(ModelOutput.error.isnot(None))
        )
        td_outputs = _count(
            s,
            select(func.count())
            .select_from(ModelOutput)
            .join(ModelVersion, ModelVersion.id == ModelOutput.model_version_id)
            .where(ModelVersion.test_double.is_(True)),
        )
        reportable_ids = _reportable_experiment_ids(s)
        metric_rows = _count(s, select(func.count()).select_from(MetricResult))
        metric_experiments = _count(s, select(func.count(distinct(MetricResult.experiment_id))))
        renders = _count(s, select(func.count()).select_from(RenderArtifact))
        guard_evals = _count(s, select(func.count()).select_from(GuardEvaluation))
        detectors = _count(s, select(func.count()).select_from(DetectorArtifact))

    configs = list(reg.configs())
    availability: dict[str, int] = {}
    real_available = 0
    for cfg in configs:
        status = reg.availability(cfg.key).status.value
        availability[status] = availability.get(status, 0) + 1
        if status == "available" and not cfg.test_double and cfg.key != "tesseract-ocr":
            real_available += 1
    tesseract_ok = any(c.key == "tesseract-ocr" and reg.availability(c.key).ok for c in configs)

    readiness = [
        ReadinessItem(
            key="evaluation_dataset",
            label="Frozen evaluation dataset",
            ok=frozen_eval > 0,
            detail=f"{frozen_eval} frozen evaluation version(s); synthetic fixtures do not count",
        ),
        ReadinessItem(
            key="human_annotation",
            label="Human annotations",
            ok=annotations > 0,
            detail=f"{annotations} annotation(s) by {annotators} annotator(s), "
            f"{adjudications} adjudication(s)",
        ),
        ReadinessItem(
            key="real_model",
            label="Real neural model installed",
            ok=real_available > 0,
            detail=f"{real_available} installed (test doubles and OCR excluded)",
        ),
        ReadinessItem(
            key="ocr",
            label="OCR engine",
            ok=tesseract_ok,
            detail="Tesseract available" if tesseract_ok else "Tesseract not available",
        ),
        ReadinessItem(
            key="reportable_experiment",
            label="Reportable experiment",
            ok=bool(reportable_ids),
            detail=f"{len(reportable_ids)} completed run(s) on evaluation data with no test double",
        ),
    ]

    return DashboardSummary(
        datasets={
            "total": sum(by_kind.values()),
            "by_kind": by_kind,
            "versions": versions,
            "frozen_versions": frozen,
            "sources": sources,
        },
        languages=languages,
        transforms={
            "variants": variants,
            "invalid_variants": invalid_variants,
            "recipes": recipes,
            "families": families,
        },
        annotation={
            "annotators": annotators,
            "annotations": annotations,
            "adjudications": adjudications,
        },
        models={
            "catalogue": sum(1 for c in configs if not c.test_double),
            "test_doubles": sum(1 for c in configs if c.test_double),
            "availability": availability,
        },
        experiments={
            "by_status": {k: int(exp_status.get(k, 0)) for k in EXPERIMENT_STATES},
            "outputs": outputs,
            "failed_outputs": failed_outputs,
            "test_double_outputs": td_outputs,
            "reportable": len(reportable_ids),
        },
        crsc={"metric_rows": metric_rows, "experiments": metric_experiments},
        multimodal={"render_artifacts": renders},
        guard={"evaluations": guard_evals, "detector_artifacts": detectors},
        readiness=readiness,
        reportable=bool(reportable_ids),
    )
