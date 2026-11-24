"""Compare original text with OCR or VLM readings of its rendering."""

from __future__ import annotations

import unicodedata
from dataclasses import dataclass

import regex

_WS = regex.compile(r"\s+")


def levenshtein(a: list[str], b: list[str]) -> int:
    prev = list(range(len(b) + 1))
    for i, x in enumerate(a, 1):
        cur = [i]
        for j, y in enumerate(b, 1):
            cur.append(min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (x != y)))
        prev = cur
    return prev[-1]


def _graphemes(s: str) -> list[str]:
    found: list[str] = regex.findall(r"\X", s)
    return found


def visible_form(text: str) -> str:
    """What a reader can see: format/invisible code points removed, NFC, whitespace collapsed."""
    kept = "".join(c for c in text if unicodedata.category(c) not in ("Cf", "Cc") or c in "\n\t")
    kept = "".join(
        c for c in kept if not (0xFE00 <= ord(c) <= 0xFE0F or 0xE0100 <= ord(c) <= 0xE01EF)
    )
    collapsed: str = _WS.sub(" ", unicodedata.normalize("NFC", kept))
    return collapsed.strip()


@dataclass(frozen=True, slots=True)
class Comparison:
    reference: str
    reading: str
    grapheme_error_rate: float | None
    exact_match: bool
    nfkc_casefold_match: bool
    hidden_codepoints_in_original: int
    hidden_codepoints_recovered: int


def compare(original: str, reading: str) -> Comparison:
    """GER is computed against the *visible* form of the original (hidden code points cannot be
    seen, so OCR is not penalised for missing them); hidden-content recovery is reported apart."""
    ref = visible_form(original)
    got = _WS.sub(" ", unicodedata.normalize("NFC", reading)).strip()
    rg, gg = _graphemes(ref), _graphemes(got)
    ger = levenshtein(rg, gg) / len(rg) if rg else None
    hidden = [
        c
        for c in original
        if unicodedata.category(c) == "Cf"
        or 0xFE00 <= ord(c) <= 0xFE0F
        or 0xE0100 <= ord(c) <= 0xE01EF
    ]
    return Comparison(
        reference=ref,
        reading=got,
        grapheme_error_rate=None if ger is None else round(ger, 4),
        exact_match=ref == got,
        nfkc_casefold_match=unicodedata.normalize("NFKC", ref).casefold()
        == unicodedata.normalize("NFKC", got).casefold(),
        hidden_codepoints_in_original=len(hidden),
        hidden_codepoints_recovered=sum(1 for c in hidden if c in reading),
    )
