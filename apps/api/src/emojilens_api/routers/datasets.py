from __future__ import annotations

from collections.abc import Iterator
from datetime import datetime
from typing import Annotated, Any, Literal

from fastapi import APIRouter, Depends, Query, Request
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from emojilens_api.db.models import Dataset, DatasetVersion
from emojilens_api.errors import ApiError, ErrorResponse
from emojilens_api.services import datasets as svc

router = APIRouter(prefix="/datasets", tags=["datasets"])

Kind = Literal["evaluation", "synthetic_fixture"]
SplitName = Literal["train", "validation", "test"]


def session_dep(request: Request) -> Iterator[Session]:
    with request.app.state.sessionmaker() as session:
        yield session


SessionDep = Annotated[Session, Depends(session_dep)]


class Out(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class DatasetCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    slug: str = Field(min_length=2, max_length=64, pattern=r"^[a-z0-9][a-z0-9-]*$")
    name: str = Field(min_length=1, max_length=200)
    description: str = Field(default="", max_length=4000)
    kind: Kind
    license: str = Field(min_length=1, max_length=128)


class VersionOut(Out):
    number: int
    content_sha256: str
    record_count: int
    schema_version: int
    split_seed: int | None
    split_ratios: list[float] | None
    split_method: str | None
    frozen_at: datetime | None
    created_at: datetime


class DatasetOut(Out):
    slug: str
    name: str
    description: str
    kind: Kind
    license: str
    created_at: datetime
    versions: list[VersionOut]


class LeakageIssueOut(BaseModel):
    kind: str
    ids: list[str]
    splits: list[str]


class VersionDetail(BaseModel):
    dataset: str
    version: VersionOut
    stats: dict[str, dict[str, int]]
    language_agreement: dict[str, int]
    leakage: list[LeakageIssueOut]
    leakage_checked: bool


class ImportResponse(BaseModel):
    dataset: str
    version: VersionOut
    duplicates: list[dict[str, Any]]


class FreezeRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    seed: int = Field(ge=0, le=2**31 - 1)
    ratios: tuple[float, float, float] = (0.7, 0.15, 0.15)


class SourceOut(Out):
    external_id: str
    source_group: str
    text: str
    text_sha256: str
    language: str
    detected_language: str | None
    detected_confidence: float | None
    safety_label: str
    control: str | None
    origin: str
    license: str
    meta: dict[str, Any]
    split: str | None


class SourcePage(BaseModel):
    total: int
    page: int
    page_size: int
    items: list[SourceOut]


@router.get("", response_model=list[DatasetOut])
def list_datasets(session: SessionDep) -> list[Dataset]:
    return list(session.scalars(select(Dataset).order_by(Dataset.created_at.desc())).all())


@router.post(
    "", response_model=DatasetOut, status_code=201, responses={409: {"model": ErrorResponse}}
)
def create_dataset(body: DatasetCreate, session: SessionDep) -> Dataset:
    ds = Dataset(**body.model_dump())
    session.add(ds)
    try:
        session.commit()
    except IntegrityError as exc:
        session.rollback()
        raise ApiError(409, "dataset_exists", f"Slug '{body.slug}' is already used.") from exc
    session.refresh(ds)
    return ds


@router.get("/{slug}", response_model=DatasetOut, responses={404: {"model": ErrorResponse}})
def get_dataset(slug: str, session: SessionDep) -> Dataset:
    return svc.get_dataset(session, slug)


@router.post(
    "/{slug}/versions",
    response_model=ImportResponse,
    status_code=201,
    responses={413: {"model": ErrorResponse}, 422: {"model": ErrorResponse}},
    openapi_extra={
        "requestBody": {
            "required": True,
            "content": {"application/x-ndjson": {"schema": {"type": "string"}}},
        }
    },
)
async def import_version(slug: str, request: Request) -> ImportResponse:
    """Upload JSONL (schema v1) as the request body. Creates a new immutable version."""
    limit: int = request.app.state.settings.max_upload_bytes
    declared = request.headers.get("content-length")
    if declared and declared.isdigit() and int(declared) > limit:
        raise ApiError(413, "upload_too_large", f"Upload exceeds {limit} bytes.", {"limit": limit})
    chunks: list[bytes] = []
    size = 0
    async for chunk in request.stream():
        size += len(chunk)
        if size > limit:
            raise ApiError(
                413, "upload_too_large", f"Upload exceeds {limit} bytes.", {"limit": limit}
            )
        chunks.append(chunk)
    data = b"".join(chunks)
    with request.app.state.sessionmaker() as session:
        ds = svc.get_dataset(session, slug)
        outcome = svc.import_version(session, ds, data)
        session.commit()
        session.refresh(outcome.version)
        return ImportResponse(
            dataset=slug,
            version=VersionOut.model_validate(outcome.version),
            duplicates=outcome.duplicates,
        )


def _detail(session: Session, slug: str, version: DatasetVersion) -> VersionDetail:
    frozen = version.frozen_at is not None
    issues = svc.leakage(session, version) if frozen else []
    return VersionDetail(
        dataset=slug,
        version=VersionOut.model_validate(version),
        stats=svc.stats(session, version),
        language_agreement=svc.language_agreement(session, version),
        leakage=[
            LeakageIssueOut(kind=i.kind, ids=list(i.ids), splits=list(i.splits)) for i in issues
        ],
        leakage_checked=frozen,
    )


@router.get(
    "/{slug}/versions/{number}",
    response_model=VersionDetail,
    responses={404: {"model": ErrorResponse}},
)
def version_detail(slug: str, number: int, session: SessionDep) -> VersionDetail:
    return _detail(session, slug, svc.get_version(session, slug, number))


@router.post(
    "/{slug}/versions/{number}/freeze",
    response_model=VersionDetail,
    responses={409: {"model": ErrorResponse}, 422: {"model": ErrorResponse}},
)
def freeze(slug: str, number: int, body: FreezeRequest, session: SessionDep) -> VersionDetail:
    version = svc.get_version(session, slug, number)
    svc.freeze_version(session, version, body.seed, body.ratios)
    session.commit()
    return _detail(session, slug, version)


@router.get("/{slug}/versions/{number}/sources", response_model=SourcePage)
def sources(
    slug: str,
    number: int,
    session: SessionDep,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=200)] = 50,
    language: str | None = None,
    split: SplitName | None = None,
    safety_label: Literal["safe", "unsafe", "unknown"] | None = None,
    control: str | None = None,
    q: Annotated[str | None, Query(max_length=200)] = None,
) -> SourcePage:
    version = svc.get_version(session, slug, number)
    total, rows = svc.list_sources(
        session,
        version,
        page=page,
        page_size=page_size,
        language=language,
        split=split,
        safety_label=safety_label,
        control=control,
        q=q,
    )
    return SourcePage(
        total=total,
        page=page,
        page_size=page_size,
        items=[SourceOut.model_validate(r) for r in rows],
    )
