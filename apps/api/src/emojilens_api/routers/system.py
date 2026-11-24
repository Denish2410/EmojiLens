from __future__ import annotations

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
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
