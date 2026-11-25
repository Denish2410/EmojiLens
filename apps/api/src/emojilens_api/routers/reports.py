"""Research report endpoints. Numbers come only from runs that pass every eligibility rule."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Request
from fastapi.responses import PlainTextResponse

from emojilens_api.services.reporting import build_report, render_markdown

router = APIRouter(prefix="/reports", tags=["reports"])


@router.get("/research")
def research_report(request: Request) -> dict[str, Any]:
    with request.app.state.sessionmaker() as session:
        return build_report(session, request.app.state.registry)


@router.get("/research.md", response_class=PlainTextResponse)
def research_report_markdown(request: Request) -> PlainTextResponse:
    with request.app.state.sessionmaker() as session:
        report = build_report(session, request.app.state.registry)
    return PlainTextResponse(render_markdown(report), media_type="text/markdown; charset=utf-8")
