"""Multilingual engine: language varieties, identification, emoji semantics."""

from emojilens_core.multilingual.emoji_semantics import EmojiMeaning, cldr_version, meaning
from emojilens_core.multilingual.identify import METHOD, TokenTag, VarietyResult, identify
from emojilens_core.multilingual.varieties import VARIETIES, Variety, VarietyInfo

__all__ = [
    "METHOD",
    "VARIETIES",
    "EmojiMeaning",
    "TokenTag",
    "Variety",
    "VarietyInfo",
    "VarietyResult",
    "cldr_version",
    "identify",
    "meaning",
]
