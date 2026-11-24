"""Render-artifact management and the text -> render -> OCR reading path."""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from emojilens_api.db.models import RenderArtifact
from emojilens_core.models import Capability, InferenceResult, ModelRegistry
from emojilens_core.multimodal import RenderConfig, render_chromium

OCR_MODEL = "tesseract-ocr"


def artifact_path(root: Path, art: RenderArtifact) -> Path:
    """Resolve an artifact path and refuse anything outside the artifacts root."""
    path = (root / art.rel_path).resolve()
    if root.resolve() not in path.parents:
        raise ValueError("artifact path escapes the artifacts directory")
    return path


def get_or_render(session: Session, root: Path, text: str, cfg: RenderConfig) -> RenderArtifact:
    text_hash = hashlib.sha256(text.encode()).hexdigest()
    art = session.scalar(
        select(RenderArtifact).where(
            RenderArtifact.text_sha256 == text_hash,
            RenderArtifact.config_hash == cfg.hash(),
            RenderArtifact.renderer == "chromium",
        )
    )
    if art is not None:
        path = artifact_path(root, art)
        if path.is_file() and hashlib.sha256(path.read_bytes()).hexdigest() == art.image_sha256:
            return art
        session.delete(art)
        session.flush()
    out = render_chromium(text, root / "renders", cfg)
    rel = str(Path(out.image_path).resolve().relative_to(root.resolve()))
    art = RenderArtifact(
        text_sha256=text_hash,
        config_hash=cfg.hash(),
        renderer=out.renderer,
        renderer_version=out.renderer_version,
        rel_path=rel,
        image_sha256=out.image_sha256,
        width=out.width,
        height=out.height,
        provenance=out.provenance,
    )
    session.add(art)
    session.flush()
    return art


def ocr_reading(
    session: Session,
    root: Path,
    registry: ModelRegistry,
    text: str,
    cfg: RenderConfig | None = None,
) -> tuple[RenderArtifact, InferenceResult]:
    art = get_or_render(session, root, text, cfg or RenderConfig())
    return art, registry.run(OCR_MODEL, Capability.OCR, str(artifact_path(root, art)))


def reading_extra(art: RenderArtifact, ocr: InferenceResult) -> dict[str, Any]:
    return {
        "artifact_id": art.id,
        "image_sha256": art.image_sha256,
        "ocr_text": ocr.normalized.get("text"),
        "ocr_mean_confidence": ocr.normalized.get("mean_confidence"),
        "ocr_error": ocr.error,
        "ocr_engine": ocr.metadata.library_versions,
    }
