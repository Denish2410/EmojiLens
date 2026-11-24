"""Human annotation workflow: annotators, guidelines, blinded queues, adjudication, agreement.

All labels stored here are entered by people through this API. Nothing is generated. The
queue is blinded: it never reveals the transformation family, the recipe, model outputs or
other annotators' labels.
"""

from __future__ import annotations

import hashlib
from collections import defaultdict
from itertools import combinations
from typing import Annotated, Literal

from fastapi import APIRouter, Query, Request
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError

from emojilens_api.db.models import (
    Adjudication,
    Annotation,
    AnnotationTask,
    Annotator,
    Guideline,
    Source,
    Variant,
)
from emojilens_api.errors import ApiError, ErrorResponse
from emojilens_api.services import datasets as svc
from emojilens_core.annotation import cohen_kappa, krippendorff_alpha_nominal

router = APIRouter(prefix="/annotation", tags=["annotation"])

Semantic = Literal["equivalent", "partial", "not_equivalent", "unsure"]
Safety = Literal["safe", "unsafe", "unsure"]
Level = Literal["none", "basic", "fluent", "native"]
Pseudonym = Annotated[str, Field(min_length=2, max_length=64, pattern=r"^[A-Za-z0-9_-]+$")]


class Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")


class AnnotatorIn(Strict):
    pseudonym: Pseudonym
    proficiency: dict[Literal["en", "hi", "gu", "hi-Latn", "gu-Latn"], Level]


class AnnotatorOut(BaseModel):
    pseudonym: str
    proficiency: dict[str, str]
    annotations: int


class GuidelineIn(Strict):
    version: str = Field(min_length=1, max_length=32, pattern=r"^[A-Za-z0-9._-]+$")
    title: str = Field(min_length=1, max_length=200)
    body: str = Field(min_length=1, max_length=20_000)


class GuidelineOut(BaseModel):
    version: str
    title: str
    body: str


class TasksIn(Strict):
    dataset: str
    version: int
    recipe_hash: str = Field(min_length=64, max_length=64)
    guideline_version: str
    per_language: int = Field(default=30, ge=1, le=1000)
    seed: int = Field(default=0, ge=0)


class TasksOut(BaseModel):
    created: int
    existing: int
    by_language: dict[str, int]


class QueueItem(BaseModel):
    task_id: int
    guideline_version: str
    language: str
    source_text: str
    variant_text: str
    remaining: int


class AnnotationIn(Strict):
    annotator: Pseudonym
    semantic_label: Semantic
    safety_label: Safety
    note: str = Field(default="", max_length=2000)


class AdjudicationIn(Strict):
    adjudicator: Pseudonym
    semantic_label: Semantic
    safety_label: Safety
    rationale: str = Field(min_length=1, max_length=4000)


class Disagreement(BaseModel):
    task_id: int
    language: str
    source_text: str
    variant_text: str
    labels: list[dict[str, str]]


class PairKappa(BaseModel):
    annotators: tuple[str, str]
    items: int
    kappa: float | None


class AgreementOut(BaseModel):
    field: Literal["semantic_label", "safety_label"]
    tasks_annotated: int
    tasks_with_two_or_more: int
    annotations: int
    alpha_nominal: float | None
    pairwise_kappa: list[PairKappa]
    label_counts: dict[str, int]
    unsure_treated_as_missing: bool
    adjudicated: int
    note: str


def _get_annotator(session: object, pseudonym: str) -> Annotator:
    a = session.scalar(select(Annotator).where(Annotator.pseudonym == pseudonym))  # type: ignore[attr-defined]
    if a is None:
        raise ApiError(404, "annotator_not_found", f"No annotator '{pseudonym}'.")
    return a  # type: ignore[no-any-return]


@router.post(
    "/annotators",
    response_model=AnnotatorOut,
    status_code=201,
    responses={409: {"model": ErrorResponse}},
)
def create_annotator(body: AnnotatorIn, request: Request) -> AnnotatorOut:
    with request.app.state.sessionmaker() as session:
        session.add(Annotator(pseudonym=body.pseudonym, proficiency=dict(body.proficiency)))
        try:
            session.commit()
        except IntegrityError as exc:
            raise ApiError(409, "annotator_exists", f"'{body.pseudonym}' already exists.") from exc
        return AnnotatorOut(
            pseudonym=body.pseudonym, proficiency=dict(body.proficiency), annotations=0
        )


@router.get("/annotators", response_model=list[AnnotatorOut])
def list_annotators(request: Request) -> list[AnnotatorOut]:
    with request.app.state.sessionmaker() as session:
        rows = session.execute(
            select(Annotator, func.count(Annotation.id))
            .outerjoin(Annotation, Annotation.annotator_id == Annotator.id)
            .group_by(Annotator.id)
            .order_by(Annotator.pseudonym)
        ).all()
        return [
            AnnotatorOut(pseudonym=a.pseudonym, proficiency=a.proficiency, annotations=n)
            for a, n in rows
        ]


@router.post(
    "/guidelines",
    response_model=GuidelineOut,
    status_code=201,
    responses={409: {"model": ErrorResponse}},
)
def create_guideline(body: GuidelineIn, request: Request) -> GuidelineOut:
    with request.app.state.sessionmaker() as session:
        session.add(Guideline(**body.model_dump()))
        try:
            session.commit()
        except IntegrityError as exc:
            raise ApiError(
                409,
                "guideline_exists",
                f"Guideline version '{body.version}' exists; versions are immutable.",
            ) from exc
        return GuidelineOut(**body.model_dump())


@router.get("/guidelines", response_model=list[GuidelineOut])
def list_guidelines(request: Request) -> list[GuidelineOut]:
    with request.app.state.sessionmaker() as session:
        return [
            GuidelineOut(version=g.version, title=g.title, body=g.body)
            for g in session.scalars(select(Guideline).order_by(Guideline.created_at)).all()
        ]


@router.post(
    "/tasks", response_model=TasksOut, status_code=201, responses={404: {"model": ErrorResponse}}
)
def create_tasks(body: TasksIn, request: Request) -> TasksOut:
    """Stratified, seeded sample of variants (per source language) into annotation tasks."""
    with request.app.state.sessionmaker() as session:
        version = svc.get_version(session, body.dataset, body.version)
        guideline = session.scalar(
            select(Guideline).where(Guideline.version == body.guideline_version)
        )
        if guideline is None:
            raise ApiError(404, "guideline_not_found", f"No guideline '{body.guideline_version}'.")
        rows = session.execute(
            select(Variant.id, Source.language)
            .join(Source, Variant.source_id == Source.id)
            .where(Variant.version_id == version.id, Variant.recipe_hash == body.recipe_hash)
        ).all()
        by_lang: dict[str, list[int]] = defaultdict(list)
        for vid, lang in rows:
            by_lang[lang].append(vid)
        created = existing = 0
        counts: dict[str, int] = {}
        for lang, ids in sorted(by_lang.items()):
            ranked = sorted(
                ids, key=lambda v: hashlib.sha256(f"{body.seed}:{v}".encode()).hexdigest()
            )
            picked = ranked[: body.per_language]
            counts[lang] = len(picked)
            for vid in picked:
                exists = session.scalar(
                    select(AnnotationTask.id).where(
                        AnnotationTask.variant_id == vid,
                        AnnotationTask.guideline_id == guideline.id,
                    )
                )
                if exists:
                    existing += 1
                else:
                    session.add(AnnotationTask(variant_id=vid, guideline_id=guideline.id))
                    created += 1
        session.commit()
        return TasksOut(created=created, existing=existing, by_language=counts)


@router.get("/queue", response_model=QueueItem | None, responses={404: {"model": ErrorResponse}})
def next_item(
    request: Request, annotator: Annotated[str, Query(max_length=64)]
) -> QueueItem | None:
    """Next task for this annotator, in a per-annotator pseudo-random order (blinded)."""
    with request.app.state.sessionmaker() as session:
        a = _get_annotator(session, annotator)
        done = select(Annotation.task_id).where(Annotation.annotator_id == a.id)
        rows = session.execute(
            select(AnnotationTask, Guideline.version, Variant.text, Source.text, Source.language)
            .join(Guideline, AnnotationTask.guideline_id == Guideline.id)
            .join(Variant, AnnotationTask.variant_id == Variant.id)
            .join(Source, Variant.source_id == Source.id)
            .where(AnnotationTask.id.not_in(done))
        ).all()
        if not rows:
            return None
        rows = sorted(
            rows, key=lambda r: hashlib.sha256(f"{a.pseudonym}:{r[0].id}".encode()).hexdigest()
        )
        task, gv, vtext, stext, lang = rows[0]
        return QueueItem(
            task_id=task.id,
            guideline_version=gv,
            language=lang,
            source_text=stext,
            variant_text=vtext,
            remaining=len(rows),
        )


@router.post(
    "/tasks/{task_id}/annotations",
    status_code=201,
    response_model=dict[str, int],
    responses={404: {"model": ErrorResponse}, 409: {"model": ErrorResponse}},
)
def submit(task_id: int, body: AnnotationIn, request: Request) -> dict[str, int]:
    with request.app.state.sessionmaker() as session:
        a = _get_annotator(session, body.annotator)
        if session.get(AnnotationTask, task_id) is None:
            raise ApiError(404, "task_not_found", f"No task {task_id}.")
        session.add(
            Annotation(
                task_id=task_id,
                annotator_id=a.id,
                semantic_label=body.semantic_label,
                safety_label=body.safety_label,
                note=body.note,
            )
        )
        try:
            session.commit()
        except IntegrityError as exc:
            raise ApiError(
                409, "already_annotated", "This annotator already labelled this task."
            ) from exc
        return {"task_id": task_id}


@router.get("/disagreements", response_model=list[Disagreement])
def disagreements(
    request: Request, field: Literal["semantic_label", "safety_label"] = "semantic_label"
) -> list[Disagreement]:
    with request.app.state.sessionmaker() as session:
        adjudicated = set(session.scalars(select(Adjudication.task_id)).all())
        rows = session.execute(
            select(Annotation, Annotator.pseudonym, Variant.text, Source.text, Source.language)
            .join(Annotator, Annotation.annotator_id == Annotator.id)
            .join(AnnotationTask, Annotation.task_id == AnnotationTask.id)
            .join(Variant, AnnotationTask.variant_id == Variant.id)
            .join(Source, Variant.source_id == Source.id)
        ).all()
        grouped: dict[int, list[tuple[Annotation, str, str, str, str]]] = defaultdict(list)
        for row in rows:
            grouped[row[0].task_id].append(tuple(row))
        out = []
        for tid, items in sorted(grouped.items()):
            if tid in adjudicated or len(items) < 2:
                continue
            if len({getattr(i[0], field) for i in items}) > 1:
                out.append(
                    Disagreement(
                        task_id=tid,
                        language=items[0][4],
                        source_text=items[0][3],
                        variant_text=items[0][2],
                        labels=[
                            {
                                "annotator": i[1],
                                "semantic_label": i[0].semantic_label,
                                "safety_label": i[0].safety_label,
                            }
                            for i in items
                        ],
                    )
                )
        return out


@router.post(
    "/tasks/{task_id}/adjudication",
    status_code=201,
    response_model=dict[str, int],
    responses={404: {"model": ErrorResponse}, 409: {"model": ErrorResponse}},
)
def adjudicate(task_id: int, body: AdjudicationIn, request: Request) -> dict[str, int]:
    with request.app.state.sessionmaker() as session:
        if session.get(AnnotationTask, task_id) is None:
            raise ApiError(404, "task_not_found", f"No task {task_id}.")
        session.add(Adjudication(task_id=task_id, **body.model_dump()))
        try:
            session.commit()
        except IntegrityError as exc:
            raise ApiError(409, "already_adjudicated", "This task is already adjudicated.") from exc
        return {"task_id": task_id}


@router.get("/agreement", response_model=AgreementOut)
def agreement(
    request: Request, field: Literal["semantic_label", "safety_label"] = "semantic_label"
) -> AgreementOut:
    with request.app.state.sessionmaker() as session:
        rows = session.execute(
            select(Annotation.task_id, Annotator.pseudonym, getattr(Annotation, field)).join(
                Annotator, Annotation.annotator_id == Annotator.id
            )
        ).all()
        adjudicated = session.scalar(select(func.count(Adjudication.id))) or 0
    by_task: dict[int, dict[str, str]] = defaultdict(dict)
    counts: dict[str, int] = defaultdict(int)
    for tid, who, label in rows:
        by_task[tid][who] = label
        counts[label] += 1
    units = [[lab for lab in labs.values() if lab != "unsure"] for labs in by_task.values()]
    raters = sorted({who for labs in by_task.values() for who in labs})
    pairs = []
    for r1, r2 in combinations(raters, 2):
        items = [
            (labs[r1], labs[r2])
            for labs in by_task.values()
            if r1 in labs and r2 in labs and "unsure" not in (labs[r1], labs[r2])
        ]
        if items:
            pairs.append(PairKappa(annotators=(r1, r2), items=len(items), kappa=cohen_kappa(items)))
    return AgreementOut(
        field=field,
        tasks_annotated=len(by_task),
        tasks_with_two_or_more=sum(1 for labs in by_task.values() if len(labs) >= 2),
        annotations=len(rows),
        alpha_nominal=krippendorff_alpha_nominal(units),
        pairwise_kappa=pairs,
        label_counts=dict(sorted(counts.items())),
        unsure_treated_as_missing=True,
        adjudicated=adjudicated,
        note=(
            "Statistics are computed only from labels entered by annotators; null means undefined."
        ),
    )
