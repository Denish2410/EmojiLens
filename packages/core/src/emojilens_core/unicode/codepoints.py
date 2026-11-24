"""Per-code-point inspection.

This module describes *what* each code point is. It deliberately does not judge
whether a code point is malicious: invisible characters such as ZWJ are
structural in emoji sequences and in Devanagari/Gujarati text. Contextual
evidence classification is a separate layer (Week 2, ``evidence`` module).
"""

from __future__ import annotations

import unicodedata
from dataclasses import dataclass
from enum import StrEnum

from emojilens_core.unicode.offsets import OffsetTable, Span


class CodepointKind(StrEnum):
    """Structural markers for code points that are invisible or render-altering."""

    ZERO_WIDTH = "zero_width"
    JOINER = "joiner"
    VARIATION_SELECTOR = "variation_selector"
    TAG = "tag"
    BIDI_CONTROL = "bidi_control"
    FILLER = "filler"
    FORMAT = "format"
    CONTROL = "control"
    EMOJI_MODIFIER = "emoji_modifier"
    REGIONAL_INDICATOR = "regional_indicator"
    COMBINING_ENCLOSING_KEYCAP = "combining_enclosing_keycap"


_ZERO_WIDTH = {0x200B, 0x2060, 0xFEFF, 0x2061, 0x2062, 0x2063, 0x2064, 0x180E, 0x00AD}
_JOINERS = {0x200C, 0x200D}
_BIDI = {0x061C, 0x200E, 0x200F, *range(0x202A, 0x202F), *range(0x2066, 0x206A)}
_FILLERS = {0x115F, 0x1160, 0x3164, 0xFFA0}


def classify_kinds(cp: int) -> tuple[CodepointKind, ...]:
    kinds: list[CodepointKind] = []
    category = unicodedata.category(chr(cp))
    if cp in _ZERO_WIDTH:
        kinds.append(CodepointKind.ZERO_WIDTH)
    if cp in _JOINERS:
        kinds.append(CodepointKind.JOINER)
    if 0xFE00 <= cp <= 0xFE0F or 0xE0100 <= cp <= 0xE01EF:
        kinds.append(CodepointKind.VARIATION_SELECTOR)
    if 0xE0000 <= cp <= 0xE007F:
        kinds.append(CodepointKind.TAG)
    if cp in _BIDI:
        kinds.append(CodepointKind.BIDI_CONTROL)
    if cp in _FILLERS:
        kinds.append(CodepointKind.FILLER)
    if 0x1F3FB <= cp <= 0x1F3FF:
        kinds.append(CodepointKind.EMOJI_MODIFIER)
    if 0x1F1E6 <= cp <= 0x1F1FF:
        kinds.append(CodepointKind.REGIONAL_INDICATOR)
    if cp == 0x20E3:
        kinds.append(CodepointKind.COMBINING_ENCLOSING_KEYCAP)
    if category == "Cc" and cp not in (0x09, 0x0A, 0x0D):
        kinds.append(CodepointKind.CONTROL)
    if category == "Cf" and not kinds:
        kinds.append(CodepointKind.FORMAT)
    return tuple(kinds)


_INVISIBLE_KINDS = frozenset(
    {
        CodepointKind.ZERO_WIDTH,
        CodepointKind.JOINER,
        CodepointKind.VARIATION_SELECTOR,
        CodepointKind.TAG,
        CodepointKind.BIDI_CONTROL,
        CodepointKind.FILLER,
        CodepointKind.FORMAT,
        CodepointKind.CONTROL,
    }
)


def codepoint_name(cp: int) -> str:
    """Return the Unicode name, or a documented label for unnamed code points."""
    name = unicodedata.name(chr(cp), "")
    if name:
        return name
    category = unicodedata.category(chr(cp))
    if category == "Cc":
        return f"<control-{cp:04X}>"
    if category == "Co":
        return f"<private-use-{cp:04X}>"
    if category == "Cn":
        return f"<unassigned-{cp:04X}>"
    return f"<unnamed-{cp:04X}>"


@dataclass(frozen=True, slots=True)
class CodepointInfo:
    index: int
    char: str
    codepoint: str
    name: str
    category: str
    bidi_class: str
    combining_class: int
    utf8_hex: str
    span: Span
    kinds: tuple[CodepointKind, ...]
    invisible: bool


def inspect_codepoints(text: str, table: OffsetTable | None = None) -> list[CodepointInfo]:
    """Describe every code point in ``text``. ``text`` must already be validated."""
    table = table or OffsetTable.build(text)
    out: list[CodepointInfo] = []
    for index, char in enumerate(text):
        cp = ord(char)
        kinds = classify_kinds(cp)
        out.append(
            CodepointInfo(
                index=index,
                char=char,
                codepoint=f"U+{cp:04X}",
                name=codepoint_name(cp),
                category=unicodedata.category(char),
                bidi_class=unicodedata.bidirectional(char),
                combining_class=unicodedata.combining(char),
                utf8_hex=char.encode("utf-8").hex(" ").upper(),
                span=table.span(index, index + 1),
                kinds=kinds,
                invisible=any(k in _INVISIBLE_KINDS for k in kinds),
            )
        )
    return out
