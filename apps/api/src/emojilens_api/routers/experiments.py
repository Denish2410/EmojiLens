from __future__ import annotations

from datetime import datetime
from typing import Annotated, Any, Literal

from fastapi import APIRouter, Query, Request
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import func, select

from emojilens_api.db.models import Experiment, ModelOutput, ModelVersion, Source, Variant
from emojilens_api.errors import ApiError, ErrorResponse
from emojilens_api.services import datasets as svc
from emojilens_api.services import provenance
from emojilens_api.services.experiments import (
    SUPPORTED_MODALITIES,
    TERMINAL,
    config_hash,
    count_units,
)
from emojilens_core.models import SAFETY_TASK, Capability, ModelError, ModelRegistry

router = APIRouter(prefix="/experiments", tags=["experiments"])


class ExperimentIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str = Field(min_length=1, max_length=200)
    dataset: str
    version: int = Field(ge=1)
    recipe_hashes: list[str] = Field(default_factory=list, max_length=20)
    model_keys: list[str] = Field(min_length=1, max_length=10)
    capabilities: list[Literal["TOKENIZE", "CLASSIFY", "EMBED", "GENERATE", "VISION_INPUT"]] = (
        Field(min_length=1)
    )
    modalities: list[Literal["text", "ocr", "vlm"]] = Field(default=["text"], min_length=1)
    vlm_prompt: str | None = Field(default=None, min_length=1, max_length=300)
    seed: int = Field(default=0, ge=0)
    label_map: dict[str, Literal["safe", "unsafe"]] | None = None


class ExperimentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str
    status: str
    config: dict[str, Any]
    config_hash: str
    total_items: int
    done_items: int
    failed_items: int
    cancel_requested: bool
    error: str | None
    created_at: datetime
    started_at: datetime | None
    finished_at: datetime | None
    uses_test_doubles: bool = False


class OutputOut(BaseModel):
    id: int
    model_key: str
    model_id: str
    revision: str | None
    test_double: bool
    source_id: str
    variant_id: int | None
    families: str | None
    language: str
    split: str | None
    input_text: str
    capability: str
    modality: str
    normalized: dict[str, Any]
    latency_ms: float
    error: dict[str, Any] | None
    behavior: str | None
    safety: str | None


class OutputPage(BaseModel):
    total: int
    page: int
    page_size: int
    items: list[OutputOut]


def _reg(request: Request) -> ModelRegistry:
    reg: ModelRegistry = request.app.state.registry
    return reg


def _out(exp: Experiment, reg: ModelRegistry) -> ExperimentOut:
    o = ExperimentOut.model_validate(exp)
    keys = exp.config.get("model_keys", [])
    o.uses_test_doubles = any(
        reg.config(k).test_double for k in keys if k in {c.key for c in reg.configs()}
    )
    return o


@router.post(
    "",
    response_model=ExperimentOut,
    status_code=201,
    responses={
        404: {"model": ErrorResponse},
        409: {"model": ErrorResponse},
        422: {"model": ErrorResponse},
    },
)
def create(body: ExperimentIn, request: Request) -> ExperimentOut:
    reg = _reg(request)
    for key in body.model_keys:
        try:
            cfg = reg.config(key)
        except ModelError as exc:
            raise ApiError(404, "model_not_found", exc.message) from exc
        if not any(Capability(c) in cfg.capabilities for c in body.capabilities):
            raise ApiError(
                422, "capability_unsupported", f"{key} supports none of the requested capabilities."
            )
        av = reg.availability(key)
        if not av.ok:
            raise ApiError(409, av.status.value, f"{key} is not available: {av.detail}")
        classifies = "CLASSIFY" in body.capabilities and Capability.CLASSIFY in cfg.capabilities
        if body.label_map and classifies and cfg.task != SAFETY_TASK:
            raise ApiError(
                422,
                "not_a_safety_classifier",
                f"{key} is a '{cfg.task}' model; its labels cannot be mapped to safety judgments.",
            )
    if any(m not in SUPPORTED_MODALITIES for m in body.modalities):
        raise ApiError(422, "modality_unsupported", "Unsupported modality.")
    if ("vlm" in body.modalities) != ("VISION_INPUT" in body.capabilities):
        raise ApiError(
            422,
            "modality_capability_mismatch",
            "The 'vlm' modality needs the VISION_INPUT capability, and VISION_INPUT runs only "
            "with the 'vlm' modality.",
        )
    if body.vlm_prompt is not None and "vlm" not in body.modalities:
        raise ApiError(422, "vlm_prompt_without_vlm", "vlm_prompt applies only to 'vlm' runs.")
    with request.app.state.sessionmaker() as session:
        version = svc.get_version(session, body.dataset, body.version)
        if version.frozen_at is None:
            raise ApiError(
                409, "version_not_frozen", "Experiments run on frozen dataset versions only."
            )
        dumped = body.model_dump()
        if dumped["vlm_prompt"] is None:
            del dumped["vlm_prompt"]  # keep config hashes of non-VLM runs unchanged
        config = dumped | {
            "version_id": version.id,
            "dataset_kind": version.dataset.kind,
        }
        exp = Experiment(
            name=body.name, status="queued", config=config, config_hash=config_hash(config)
        )
        exp.total_items = count_units(session, reg, config)
        session.add(exp)
        session.commit()
        session.refresh(exp)
        return _out(exp, reg)


@router.get("", response_model=list[ExperimentOut])
def list_experiments(request: Request) -> list[ExperimentOut]:
    with request.app.state.sessionmaker() as session:
        return [
            _out(e, _reg(request))
            for e in session.scalars(select(Experiment).order_by(Experiment.id.desc())).all()
        ]


def _get(session: Any, exp_id: int) -> Experiment:
    exp = session.get(Experiment, exp_id)
    if exp is None:
        raise ApiError(404, "experiment_not_found", f"No experiment {exp_id}.")
    return exp  # type: ignore[no-any-return]


@router.get("/{exp_id}", response_model=ExperimentOut, responses={404: {"model": ErrorResponse}})
def get_experiment(exp_id: int, request: Request) -> ExperimentOut:
    with request.app.state.sessionmaker() as session:
        return _out(_get(session, exp_id), _reg(request))


@router.post(
    "/{exp_id}/cancel", response_model=ExperimentOut, responses={409: {"model": ErrorResponse}}
)
def cancel(exp_id: int, request: Request) -> ExperimentOut:
    with request.app.state.sessionmaker() as session:
        exp = _get(session, exp_id)
        if exp.status in TERMINAL:
            raise ApiError(409, "experiment_finished", f"Experiment is already {exp.status}.")
        exp.cancel_requested = True
        if exp.status == "queued":
            exp.status = "cancelled"
        else:
            exp.status = "cancelling"
        session.commit()
        return _out(exp, _reg(request))


@router.post(
    "/{exp_id}/resume", response_model=ExperimentOut, responses={409: {"model": ErrorResponse}}
)
def resume(exp_id: int, request: Request) -> ExperimentOut:
    """Re-queue an interrupted, failed or cancelled run; existing outputs are kept and skipped."""
    with request.app.state.sessionmaker() as session:
        exp = _get(session, exp_id)
        if exp.status not in ("interrupted", "failed", "cancelled"):
            raise ApiError(409, "not_resumable", f"Experiment is {exp.status}.")
        exp.status, exp.cancel_requested, exp.error, exp.finished_at = "queued", False, None, None
        session.commit()
        return _out(exp, _reg(request))


@router.get("/{exp_id}/eligibility", responses={404: {"model": ErrorResponse}})
def get_eligibility(exp_id: int, request: Request) -> dict[str, Any]:
    """Whether this run may appear in a research report, with every failing rule explained."""
    with request.app.state.sessionmaker() as session:
        return provenance.eligibility(session, _reg(request), _get(session, exp_id)).to_dict()


@router.get("/{exp_id}/manifest", responses={404: {"model": ErrorResponse}})
def get_manifest(exp_id: int, request: Request) -> dict[str, Any]:
    """Reproducibility manifest: config, dataset and split hashes, recipes, model builds,
    run environments, an output digest and eligibility. Built from stored rows only."""
    with request.app.state.sessionmaker() as session:
        return provenance.manifest(session, _reg(request), _get(session, exp_id))


@router.get("/{exp_id}/outputs", response_model=OutputPage)
def outputs(
    exp_id: int,
    request: Request,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=200)] = 50,
    capability: str | None = None,
    model_key: str | None = None,
    errors_only: bool = False,
) -> OutputPage:
    with request.app.state.sessionmaker() as session:
        _get(session, exp_id)
        stmt = (
            select(ModelOutput, ModelVersion, Source, Variant)
            .join(ModelVersion, ModelOutput.model_version_id == ModelVersion.id)
            .join(Source, ModelOutput.source_id == Source.id)
            .outerjoin(Variant, ModelOutput.variant_id == Variant.id)
            .where(ModelOutput.experiment_id == exp_id)
        )
        if capability:
            stmt = stmt.where(ModelOutput.capability == capability)
        if model_key:
            stmt = stmt.where(ModelVersion.key == model_key)
        if errors_only:
            stmt = stmt.where(ModelOutput.error.is_not(None))
        total = session.scalar(select(func.count()).select_from(stmt.subquery())) or 0
        rows = session.execute(
            stmt.order_by(ModelOutput.id).offset((page - 1) * page_size).limit(page_size)
        ).all()
        return OutputPage(
            total=total,
            page=page,
            page_size=page_size,
            items=[
                OutputOut(
                    id=o.id,
                    model_key=mv.key,
                    model_id=mv.model_id,
                    revision=mv.revision,
                    test_double=mv.test_double,
                    source_id=s.external_id,
                    variant_id=o.variant_id,
                    families=v.families if v else None,
                    language=s.language,
                    split=s.split,
                    input_text=v.text if v else s.text,
                    capability=o.capability,
                    modality=o.modality,
                    normalized=o.normalized,
                    latency_ms=o.latency_ms,
                    error=o.error,
                    behavior=o.behavior,
                    safety=o.safety,
                )
                for o, mv, s, v in rows
            ],
        )
