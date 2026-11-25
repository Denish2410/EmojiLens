from __future__ import annotations

import importlib.util
import os
import platform
from importlib import metadata
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from sqlalchemy import text

from emojilens_api import __version__
from emojilens_api.db.migrate import current_revision, head_revision
from emojilens_api.schemas import HealthResponse, ReadinessCheck, ReadinessResponse

router = APIRouter(tags=["system"])


@router.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    """Liveness: the process is up. Does not touch the database."""
    return HealthResponse(status="ok", version=__version__)


@router.get(
    "/ready",
    response_model=ReadinessResponse,
    responses={503: {"model": ReadinessResponse}},
)
def ready(request: Request) -> JSONResponse:
    """Readiness: database reachable and schema at the latest migration."""
    engine = request.app.state.engine
    settings = request.app.state.settings
    checks: list[ReadinessCheck] = []
    try:
        with engine.connect() as conn:
            mode = conn.execute(text("PRAGMA journal_mode")).scalar()
        checks.append(ReadinessCheck(name="database", ok=True, detail=f"journal_mode={mode}"))
    except Exception as exc:  # pragma: no cover - exercised via failure test
        checks.append(ReadinessCheck(name="database", ok=False, detail=type(exc).__name__))
    else:
        current = current_revision(engine)
        head = head_revision(settings.database_url)
        checks.append(
            ReadinessCheck(
                name="migrations",
                ok=current == head,
                detail=f"current={current} head={head}",
            )
        )
    ok = all(c.ok for c in checks)
    body = ReadinessResponse(status="ready" if ok else "not_ready", checks=checks)
    return JSONResponse(status_code=200 if ok else 503, content=body.model_dump())


# ----------------------------------------------------------------------------- system info

OPTIONAL_PACKAGES = (
    ("torch", "neural model adapters"),
    ("transformers", "classifier, generative and VLM adapters"),
    ("sentence_transformers", "embedding adapter"),
    ("huggingface_hub", "pinned model downloads"),
    ("sklearn", "EmojiGuard logistic detector"),
    ("playwright", "sandboxed Chromium renderer"),
)


class DependencyInfo(BaseModel):
    name: str
    purpose: str
    installed: bool
    version: str | None


class ModelPinInfo(BaseModel):
    key: str
    model_id: str
    task: str
    revision: str | None
    availability: str
    test_double: bool


class SystemInfo(BaseModel):
    version: str
    python: str
    platform: str
    device: str
    device_reason: str
    database: dict[str, Any]
    models: list[ModelPinInfo]
    ocr_languages: list[str]
    renderer: dict[str, Any]
    artifacts: dict[str, int]
    dependencies: list[DependencyInfo]
    test_doubles_enabled: bool
    limits: dict[str, int]


def _pkg_version(name: str) -> tuple[bool, str | None]:
    if importlib.util.find_spec(name) is None:
        return False, None
    dist = {"sklearn": "scikit-learn", "sentence_transformers": "sentence-transformers"}
    try:
        return True, metadata.version(dist.get(name, name).replace("_", "-"))
    except metadata.PackageNotFoundError:
        return True, None


@router.get("/system/info", response_model=SystemInfo)
def system_info(request: Request) -> SystemInfo:
    """Runtime facts for the Settings page. Deliberately excludes filesystem paths, hostnames,
    environment variables and credentials: only versions, counts and booleans are returned."""
    app = request.app
    reg = app.state.registry
    settings = app.state.settings
    db: dict[str, Any] = {"ok": False}
    try:
        with app.state.engine.connect() as conn:
            mode = conn.execute(text("PRAGMA journal_mode")).scalar()
        current = current_revision(app.state.engine)
        head = head_revision(settings.database_url)
        db = {
            "ok": current == head,
            "journal_mode": mode,
            "migration": current,
            "head": head,
            "backend": settings.database_url.split(":", 1)[0],
        }
    except Exception as exc:  # reported, never raised
        db = {"ok": False, "error": type(exc).__name__}

    models = [
        ModelPinInfo(
            key=c.key,
            model_id=c.model_id,
            task=c.task,
            revision=c.revision,
            availability=reg.availability(c.key).status.value,
            test_double=c.test_double,
        )
        for c in reg.configs()
    ]
    ocr: list[str] = []
    try:
        adapter = reg.adapter("tesseract-ocr")
        ocr = sorted(adapter.installed_langs())
    except Exception:  # tesseract missing: an empty list, not an error
        ocr = []

    root: Path = app.state.artifacts_root
    files = [p for p in root.rglob("*") if p.is_file()] if root.is_dir() else []
    renderer_path = os.environ.get("EMOJILENS_CHROMIUM_PATH")
    return SystemInfo(
        version=__version__,
        python=platform.python_version(),
        platform=platform.system(),
        device=reg.device,
        device_reason=app.state.device_reason,
        database=db,
        models=models,
        ocr_languages=ocr,
        renderer={
            "engine": "chromium",
            "playwright_installed": importlib.util.find_spec("playwright") is not None,
            "custom_executable": bool(renderer_path),
            "javascript": False,
            "network": False,
        },
        artifacts={"files": len(files), "bytes": sum(p.stat().st_size for p in files)},
        dependencies=[
            DependencyInfo(name=n, purpose=why, installed=ok, version=v)
            for n, why in OPTIONAL_PACKAGES
            for ok, v in [_pkg_version(n)]
        ],
        test_doubles_enabled=bool(settings.enable_test_doubles),
        limits={
            "max_input_codepoints": settings.max_input_codepoints,
            "max_upload_bytes": settings.max_upload_bytes,
            "max_loaded_models": settings.max_loaded_models,
        },
    )
