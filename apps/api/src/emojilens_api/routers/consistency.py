from __future__ import annotations

from datetime import datetime
from typing import Any

from fastapi import APIRouter, Request
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select

from emojilens_api.db.models import Experiment, MetricResult, ModelOutput, ModelVersion
from emojilens_api.errors import ApiError, ErrorResponse
from emojilens_api.services.consistency import compute_and_store
from emojilens_core.eval import CRSC_VERSION

router = APIRouter(prefix="/experiments", tags=["consistency"])


class ComputeIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    resamples: int = Field(default=2000, ge=100, le=20000)
    seed: int = Field(default=0, ge=0)


class MetricOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    metric: str
    model: str
    stratum: str
    stratum_value: str
    value: float | None
    ci_low: float | None
    ci_high: float | None
    n: int
    n_groups: int
    details: dict[str, Any]


class CRSCOut(BaseModel):
    experiment_id: int
    crsc_version: str
    experimental: bool = True
    computed_at: datetime | None
    resamples: int | None
    seed: int | None
    synthetic_fixture: bool
    test_double: bool
    research_reportable: bool
    results: list[MetricOut]


def _flags(session: Any, exp: Experiment) -> tuple[bool, bool]:
    synthetic = exp.config.get("dataset_kind") == "synthetic_fixture"
    td = bool(
        session.scalar(
            select(ModelVersion.id)
            .join(ModelOutput, ModelOutput.model_version_id == ModelVersion.id)
            .where(ModelOutput.experiment_id == exp.id, ModelVersion.test_double.is_(True))
            .limit(1)
        )
    )
    return synthetic, td


def _read(session: Any, exp: Experiment) -> CRSCOut:
    rows = session.scalars(
        select(MetricResult)
        .where(MetricResult.experiment_id == exp.id, MetricResult.crsc_version == CRSC_VERSION)
        .order_by(MetricResult.id)
    ).all()
    synthetic, td = _flags(session, exp)
    return CRSCOut(
        experiment_id=exp.id,
        crsc_version=CRSC_VERSION,
        computed_at=rows[0].computed_at if rows else None,
        resamples=rows[0].resamples if rows else None,
        seed=rows[0].seed if rows else None,
        synthetic_fixture=synthetic,
        test_double=td,
        research_reportable=not (synthetic or td),
        results=[MetricOut.model_validate(r) for r in rows],
    )


def _exp(session: Any, exp_id: int) -> Experiment:
    exp = session.get(Experiment, exp_id)
    if exp is None:
        raise ApiError(404, "experiment_not_found", f"No experiment {exp_id}.")
    return exp  # type: ignore[no-any-return]


@router.post("/{exp_id}/crsc", response_model=CRSCOut, responses={409: {"model": ErrorResponse}})
def compute(exp_id: int, body: ComputeIn, request: Request) -> CRSCOut:
    with request.app.state.sessionmaker() as session:
        exp = _exp(session, exp_id)
        if exp.status != "completed":
            raise ApiError(
                409,
                "experiment_not_completed",
                f"Experiment is {exp.status}; CRSC needs a completed run.",
            )
        compute_and_store(session, exp, body.resamples, body.seed)
        return _read(session, exp)


@router.get("/{exp_id}/crsc", response_model=CRSCOut, responses={404: {"model": ErrorResponse}})
def read(exp_id: int, request: Request) -> CRSCOut:
    with request.app.state.sessionmaker() as session:
        return _read(session, _exp(session, exp_id))
