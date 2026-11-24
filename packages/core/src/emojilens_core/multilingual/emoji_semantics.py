"""Localised emoji meanings from vendored Unicode CLDR annotations (license: Unicode-3.0)."""

from __future__ import annotations

import json
from dataclasses import dataclass
from functools import lru_cache
from importlib import resources
from typing import Any

from emojilens_core.multilingual.varieties import VARIETIES, Variety


@lru_cache(maxsize=1)
def _data() -> dict[str, Any]:
    raw = resources.files("emojilens_core.multilingual").joinpath("data/cldr_annotations.json")
    loaded: dict[str, Any] = json.loads(raw.read_text("utf-8"))
    return loaded


def cldr_version() -> str:
    return str(_data()["cldr_version"])


@dataclass(frozen=True, slots=True)
class EmojiMeaning:
    emoji: str
    locale: str
    name: str
    keywords: tuple[str, ...]
    fallback: bool  # True when the requested variety has no CLDR data and another locale was used


def _lookup(seq: str, locale: str) -> dict[str, Any] | None:
    locales: dict[str, dict[str, Any]] = _data()["locales"]
    table = locales.get(locale, {})
    hit = table.get(seq)
    if hit is None and seq.endswith("\ufe0f"):
        hit = table.get(seq[:-1])
    if hit is None:
        hit = table.get(seq + "\ufe0f")
    return hit


def meaning(seq: str, variety: Variety) -> EmojiMeaning | None:
    """CLDR name and keywords for an emoji in a variety, with documented fallbacks.

    gu-Latn has no CLDR locale: it falls back to gu, then en, with ``fallback=True``.
    hi-Latn data in CLDR is partial: missing entries fall back to hi, then en.
    """
    preferred = VARIETIES[variety].cldr_locale
    chain: list[str] = [loc for loc in (preferred,) if loc]
    if variety is Variety.GU_LATN:
        chain += ["gu", "en"]
    elif variety is Variety.HI_LATN:
        chain += ["hi", "en"]
    elif "en" not in chain:
        chain.append("en")
    for i, loc in enumerate(chain):
        hit = _lookup(seq, loc)
        if hit and hit.get("name"):
            return EmojiMeaning(
                emoji=seq,
                locale=loc,
                name=str(hit["name"]),
                keywords=tuple(hit.get("keywords", ())),
                fallback=i > 0 or loc != preferred,
            )
    return None
