"""Transparent, heuristic language-variety identification with explicit uncertainty.

Method ``script+lexicon/0.1``:

1. Tokens in Devanagari are tagged ``hi`` and tokens in Gujarati script ``gu``.
2. Latin tokens are looked up in seed lexicons (en, hi-Latn, gu-Latn). A token found in
   k lexicons contributes 1/k to each. Latin tokens with no lexicon hit are ``unknown``.
3. The text label is the variety with the highest mass. Confidence is that mass divided by
   all identified mass. A result is flagged uncertain when evidence is thin (fewer than three
   identified tokens) or the margin over the runner-up is under 0.2.

Code-mixing is measured with the Code-Mixing Index (CMI) over identified tokens:
``CMI = 100 * (1 - max_lang / (n - u))``, where n is the token count and u the number of
language-independent tokens (unknown, emoji, numbers, punctuation). CMI is 0 when n == u.
The CMI formulation is attributed to Das & Gambäck (2014); that reference is listed as
*unverified* in research/LITERATURE_REVIEW.md until it is checked against the paper.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from itertools import pairwise

import regex

from emojilens_core.multilingual.lexicons import LEXICON_VERSION, LEXICONS
from emojilens_core.multilingual.varieties import Variety
from emojilens_core.unicode.scripts import script_of

METHOD = f"script+lexicon/{LEXICON_VERSION}"
_WORD = regex.compile(r"[\p{L}\p{M}\u200c\u200d']+")
_PICTO = regex.compile(r"\p{Extended_Pictographic}")


@dataclass(frozen=True, slots=True)
class TokenTag:
    text: str
    cp_start: int
    cp_end: int
    tag: str  # a Variety value, "ambiguous", "unknown", "emoji" or "other"
    candidates: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class VarietyResult:
    label: Variety | None
    confidence: float
    uncertain: bool
    reasons: tuple[str, ...]
    scores: dict[str, float]
    tokens: list[TokenTag]
    code_mixed: bool
    cmi: float
    switch_points: int
    method: str


def _tag_word(word: str) -> tuple[str, tuple[str, ...]]:
    letters = [ch for ch in word if regex.match(r"\p{L}", ch)]
    scripts = {script_of(ch) for ch in letters}
    if scripts == {"Devanagari"}:
        return Variety.HI.value, (Variety.HI.value,)
    if scripts == {"Gujarati"}:
        return Variety.GU.value, (Variety.GU.value,)
    if scripts == {"Latin"}:
        low = word.lower().strip("'")
        hits = tuple(name for name, lex in LEXICONS.items() if low in lex)
        if len(hits) == 1:
            return hits[0], hits
        if hits:
            return "ambiguous", hits
        return "unknown", ()
    return "other", ()


def identify(text: str) -> VarietyResult:
    tokens: list[TokenTag] = []
    for m in _WORD.finditer(text):
        tag, cands = _tag_word(m.group())
        tokens.append(TokenTag(m.group(), m.start(), m.end(), tag, cands))
    for m in _PICTO.finditer(text):
        tokens.append(TokenTag(m.group(), m.start(), m.end(), "emoji", ()))
    tokens.sort(key=lambda t: t.cp_start)

    mass: dict[str, float] = defaultdict(float)
    for t in tokens:
        for c in t.candidates:
            mass[c] += 1 / len(t.candidates)
    identified = sum(mass.values())
    ranked = sorted(mass.items(), key=lambda kv: (-kv[1], kv[0]))

    reasons: list[str] = []
    label: Variety | None = None
    confidence = 0.0
    if ranked:
        label = Variety(ranked[0][0])
        confidence = ranked[0][1] / identified
        margin = confidence - (ranked[1][1] / identified if len(ranked) > 1 else 0.0)
        if identified < 3:
            reasons.append(f"thin evidence: {identified:g} identified token(s)")
        if margin < 0.2:
            reasons.append(f"small margin over runner-up ({margin:.2f})")
    else:
        reasons.append("no identifiable tokens")
    unknown = sum(1 for t in tokens if t.tag == "unknown")
    if unknown and tokens and unknown / len(tokens) > 0.5:
        reasons.append(f"{unknown} of {len(tokens)} tokens not in any lexicon")

    # Code-mixing statistics over unambiguous language tokens.
    lang_tokens = [t.tag for t in tokens if t.tag in {v.value for v in Variety}]
    n_lang = len(lang_tokens)
    if n_lang:
        counts: dict[str, int] = defaultdict(int)
        for tag in lang_tokens:
            counts[tag] += 1
        cmi = 100 * (1 - max(counts.values()) / n_lang)
    else:
        cmi = 0.0
    switches = sum(1 for a, b in pairwise(lang_tokens) if a != b)

    return VarietyResult(
        label=label,
        confidence=round(confidence, 4),
        uncertain=bool(reasons),
        reasons=tuple(reasons),
        scores={k: round(v, 4) for k, v in ranked},
        tokens=tokens,
        code_mixed=len({t for t in lang_tokens}) > 1,
        cmi=round(cmi, 2),
        switch_points=switches,
        method=METHOD,
    )
