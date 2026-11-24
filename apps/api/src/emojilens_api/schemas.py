"""Typed API contracts (v1)."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from emojilens_core.unicode import UnicodeAnalysis
from emojilens_core.unicode.offsets import Span


class Model(BaseModel):
    model_config = ConfigDict(frozen=True)


class SpanOut(Model):
    cp_start: int
    cp_end: int
    utf8_start: int
    utf8_end: int
    utf16_start: int
    utf16_end: int

    @classmethod
    def of(cls, s: Span) -> SpanOut:
        return cls(
            cp_start=s.cp_start,
            cp_end=s.cp_end,
            utf8_start=s.utf8_start,
            utf8_end=s.utf8_end,
            utf16_start=s.utf16_start,
            utf16_end=s.utf16_end,
        )


class CodepointOut(Model):
    index: int
    char: str
    codepoint: str
    name: str
    category: str
    bidi_class: str
    combining_class: int
    utf8_hex: str
    span: SpanOut
    kinds: list[str]
    invisible: bool


class GraphemeOut(Model):
    index: int
    text: str
    span: SpanOut
    codepoint_count: int


class LengthsOut(Model):
    codepoints: int
    graphemes: int
    utf8_bytes: int
    utf16_units: int


class NormalizationOut(Model):
    is_nfc: bool
    is_nfd: bool
    is_nfkc: bool
    is_nfkd: bool


class EngineOut(Model):
    engine_version: str
    ruleset_version: str
    unicodedata_version: str
    regex_version: str
    emoji_version: str


EvidenceCategory = Literal[
    "legitimate_structure",
    "informational",
    "anomalous",
    "suspicious",
    "concealed_payload_decoded",
]


class EvidenceOut(Model):
    id: str
    rule: str
    category: EvidenceCategory
    message: str
    span: SpanOut
    details: dict[str, Any]


class ScriptsOut(Model):
    counts: dict[str, int]
    dominant: str | None
    is_mixed: bool


class ViewSegmentOut(Model):
    original: SpanOut
    view: SpanOut
    text: str


ViewName = Literal["original", "nfc", "nfkc", "sanitized", "demojized", "decoded"]


class DerivedViewOut(Model):
    name: ViewName
    description: str
    text: str
    changed: bool
    segments: list[ViewSegmentOut]


class UnicodeAnalyzeRequest(Model):
    text: str = Field(description="Input text. Preserved exactly; never trimmed or normalized.")


class UnicodeAnalyzeResponse(Model):
    original: str
    sha256: str
    lengths: LengthsOut
    normalization: NormalizationOut
    graphemes: list[GraphemeOut]
    codepoints: list[CodepointOut]
    invisible_count: int
    scripts: ScriptsOut
    evidence: list[EvidenceOut]
    views: list[DerivedViewOut]
    engine: EngineOut

    @classmethod
    def of(cls, a: UnicodeAnalysis) -> UnicodeAnalyzeResponse:
        return cls(
            original=a.original,
            sha256=a.sha256,
            lengths=LengthsOut(**vars_slots(a.lengths)),
            normalization=NormalizationOut(**vars_slots(a.normalization)),
            graphemes=[
                GraphemeOut(
                    index=g.index,
                    text=g.text,
                    span=SpanOut.of(g.span),
                    codepoint_count=g.codepoint_count,
                )
                for g in a.graphemes
            ],
            codepoints=[
                CodepointOut(
                    index=c.index,
                    char=c.char,
                    codepoint=c.codepoint,
                    name=c.name,
                    category=c.category,
                    bidi_class=c.bidi_class,
                    combining_class=c.combining_class,
                    utf8_hex=c.utf8_hex,
                    span=SpanOut.of(c.span),
                    kinds=[str(k) for k in c.kinds],
                    invisible=c.invisible,
                )
                for c in a.codepoints
            ],
            invisible_count=a.invisible_count,
            scripts=ScriptsOut(**vars_slots(a.scripts)),
            evidence=[
                EvidenceOut(
                    id=e.id,
                    rule=e.rule,
                    category=e.category.value,
                    message=e.message,
                    span=SpanOut.of(e.span),
                    details=dict(e.details),
                )
                for e in a.evidence
            ],
            views=[
                DerivedViewOut(
                    name=v.name,
                    description=v.description,
                    text=v.text,
                    changed=v.changed,
                    segments=[
                        ViewSegmentOut(
                            original=SpanOut.of(seg.original),
                            view=SpanOut.of(seg.view),
                            text=seg.text,
                        )
                        for seg in v.segments
                    ],
                )
                for v in a.views
            ],
            engine=EngineOut(**vars_slots(a.engine)),
        )


def vars_slots(obj: object) -> dict[str, object]:
    return {name: getattr(obj, name) for name in obj.__slots__}  # type: ignore[attr-defined]


class HealthResponse(Model):
    status: Literal["ok"]
    version: str


class ReadinessCheck(Model):
    name: str
    ok: bool
    detail: str


class ReadinessResponse(Model):
    status: Literal["ready", "not_ready"]
    checks: list[ReadinessCheck]
