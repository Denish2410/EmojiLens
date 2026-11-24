from __future__ import annotations

from fastapi import APIRouter, Request

from emojilens_api.errors import ApiError, ErrorResponse
from emojilens_api.schemas import UnicodeAnalyzeRequest, UnicodeAnalyzeResponse
from emojilens_core.unicode import analyze

router = APIRouter(prefix="/unicode", tags=["unicode"])


@router.post(
    "/analyze",
    response_model=UnicodeAnalyzeResponse,
    responses={413: {"model": ErrorResponse}, 422: {"model": ErrorResponse}},
)
def analyze_text(body: UnicodeAnalyzeRequest, request: Request) -> UnicodeAnalyzeResponse:
    """Inspect code points, graphemes and offsets. The input is never modified."""
    limit: int = request.app.state.settings.max_input_codepoints
    if len(body.text) > limit:
        raise ApiError(
            413,
            "input_too_large",
            f"Input exceeds the limit of {limit} code points.",
            {"limit": limit, "received": len(body.text)},
        )
    return UnicodeAnalyzeResponse.of(analyze(body.text))
