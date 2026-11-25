from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Request
from pydantic import BaseModel, ConfigDict, Field

from emojilens_api.errors import ApiError, ErrorResponse
from emojilens_core.models import Capability, ModelError, ModelRegistry, resources

router = APIRouter(prefix="/models", tags=["models"])


class ModelOut(BaseModel):
    key: str
    model_id: str
    adapter: str
    capabilities: list[str]
    license: str
    task: str
    revision: str | None
    languages: list[str]
    approx_ram_gb: float
    approx_disk_gb: float
    notes: str
    test_double: bool
    availability: str
    availability_detail: str
    loaded: bool


class ModelsResponse(BaseModel):
    device: str
    device_reason: str
    resources: dict[str, Any]
    models: list[ModelOut]


class InferRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    capability: Capability
    text: str = Field(max_length=5000)


class InferResponse(BaseModel):
    model: str
    capability: str
    raw_output: Any
    normalized: dict[str, Any]
    latency_ms: float
    tokenization: dict[str, Any] | None
    metadata: dict[str, Any]
    error: dict[str, Any] | None


def _reg(request: Request) -> ModelRegistry:
    reg: ModelRegistry = request.app.state.registry
    return reg


@router.get("", response_model=ModelsResponse)
def list_models(request: Request) -> ModelsResponse:
    reg = _reg(request)
    res = resources()
    out = []
    for c in reg.configs():
        a = reg.adapter(c.key)
        av = a.availability()
        out.append(
            ModelOut(
                key=c.key,
                model_id=c.model_id,
                adapter=c.adapter,
                capabilities=[x.value for x in c.capabilities],
                license=c.license,
                task=c.task,
                revision=c.revision,
                languages=list(c.languages),
                approx_ram_gb=c.approx_ram_gb,
                approx_disk_gb=c.approx_disk_gb,
                notes=c.notes,
                test_double=c.test_double,
                availability=av.status.value,
                availability_detail=av.detail,
                loaded=a.loaded,
            )
        )
    return ModelsResponse(
        device=reg.device,
        device_reason=request.app.state.device_reason,
        resources={
            "available_ram_gb": res.available_ram_gb,
            "free_disk_gb": res.free_disk_gb,
            "cache_dir": _display_path(res.cache_dir),
        },
        models=out,
    )


def _display_path(path: str) -> str:
    """Show the cache location relative to the home directory, never the absolute path."""
    home = str(Path.home())
    if path == home or path.startswith(home + os.sep):
        return "~" + path[len(home) :]
    return "(configured location)"


@router.post(
    "/{key}/infer",
    response_model=InferResponse,
    responses={
        404: {"model": ErrorResponse},
        409: {"model": ErrorResponse},
        422: {"model": ErrorResponse},
    },
)
def infer(key: str, body: InferRequest, request: Request) -> InferResponse:
    """Single text inference for the Model Arena. Refuses unavailable models with a reason."""
    reg = _reg(request)
    try:
        cfg = reg.config(key)
    except ModelError as exc:
        raise ApiError(404, "model_not_found", exc.message) from exc
    if body.capability in (Capability.OCR, Capability.VISION_INPUT):
        raise ApiError(
            422,
            "capability_unsupported",
            "Image capabilities run through the Multimodal Laboratory.",
        )
    if body.capability not in cfg.capabilities:
        raise ApiError(
            422, "capability_unsupported", f"{key} does not support {body.capability.value}."
        )
    av = reg.availability(key)
    if not av.ok:
        raise ApiError(
            409,
            av.status.value,
            f"{key} is not available: {av.detail}",
            {"availability": av.status.value},
        )
    r = reg.run(key, body.capability, body.text)
    tok = r.tokenization
    return InferResponse(
        model=key,
        capability=r.capability.value,
        raw_output=r.raw_output,
        normalized=r.normalized,
        latency_ms=r.latency_ms,
        tokenization=None
        if tok is None
        else {
            "tokens": tok.tokens,
            "ids": tok.ids,
            "offsets": tok.offsets,
            "unknown": tok.unknown_tokens,
        },
        metadata={
            "model_id": r.metadata.model_id,
            "revision": r.metadata.revision,
            "tokenizer_revision": r.metadata.tokenizer_revision,
            "adapter_version": r.metadata.adapter_version,
            "device": r.metadata.device,
            "dtype": r.metadata.dtype,
            "library_versions": r.metadata.library_versions,
            "test_double": r.metadata.test_double,
        },
        error=r.error,
    )
