"""Script identification and Latin-lookalike (homoglyph) data.

Script values follow the Unicode ``Script`` property as implemented by ``regex``.
Lookalike data comes from the ``confusable_homoglyphs`` package (MIT), which bundles a
snapshot of Unicode's confusables.txt; its Unicode version is older than ``regex``'s.
This is recorded as a limitation (docs/DECISIONS.md, D-009).
"""

from __future__ import annotations

import json
from collections import Counter
from dataclasses import dataclass
from functools import lru_cache
from importlib import resources

import regex

NEUTRAL_SCRIPTS = frozenset({"Common", "Inherited", "Unknown"})

# Ordered roughly by expected frequency in EmojiLens inputs; first match wins.
_SCRIPTS = (
    "Latin",
    "Common",
    "Inherited",
    "Devanagari",
    "Gujarati",
    "Cyrillic",
    "Greek",
    "Arabic",
    "Hebrew",
    "Bengali",
    "Gurmukhi",
    "Oriya",
    "Tamil",
    "Telugu",
    "Kannada",
    "Malayalam",
    "Sinhala",
    "Thai",
    "Lao",
    "Tibetan",
    "Myanmar",
    "Georgian",
    "Armenian",
    "Hangul",
    "Hiragana",
    "Katakana",
    "Han",
    "Ethiopic",
    "Cherokee",
    "Canadian_Aboriginal",
    "Mongolian",
    "Khmer",
)
_PATTERNS = tuple((name, regex.compile(rf"\p{{Script={name}}}")) for name in _SCRIPTS)


@lru_cache(maxsize=8192)
def script_of(char: str) -> str:
    for name, pattern in _PATTERNS:
        if pattern.match(char):
            return name
    return "Other"


@lru_cache(maxsize=1)
def _confusables() -> dict[str, list[dict[str, str]]]:
    data = resources.files("confusable_homoglyphs").joinpath("confusables.json").read_text("utf-8")
    loaded: dict[str, list[dict[str, str]]] = json.loads(data)
    return loaded


@lru_cache(maxsize=8192)
def latin_lookalikes(char: str) -> tuple[str, ...]:
    """Latin (or ASCII) characters that ``char`` can be visually confused with."""
    if script_of(char) == "Latin":
        return ()
    out = []
    for entry in _confusables().get(char, []):
        target = entry["c"]
        if len(target) == 1 and (target.isascii() or script_of(target) == "Latin"):
            out.append(target)
    return tuple(out)


def has_latin_lookalike(char: str) -> bool:
    return bool(latin_lookalikes(char))


@dataclass(frozen=True, slots=True)
class ScriptProfile:
    counts: dict[str, int]
    dominant: str | None
    is_mixed: bool


def script_profile(text: str) -> ScriptProfile:
    """Count letters by script (neutral scripts excluded)."""
    counts: Counter[str] = Counter()
    for char in text:
        if regex.match(r"\p{L}", char):
            s = script_of(char)
            if s not in NEUTRAL_SCRIPTS:
                counts[s] += 1
    dominant = counts.most_common(1)[0][0] if counts else None
    return ScriptProfile(counts=dict(counts), dominant=dominant, is_mixed=len(counts) > 1)
