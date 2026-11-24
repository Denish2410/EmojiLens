"""Unicode forensics engine."""

from emojilens_core.unicode.analysis import ENGINE_VERSION, UnicodeAnalysis, analyze, engine_info
from emojilens_core.unicode.codepoints import CodepointInfo, CodepointKind, inspect_codepoints
from emojilens_core.unicode.errors import InvalidUnicodeError
from emojilens_core.unicode.graphemes import Grapheme, segment_graphemes
from emojilens_core.unicode.integrity import original_sha256, validate_unicode
from emojilens_core.unicode.offsets import OffsetTable, Span

__all__ = [
    "ENGINE_VERSION",
    "CodepointInfo",
    "CodepointKind",
    "Grapheme",
    "InvalidUnicodeError",
    "OffsetTable",
    "Span",
    "UnicodeAnalysis",
    "analyze",
    "engine_info",
    "inspect_codepoints",
    "original_sha256",
    "segment_graphemes",
    "validate_unicode",
]
