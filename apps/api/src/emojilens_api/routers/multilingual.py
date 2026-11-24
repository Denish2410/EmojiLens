from __future__ import annotations

from fastapi import APIRouter, Request
from pydantic import BaseModel, Field

from emojilens_api.errors import ApiError, ErrorResponse
from emojilens_core.multilingual import VARIETIES, Variety, cldr_version, identify, meaning
from emojilens_core.unicode import segment_graphemes, validate_unicode
from emojilens_core.unicode.scripts import script_profile

router = APIRouter(prefix="/multilingual", tags=["multilingual"])


class VarietyOut(BaseModel):
    code: str
    name: str
    script: str
    cldr_locale: str | None
    notes: str


class AnalyzeRequest(BaseModel):
    text: str = Field(description="Input text, analysed exactly as given.")


class TokenOut(BaseModel):
    text: str
    cp_start: int
    cp_end: int
    tag: str
    candidates: list[str]


class MeaningOut(BaseModel):
    variety: str
    locale: str
    name: str
    keywords: list[str]
    fallback: bool


class EmojiOut(BaseModel):
    emoji: str
    cp_start: int
    cp_end: int
    meanings: list[MeaningOut]


class IdentificationOut(BaseModel):
    label: str | None
    confidence: float
    uncertain: bool
    reasons: list[str]
    scores: dict[str, float]
    code_mixed: bool
    cmi: float
    switch_points: int
    method: str


class MultilingualResponse(BaseModel):
    identification: IdentificationOut
    tokens: list[TokenOut]
    scripts: dict[str, int]
    dominant_script: str | None
    emoji: list[EmojiOut]
    cldr_version: str


@router.get("/varieties", response_model=list[VarietyOut])
def varieties() -> list[VarietyOut]:
    return [
        VarietyOut(
            code=v.code.value,
            name=v.name,
            script=v.script,
            cldr_locale=v.cldr_locale,
            notes=v.notes,
        )
        for v in VARIETIES.values()
    ]


@router.post(
    "/analyze",
    response_model=MultilingualResponse,
    responses={413: {"model": ErrorResponse}, 422: {"model": ErrorResponse}},
)
def analyze(body: AnalyzeRequest, request: Request) -> MultilingualResponse:
    limit: int = request.app.state.settings.max_input_codepoints
    if len(body.text) > limit:
        raise ApiError(413, "input_too_large", f"Input exceeds the limit of {limit} code points.")
    validate_unicode(body.text)
    result = identify(body.text)
    profile = script_profile(body.text)
    emoji_out: list[EmojiOut] = []
    for g in segment_graphemes(body.text):
        found = [(v, meaning(g.text, v)) for v in Variety]
        if any(m for _, m in found):
            emoji_out.append(
                EmojiOut(
                    emoji=g.text,
                    cp_start=g.span.cp_start,
                    cp_end=g.span.cp_end,
                    meanings=[
                        MeaningOut(
                            variety=v.value,
                            locale=m.locale,
                            name=m.name,
                            keywords=list(m.keywords),
                            fallback=m.fallback,
                        )
                        for v, m in found
                        if m is not None
                    ],
                )
            )
    return MultilingualResponse(
        identification=IdentificationOut(
            label=result.label.value if result.label else None,
            confidence=result.confidence,
            uncertain=result.uncertain,
            reasons=list(result.reasons),
            scores=result.scores,
            code_mixed=result.code_mixed,
            cmi=result.cmi,
            switch_points=result.switch_points,
            method=result.method,
        ),
        tokens=[
            TokenOut(
                text=t.text,
                cp_start=t.cp_start,
                cp_end=t.cp_end,
                tag=t.tag,
                candidates=list(t.candidates),
            )
            for t in result.tokens
        ],
        scripts=profile.counts,
        dominant_script=profile.dominant,
        emoji=emoji_out,
        cldr_version=cldr_version(),
    )
