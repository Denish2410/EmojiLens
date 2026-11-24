"""Concept lexicon for deliberate code-mixing transformations (v0.1).

Hand-curated by the EmojiLens developers: common, non-sensitive words in five varieties.
Romanized spellings follow one common convention each, although real usage varies. This lexicon
has **not** been reviewed by native speakers yet. Review is part of the annotation plan, and errors
found then must be fixed by bumping LEXICON_VERSION.
"""

from __future__ import annotations

LEXICON_VERSION = "0.1.0"

# concept -> (en, hi, gu, hi-Latn, gu-Latn)
CONCEPTS: dict[str, tuple[str, str, str, str, str]] = {
    "today": ("today", "आज", "આજે", "aaj", "aaje"),
    "good": ("good", "अच्छा", "સારું", "acha", "saru"),
    "very": ("very", "बहुत", "ખૂબ", "bahut", "khub"),
    "friend": ("friend", "दोस्त", "મિત્ર", "dost", "mitra"),
    "home": ("home", "घर", "ઘર", "ghar", "ghar"),
    "food": ("food", "खाना", "ખાવાનું", "khana", "khavanu"),
    "water": ("water", "पानी", "પાણી", "paani", "paani"),
    "time": ("time", "समय", "સમય", "samay", "samay"),
    "work": ("work", "काम", "કામ", "kaam", "kaam"),
    "happy": ("happy", "खुश", "ખુશ", "khush", "khush"),
    "now": ("now", "अभी", "હમણાં", "abhi", "hamna"),
    "yes": ("yes", "हाँ", "હા", "haan", "ha"),
    "thanks": ("thanks", "धन्यवाद", "આભાર", "dhanyavaad", "aabhar"),
    "morning": ("morning", "सुबह", "સવાર", "subah", "savar"),
    "night": ("night", "रात", "રાત", "raat", "raat"),
    "day": ("day", "दिन", "દિવસ", "din", "divas"),
    "brother": ("brother", "भाई", "ભાઈ", "bhai", "bhai"),
    "sister": ("sister", "बहन", "બહેન", "behen", "ben"),
    "weather": ("weather", "मौसम", "હવામાન", "mausam", "havaman"),
    "beautiful": ("beautiful", "सुंदर", "સુંદર", "sundar", "sundar"),
    "big": ("big", "बड़ा", "મોટું", "bada", "motu"),
    "small": ("small", "छोटा", "નાનું", "chota", "nanu"),
    "come": ("come", "आओ", "આવો", "aao", "aavo"),
    "meeting": ("meeting", "बैठक", "મીટિંગ", "baithak", "meeting"),
    "tomorrow": ("tomorrow", "कल", "આવતીકાલે", "kal", "kale"),
}

ORDER = ("en", "hi", "gu", "hi-Latn", "gu-Latn")


def table(variety: str) -> dict[str, str]:
    """Map a word in ``variety`` (lowercased for Latin) to its concept id."""
    idx = ORDER.index(variety)
    out: dict[str, str] = {}
    for concept, forms in CONCEPTS.items():
        out.setdefault(forms[idx].lower(), concept)
    return out


def form(concept: str, variety: str) -> str:
    return CONCEPTS[concept][ORDER.index(variety)]
