"""The five supported language varieties and their metadata."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class Variety(StrEnum):
    EN = "en"
    HI = "hi"
    GU = "gu"
    HI_LATN = "hi-Latn"
    GU_LATN = "gu-Latn"


@dataclass(frozen=True, slots=True)
class VarietyInfo:
    code: Variety
    name: str
    script: str
    cldr_locale: str | None
    notes: str


VARIETIES: dict[Variety, VarietyInfo] = {
    Variety.EN: VarietyInfo(Variety.EN, "English", "Latin", "en", ""),
    Variety.HI: VarietyInfo(Variety.HI, "Hindi", "Devanagari", "hi", ""),
    Variety.GU: VarietyInfo(Variety.GU, "Gujarati", "Gujarati", "gu", ""),
    Variety.HI_LATN: VarietyInfo(
        Variety.HI_LATN,
        "Hinglish (Romanized Hindi)",
        "Latin",
        "hi-Latn",
        "No standard orthography; spelling varies widely (e.g. nahi/nahin/nhi).",
    ),
    Variety.GU_LATN: VarietyInfo(
        Variety.GU_LATN,
        "Romanized Gujarati",
        "Latin",
        None,
        "No CLDR annotations exist for gu-Latn; emoji meanings fall back to gu and en. "
        "Public data is scarce, so identification is the least reliable of the five.",
    ),
}
