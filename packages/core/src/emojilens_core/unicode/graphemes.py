"""Extended grapheme cluster segmentation (UAX #29) via the ``regex`` package."""

from __future__ import annotations

from dataclasses import dataclass

import regex

from emojilens_core.unicode.offsets import OffsetTable, Span

_GRAPHEME = regex.compile(r"\X", flags=regex.VERSION1)


@dataclass(frozen=True, slots=True)
class Grapheme:
    index: int
    text: str
    span: Span
    codepoint_count: int


def segment_graphemes(text: str, table: OffsetTable | None = None) -> list[Grapheme]:
    """Split ``text`` into extended grapheme clusters with full offset spans.

    The concatenation of all ``Grapheme.text`` values always equals ``text``.
    """
    table = table or OffsetTable.build(text)
    out: list[Grapheme] = []
    for index, match in enumerate(_GRAPHEME.finditer(text)):
        start, end = match.span()
        out.append(
            Grapheme(
                index=index,
                text=match.group(),
                span=table.span(start, end),
                codepoint_count=end - start,
            )
        )
    return out
