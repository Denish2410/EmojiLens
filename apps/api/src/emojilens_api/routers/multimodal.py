from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Request
from fastapi.responses import FileResponse
from pydantic import BaseModel, ConfigDict, Field

from emojilens_api.db.models import RenderArtifact
from emojilens_api.errors import ApiError, ErrorResponse
from emojilens_api.services.multimodal import OCR_MODEL, artifact_path, get_or_render
from emojilens_core.models import Capability, ModelRegistry
from emojilens_core.multimodal import RenderConfig, compare

router = APIRouter(prefix="/multimodal", tags=["multimodal"])
VLM_MODEL = "vlm-smolvlm-256m"


class AnalyzeIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    text: str = Field(min_length=1, max_length=2000)
    width: int = Field(default=900, ge=200, le=2000)
    font_size: int = Field(default=32, ge=10, le=96)
    run_ocr: bool = True
    run_vlm: bool = True
    vlm_prompt: str = Field(default="Transcribe the text in this image exactly.", max_length=300)


class ReadingOut(BaseModel):
    model: str
    available: bool
    detail: str
    text: str | None = None
    confidence: float | None = None
    latency_ms: float | None = None
    error: dict[str, Any] | None = None
    comparison: dict[str, Any] | None = None
    metadata: dict[str, Any] | None = None


class AnalyzeOut(BaseModel):
    artifact_id: int
    image_url: str
    image_sha256: str
    width: int
    height: int
    renderer: str
    provenance: dict[str, Any]
    ocr: ReadingOut | None
    vlm: ReadingOut | None


def _reading(
    reg: ModelRegistry, key: str, cap: Capability, image: str, original: str, **params: Any
) -> ReadingOut:
    av = reg.availability(key)
    if not av.ok:
        return ReadingOut(model=key, available=False, detail=av.detail)
    r = reg.run(key, cap, image, **params)
    text = r.normalized.get("text")
    return ReadingOut(
        model=key,
        available=True,
        detail="ok" if r.error is None else "error",
        text=text,
        confidence=r.normalized.get("mean_confidence"),
        latency_ms=r.latency_ms,
        error=r.error,
        comparison=None if r.error or text is None else vars_cmp(compare(original, str(text))),
        metadata={
            "model_id": r.metadata.model_id,
            "revision": r.metadata.revision,
            "libraries": r.metadata.library_versions,
            "langs": r.normalized.get("langs"),
            "missing_langs": r.normalized.get("missing_langs"),
        },
    )


def vars_cmp(c: Any) -> dict[str, Any]:
    return {k: getattr(c, k) for k in c.__slots__}


@router.post(
    "/analyze",
    response_model=AnalyzeOut,
    responses={422: {"model": ErrorResponse}, 503: {"model": ErrorResponse}},
)
def analyze(body: AnalyzeIn, request: Request) -> AnalyzeOut:
    reg: ModelRegistry = request.app.state.registry
    root = request.app.state.artifacts_root
    cfg = RenderConfig(width=body.width, font_size=body.font_size)
    with request.app.state.sessionmaker() as session:
        try:
            art = get_or_render(session, root, body.text, cfg)
        except ImportError as exc:
            raise ApiError(
                503, "renderer_unavailable", "Playwright/Chromium is not installed."
            ) from exc
        except Exception as exc:
            raise ApiError(
                503, "renderer_failed", f"Rendering failed: {type(exc).__name__}"
            ) from exc
        session.commit()
        image = str(artifact_path(root, art))
        ocr = _reading(reg, OCR_MODEL, Capability.OCR, image, body.text) if body.run_ocr else None
        vlm = (
            _reading(
                reg, VLM_MODEL, Capability.VISION_INPUT, image, body.text, prompt=body.vlm_prompt
            )
            if body.run_vlm
            else None
        )
        return AnalyzeOut(
            artifact_id=art.id,
            image_url=f"/api/v1/multimodal/artifacts/{art.id}/image",
            image_sha256=art.image_sha256,
            width=art.width,
            height=art.height,
            renderer=art.renderer,
            provenance=art.provenance,
            ocr=ocr,
            vlm=vlm,
        )


@router.get(
    "/artifacts/{artifact_id}/image",
    response_class=FileResponse,
    responses={404: {"model": ErrorResponse}},
)
def image(artifact_id: int, request: Request) -> FileResponse:
    with request.app.state.sessionmaker() as session:
        art = session.get(RenderArtifact, artifact_id)
        if art is None:
            raise ApiError(404, "artifact_not_found", f"No artifact {artifact_id}.")
        try:
            path = artifact_path(request.app.state.artifacts_root, art)
        except ValueError as exc:
            raise ApiError(404, "artifact_not_found", "Artifact path is invalid.") from exc
        if not path.is_file():
            raise ApiError(404, "artifact_missing", "Artifact file is missing on disk.")
        return FileResponse(
            path,
            media_type="image/png",
            headers={"Cache-Control": "no-store", "X-Content-Type-Options": "nosniff"},
        )
