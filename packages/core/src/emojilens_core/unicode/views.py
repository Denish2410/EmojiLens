"""Named derived views with reversible provenance.

Every view is a list of segments that tile the original input exactly once, in order. Each
segment records the original span it came from, the span it occupies in the view, and its
view text. Any position in any view can therefore be traced back to original offsets.
"""

from __future__ import annotations

import unicodedata
from collections.abc import Callable, Iterable
from dataclasses import dataclass

import emoji

from emojilens_core.unicode.codepoints import CodepointInfo
from emojilens_core.unicode.evidence import Category, Evidence
from emojilens_core.unicode.graphemes import Grapheme
from emojilens_core.unicode.offsets import OffsetTable, Span

VIEW_DESCRIPTIONS = {
    "original": "Exact input. Never modified.",
    "nfc": "Unicode canonical composition (NFC).",
    "nfkc": "Compatibility composition (NFKC): folds styled and fullwidth forms.",
    "sanitized": "Invisible code points removed, except those inside legitimate structures "
    "(RGI emoji sequences, Indic and Arabic joiners).",
    "demojized": "Emoji replaced by their CLDR short names in English (:name:).",
    "decoded": "Recognised concealed payloads replaced in place by their decoded text, "
    "shown as ⟦…⟧.",
}


@dataclass(frozen=True, slots=True)
class ViewSegment:
    original: Span
    view: Span
    text: str


@dataclass(frozen=True, slots=True)
class DerivedView:
    name: str
    description: str
    text: str
    changed: bool
    segments: list[ViewSegment]


Piece = tuple[int, int, str]  # original cp start, original cp end, view text


def _finish(name: str, original: str, table: OffsetTable, pieces: list[Piece]) -> DerivedView:
    view_text = "".join(p[2] for p in pieces)
    vt = OffsetTable.build(view_text)
    segments: list[ViewSegment] = []
    pos = 0
    for start, end, text in pieces:
        segments.append(
            ViewSegment(
                original=table.span(start, end), view=vt.span(pos, pos + len(text)), text=text
            )
        )
        pos += len(text)
    return DerivedView(
        name=name,
        description=VIEW_DESCRIPTIONS[name],
        text=view_text,
        changed=view_text != original,
        segments=segments,
    )


def _per_grapheme(graphemes: list[Grapheme], fn: Callable[[str], str]) -> list[Piece]:
    return [(g.span.cp_start, g.span.cp_end, fn(g.text)) for g in graphemes]


def _with_overrides(
    text: str, graphemes: list[Grapheme], overrides: Iterable[Piece]
) -> list[Piece]:
    """Identity pieces bounded by grapheme edges, with disjoint override spans substituted."""
    starts = {s: (s, e, r) for s, e, r in overrides}
    boundaries = {g.span.cp_end for g in graphemes}
    pieces: list[Piece] = []
    i, n = 0, len(text)
    while i < n:
        if i in starts:
            s, e, r = starts[i]
            pieces.append((s, e, r))
            i = e
            continue
        j = i + 1
        while j < n and j not in boundaries and j not in starts:
            j += 1
        pieces.append((i, j, text[i:j]))
        i = j
    return pieces


def _normalized(
    name: str, form: str, text: str, graphemes: list[Grapheme], table: OffsetTable
) -> DerivedView:
    nf = form  # "NFC" | "NFKC"
    pieces = _per_grapheme(graphemes, lambda g: unicodedata.normalize(nf, g))  # type: ignore[arg-type]
    whole = unicodedata.normalize(nf, text)  # type: ignore[arg-type]
    if "".join(p[2] for p in pieces) != whole:
        # Normalization interacted across grapheme boundaries: fall back to one segment.
        pieces = [(0, len(text), whole)] if text else []
    return _finish(name, text, table, pieces)


def build_views(
    text: str,
    graphemes: list[Grapheme],
    codepoints: list[CodepointInfo],
    evidence: list[Evidence],
    table: OffsetTable,
) -> list[DerivedView]:
    legit: set[int] = set()
    for e in evidence:
        if e.category is Category.LEGITIMATE_STRUCTURE:
            legit.update(range(e.span.cp_start, e.span.cp_end))

    removed: list[Piece] = []
    for c in codepoints:
        if c.invisible and c.index not in legit:
            if removed and removed[-1][1] == c.index:
                removed[-1] = (removed[-1][0], c.index + 1, "")
            else:
                removed.append((c.index, c.index + 1, ""))

    decoded = [
        (e.span.cp_start, e.span.cp_end, f"⟦{e.details.get('decoded', '')}⟧")
        for e in evidence
        if e.category is Category.CONCEALED_PAYLOAD_DECODED
    ]

    def demojize(g: str) -> str:
        return emoji.demojize(g, language="en") if emoji.emoji_count(g) else g

    return [
        _finish("original", text, table, _per_grapheme(graphemes, lambda g: g)),
        _normalized("nfc", "NFC", text, graphemes, table),
        _normalized("nfkc", "NFKC", text, graphemes, table),
        _finish("sanitized", text, table, _with_overrides(text, graphemes, removed)),
        _finish("demojized", text, table, _per_grapheme(graphemes, demojize)),
        _finish("decoded", text, table, _with_overrides(text, graphemes, decoded)),
    ]
