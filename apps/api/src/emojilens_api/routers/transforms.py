from __future__ import annotations

import hashlib
import json
from typing import Annotated, Any

from fastapi import APIRouter, Query, Request
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import case, func, select

from emojilens_api.db.models import Source, Variant
from emojilens_api.errors import ApiError, ErrorResponse
from emojilens_api.services import datasets as svc
from emojilens_core.datasets import text_sha256
from emojilens_core.multilingual import Variety
from emojilens_core.transforms import REGISTRY, ChainResult, ChainStep, TransformError, run_chain

router = APIRouter(tags=["transforms"])


class ParamOut(BaseModel):
    name: str
    kind: str
    default: Any
    description: str
    choices: list[str]
    minimum: float | None
    maximum: float | None


class SpecOut(BaseModel):
    id: str
    version: str
    family: str
    description: str
    varieties: list[str]
    params: list[ParamOut]
    seeded: bool
    reversible: bool


class StepIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    transform_id: str = Field(max_length=64)
    params: dict[str, Any] = Field(default_factory=dict)


class ApplyRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    text: str
    variety: Variety
    seed: int = Field(default=0, ge=0, le=2**31 - 1)
    chain: list[StepIn] = Field(min_length=1, max_length=8)


class StepOut(BaseModel):
    transform_id: str
    version: str
    family: str
    params: dict[str, Any]
    seed: int
    output: str
    edits: int
    valid: bool
    checks: dict[str, bool | None]
    notes: list[str]
    provenance: dict[str, Any]
    pieces: list[tuple[int, int, str]]


class ApplyResponse(BaseModel):
    original: str
    original_sha256: str
    output: str
    output_sha256: str
    variety: str
    seed: int
    chain_hash: str
    valid: bool
    steps: list[StepOut]
    pieces: list[tuple[int, int, str]]


def _steps(result: ChainResult) -> list[StepOut]:
    return [
        StepOut(
            transform_id=s.transform_id,
            version=s.version,
            family=s.family,
            params=s.params,
            seed=s.seed,
            output=s.output,
            edits=s.edits,
            valid=s.validation.valid,
            checks=s.validation.checks,
            notes=list(s.validation.notes),
            provenance=s.provenance,
            pieces=s.pieces,
        )
        for s in result.steps
    ]


def _run(text: str, variety: Variety, chain: list[StepIn], seed: int) -> ChainResult:
    try:
        return run_chain(
            REGISTRY, text, variety, [ChainStep(s.transform_id, s.params) for s in chain], seed
        )
    except TransformError as exc:
        raise ApiError(422, "transform_error", str(exc)) from exc


@router.get("/transforms", response_model=list[SpecOut])
def list_transforms() -> list[SpecOut]:
    return [
        SpecOut(
            id=t.spec.id,
            version=t.spec.version,
            family=t.spec.family,
            description=t.spec.description,
            varieties=[v.value for v in t.spec.varieties],
            params=[
                ParamOut(
                    name=p.name,
                    kind=p.kind,
                    default=p.default,
                    description=p.description,
                    choices=list(p.choices),
                    minimum=p.minimum,
                    maximum=p.maximum,
                )
                for p in t.spec.params
            ],
            seeded=t.spec.seeded,
            reversible=t.spec.reversible,
        )
        for t in REGISTRY.values()
    ]


@router.post(
    "/transforms/apply",
    response_model=ApplyResponse,
    responses={413: {"model": ErrorResponse}, 422: {"model": ErrorResponse}},
)
def apply(body: ApplyRequest, request: Request) -> ApplyResponse:
    limit: int = request.app.state.settings.max_input_codepoints
    if len(body.text) > limit:
        raise ApiError(413, "input_too_large", f"Input exceeds the limit of {limit} code points.")
    r = _run(body.text, body.variety, body.chain, body.seed)
    return ApplyResponse(
        original=r.original,
        original_sha256=text_sha256(r.original),
        output=r.output,
        output_sha256=text_sha256(r.output),
        variety=r.variety.value,
        seed=r.seed,
        chain_hash=r.chain_hash,
        valid=r.valid,
        steps=_steps(r),
        pieces=r.pieces,
    )


# --------------------------------------------------------------------------- dataset variants


class GenerateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    seed: int = Field(default=0, ge=0, le=2**31 - 1)
    chain: list[StepIn] = Field(min_length=1, max_length=8)


class GenerateResponse(BaseModel):
    recipe_hash: str
    created: int
    skipped_existing: int
    invalid: int


class VariantOut(BaseModel):
    source_id: str
    source_text: str
    text: str
    text_sha256: str
    language: str
    split: str
    families: str
    recipe_hash: str
    chain_hash: str
    valid: bool
    pieces: list[Any]


class VariantPage(BaseModel):
    total: int
    page: int
    page_size: int
    items: list[VariantOut]


def recipe_of(chain: list[StepIn], seed: int) -> tuple[str, dict[str, Any]]:
    steps = []
    for s in chain:
        t = REGISTRY.get(s.transform_id)
        if t is None:
            raise ApiError(422, "transform_error", f"Unknown transformation '{s.transform_id}'.")
        try:
            params = t.resolve_params(s.params)
        except TransformError as exc:
            raise ApiError(422, "transform_error", str(exc)) from exc
        steps.append({"id": t.spec.id, "version": t.spec.version, "params": params})
    recipe = {"seed": seed, "steps": steps}
    canon = json.dumps(recipe, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(canon.encode()).hexdigest(), recipe


@router.post(
    "/datasets/{slug}/versions/{number}/variants",
    response_model=GenerateResponse,
    status_code=201,
    responses={409: {"model": ErrorResponse}, 422: {"model": ErrorResponse}},
)
def generate(slug: str, number: int, body: GenerateRequest, request: Request) -> GenerateResponse:
    """Apply a transformation recipe to every source of a *frozen* version.

    Splits are assigned to source groups at freeze time, before any transformation, so each
    variant inherits its source's split and variants can never leak across splits.
    """
    recipe_hash, recipe = recipe_of(body.chain, body.seed)
    with request.app.state.sessionmaker() as session:
        version = svc.get_version(session, slug, number)
        if version.frozen_at is None:
            raise ApiError(
                409,
                "version_not_frozen",
                "Freeze the version (assign splits) before generating variants.",
            )
        existing = set(
            session.scalars(
                select(Variant.source_id).where(
                    Variant.version_id == version.id, Variant.recipe_hash == recipe_hash
                )
            ).all()
        )
        created = invalid = 0
        families = "+".join(s["id"] for s in recipe["steps"])
        for src in session.scalars(select(Source).where(Source.version_id == version.id)).all():
            if src.id in existing:
                continue
            r = _run(src.text, Variety(src.language), body.chain, body.seed)
            invalid += 0 if r.valid else 1
            assert src.split is not None
            session.add(
                Variant(
                    source_id=src.id,
                    version_id=version.id,
                    recipe_hash=recipe_hash,
                    chain_hash=r.chain_hash,
                    recipe=recipe,
                    families=families,
                    text=r.output,
                    text_sha256=text_sha256(r.output),
                    pieces=[list(p) for p in r.pieces],
                    steps=[s.model_dump() for s in _steps(r)],
                    valid=r.valid,
                    split=src.split,
                )
            )
            created += 1
        session.commit()
        return GenerateResponse(
            recipe_hash=recipe_hash,
            created=created,
            skipped_existing=len(existing),
            invalid=invalid,
        )


@router.get("/datasets/{slug}/versions/{number}/variants", response_model=VariantPage)
def list_variants(
    slug: str,
    number: int,
    request: Request,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=200)] = 50,
    recipe_hash: Annotated[str | None, Query(max_length=64)] = None,
    split: str | None = None,
) -> VariantPage:
    with request.app.state.sessionmaker() as session:
        version = svc.get_version(session, slug, number)
        stmt = (
            select(Variant, Source)
            .join(Source, Variant.source_id == Source.id)
            .where(Variant.version_id == version.id)
        )
        if recipe_hash:
            stmt = stmt.where(Variant.recipe_hash == recipe_hash)
        if split:
            stmt = stmt.where(Variant.split == split)
        total = session.scalar(select(func.count()).select_from(stmt.subquery())) or 0
        rows = session.execute(
            stmt.order_by(Source.external_id, Variant.id)
            .offset((page - 1) * page_size)
            .limit(page_size)
        ).all()
        return VariantPage(
            total=total,
            page=page,
            page_size=page_size,
            items=[
                VariantOut(
                    source_id=s.external_id,
                    source_text=s.text,
                    text=v.text,
                    text_sha256=v.text_sha256,
                    language=s.language,
                    split=v.split,
                    families=v.families,
                    recipe_hash=v.recipe_hash,
                    chain_hash=v.chain_hash,
                    valid=v.valid,
                    pieces=v.pieces,
                )
                for v, s in rows
            ],
        )


class RecipeOut(BaseModel):
    recipe_hash: str
    families: str
    seed: int
    variants: int
    invalid: int


@router.get("/datasets/{slug}/versions/{number}/recipes", response_model=list[RecipeOut])
def list_recipes(slug: str, number: int, request: Request) -> list[RecipeOut]:
    """Distinct transformation recipes applied to a version, with variant counts."""
    with request.app.state.sessionmaker() as session:
        version = svc.get_version(session, slug, number)
        rows = session.execute(
            select(
                Variant.recipe_hash,
                Variant.families,
                func.count(),
                func.sum(case((Variant.valid.is_(False), 1), else_=0)),
                func.min(Variant.id),
            )
            .where(Variant.version_id == version.id)
            .group_by(Variant.recipe_hash, Variant.families)
            .order_by(func.min(Variant.id))
        ).all()
        out = []
        for recipe_hash, families, n, invalid, first_id in rows:
            first = session.get(Variant, first_id)
            seed = int(first.recipe.get("seed", 0)) if first else 0
            out.append(
                RecipeOut(
                    recipe_hash=recipe_hash,
                    families=families,
                    seed=seed,
                    variants=n,
                    invalid=int(invalid or 0),
                )
            )
        return out
