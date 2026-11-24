"""Comparison baselines. Each returns (flagged, score, detail)."""

from __future__ import annotations

import re
import unicodedata
from collections.abc import Callable

from emojilens_core.unicode import analyze

Baseline = Callable[[str], tuple[bool, float, str]]


def no_defence(text: str) -> tuple[bool, float, str]:
    return False, 0.0, "never flags"


def strip_invisibles(text: str) -> tuple[bool, float, str]:
    """Flags input that a naive sanitizer would change (removes every invisible code point)."""
    changed = any(c.invisible for c in analyze(text).codepoints)
    return changed, float(changed), "invisible code points present" if changed else "unchanged"


def nfkc_normalization(text: str) -> tuple[bool, float, str]:
    changed = unicodedata.normalize("NFKC", text) != text
    return changed, float(changed), "NFKC changes the text" if changed else "NFKC-stable"


def keyword_filter(keywords: tuple[str, ...]) -> Baseline:
    """Case-insensitive whole-word match on the raw text (the naive filter attacks evade)."""
    rx = (
        re.compile(r"\b(?:" + "|".join(re.escape(k) for k in keywords) + r")\b", re.IGNORECASE)
        if keywords
        else None
    )

    def run(text: str) -> tuple[bool, float, str]:
        hit = bool(rx and rx.search(text))
        return hit, float(hit), "keyword matched" if hit else "no keyword"

    return run
