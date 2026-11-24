"""Top-level Unicode analysis entry point."""

from __future__ import annotations

import unicodedata
from dataclasses import dataclass

import emoji
import regex

from emojilens_core.unicode.codepoints import CodepointInfo, inspect_codepoints
from emojilens_core.unicode.evidence import RULESET_VERSION, Evidence, classify
from emojilens_core.unicode.graphemes import Grapheme, segment_graphemes
from emojilens_core.unicode.integrity import original_sha256
from emojilens_core.unicode.offsets import OffsetTable
from emojilens_core.unicode.scripts import ScriptProfile, script_profile
from emojilens_core.unicode.views import DerivedView, build_views

ENGINE_VERSION = "0.2.0"


@dataclass(frozen=True, slots=True)
class EngineInfo:
    engine_version: str
    ruleset_version: str
    unicodedata_version: str
    regex_version: str
    emoji_version: str


def engine_info() -> EngineInfo:
    return EngineInfo(
        engine_version=ENGINE_VERSION,
        ruleset_version=RULESET_VERSION,
        unicodedata_version=unicodedata.unidata_version,
        regex_version=str(getattr(regex, "__version__", "unknown")),
        emoji_version=str(getattr(emoji, "__version__", "unknown")),
    )


@dataclass(frozen=True, slots=True)
class Lengths:
    codepoints: int
    graphemes: int
    utf8_bytes: int
    utf16_units: int


@dataclass(frozen=True, slots=True)
class NormalizationStatus:
    is_nfc: bool
    is_nfd: bool
    is_nfkc: bool
    is_nfkd: bool


@dataclass(frozen=True, slots=True)
class UnicodeAnalysis:
    original: str
    sha256: str
    lengths: Lengths
    normalization: NormalizationStatus
    graphemes: list[Grapheme]
    codepoints: list[CodepointInfo]
    invisible_count: int
    scripts: ScriptProfile
    evidence: list[Evidence]
    views: list[DerivedView]
    engine: EngineInfo


def analyze(text: str) -> UnicodeAnalysis:
    """Analyze ``text`` without modifying it.

    Raises :class:`~emojilens_core.unicode.errors.InvalidUnicodeError` for
    input containing surrogate code points.
    """
    digest = original_sha256(text)  # validates first
    table = OffsetTable.build(text)
    graphemes = segment_graphemes(text, table)
    codepoints = inspect_codepoints(text, table)
    evidence = classify(text, graphemes, table)
    views = build_views(text, graphemes, codepoints, evidence, table)
    return UnicodeAnalysis(
        original=text,
        sha256=digest,
        lengths=Lengths(
            codepoints=len(text),
            graphemes=len(graphemes),
            utf8_bytes=table.utf8[-1],
            utf16_units=table.utf16[-1],
        ),
        normalization=NormalizationStatus(
            is_nfc=unicodedata.is_normalized("NFC", text),
            is_nfd=unicodedata.is_normalized("NFD", text),
            is_nfkc=unicodedata.is_normalized("NFKC", text),
            is_nfkd=unicodedata.is_normalized("NFKD", text),
        ),
        graphemes=graphemes,
        codepoints=codepoints,
        invisible_count=sum(1 for c in codepoints if c.invisible),
        scripts=script_profile(text),
        evidence=evidence,
        views=views,
        engine=engine_info(),
    )
