"""The identity control and the six transformation families.

All payloads are caller-provided *harmless surrogate* strings (default ``SURROGATE-TOKEN``).
These transforms exist for controlled, local, defensive evaluation only.
"""

from __future__ import annotations

import json
import random
import unicodedata
from functools import lru_cache
from importlib import resources
from typing import Any

import emoji
import regex

from emojilens_core.multilingual import Variety
from emojilens_core.multilingual.emoji_semantics import _data as cldr_data
from emojilens_core.transforms import codemix_lexicon as cm
from emojilens_core.transforms.base import Param, Piece, Transform, TransformSpec
from emojilens_core.unicode.decoders import decode_tag_run, decode_vs_run
from emojilens_core.unicode.graphemes import segment_graphemes
from emojilens_core.unicode.scripts import script_of

ALL = tuple(Variety)
LATIN = (Variety.EN, Variety.HI_LATN, Variety.GU_LATN)
_WORD = regex.compile(r"[\p{L}\p{M}\u200c\u200d]+")
RATE = Param(
    "rate", "float", 0.5, "Fraction of eligible positions to transform.", minimum=0.0, maximum=1.0
)
SURROGATE = "SURROGATE-TOKEN"


def _graphemes(text: str) -> list[Piece]:
    return [(g.span.cp_start, g.span.cp_end, g.text) for g in segment_graphemes(text)]


def _replace_spans(text: str, edits: dict[int, tuple[int, str]]) -> list[Piece]:
    """Pieces for ``text`` with grapheme-aligned ``edits`` ({start: (end, replacement)})."""
    pieces: list[Piece] = []
    skip_until = 0
    for s, e, t in _graphemes(text):
        if s < skip_until:
            continue
        if s in edits:
            end, rep = edits[s]
            pieces.append((s, end, rep))
            skip_until = end
        else:
            pieces.append((s, e, t))
    return pieces


def _words(text: str) -> list[regex.Match[str]]:
    """Word matches whose start and end fall on grapheme boundaries (safe to replace)."""
    bounds = {0} | {g.span.cp_end for g in segment_graphemes(text)}
    return [m for m in _WORD.finditer(text) if m.start() in bounds and m.end() in bounds]


def _pick(rng: random.Random, items: list[Any], rate: float) -> list[Any]:
    return [x for x in items if rng.random() < rate]


# --------------------------------------------------------------------------- identity


def _identity(
    text: str, _v: Variety, _r: random.Random, _p: dict[str, Any]
) -> tuple[list[Piece], dict[str, Any]]:
    return _graphemes(text), {}


IDENTITY = Transform(
    TransformSpec(
        "identity",
        "1.0.0",
        "identity",
        "Returns the input unchanged. Evaluation control.",
        ALL,
        (),
        False,
        True,
    ),
    _identity,
    decoder=lambda out, _prov: out,
)

# --------------------------------------------------------------------------- 1. Unicode smuggling

_ZW_CHARS = {"zwsp": "\u200b", "zwnj": "\u200c", "wj": "\u2060"}


def _smuggling(
    text: str, _v: Variety, rng: random.Random, p: dict[str, Any]
) -> tuple[list[Piece], dict[str, Any]]:
    method = p["method"]
    if method == "zero_width_split":
        ch = _ZW_CHARS[p["zero_width_char"]]
        pieces: list[Piece] = []
        inserted = 0
        for s, e, t in _graphemes(text):
            prev = pieces[-1][2] if pieces else ""
            inside = prev and _WORD.fullmatch(prev[-1:] or " ") and _WORD.fullmatch(t[:1] or " ")
            if inside and rng.random() < p["rate"]:
                pieces[-1] = (pieces[-1][0], pieces[-1][1], prev + ch)
                inserted += 1
            pieces.append((s, e, t))
        return pieces, {"inserted": inserted, "char": f"U+{ord(ch):04X}"}
    if method == "tag_payload":
        hidden = "".join(chr(0xE0000 + ord(c)) for c in p["payload"] if 0x20 <= ord(c) <= 0x7E)
        pieces = _graphemes(text)
        if not pieces:
            return [], {"payload_chars": 0}
        s, e, t = pieces[-1]
        pieces[-1] = (s, e, t + hidden)
        return pieces, {"payload_chars": len(hidden), "encoding": "unicode_tags_ascii"}
    if method == "variation_selector_payload":
        data = p["payload"].encode("utf-8")
        hidden = "".join(chr(0xFE00 + b) if b < 16 else chr(0xE0100 + b - 16) for b in data)
        pieces = _graphemes(text)
        if not pieces:
            return [], {"payload_bytes": 0}
        s, e, t = pieces[0]
        pieces[0] = (s, e, t + hidden)
        return pieces, {"payload_bytes": len(data), "encoding": "variation_selector_bytes"}
    # bidi_reorder: wrap eligible words as RLO + reversed + PDF
    # (renders like the original in LTR text while the logical order is reversed)
    words = [m for m in _words(text) if len(m.group()) > 2 and script_of(m.group()[0]) == "Latin"]
    chosen = _pick(rng, words, p["rate"])
    edits = {m.start(): (m.end(), "\u202e" + m.group()[::-1] + "\u202c") for m in chosen}
    return _replace_spans(text, edits), {"wrapped_words": len(chosen)}


def _smuggling_decode(out: str, prov: dict[str, Any]) -> str | None:
    enc = prov.get("encoding")
    if enc == "unicode_tags_ascii":
        return "".join(c for c in out if not 0xE0000 <= ord(c) <= 0xE007F)
    if enc == "variation_selector_bytes":
        return "".join(
            c for c in out if not (0xFE00 <= ord(c) <= 0xFE0F or 0xE0100 <= ord(c) <= 0xE01EF)
        )
    if "inserted" in prov:
        return out.replace(chr(int(prov["char"][2:], 16)), "")
    return None


SMUGGLING = Transform(
    TransformSpec(
        "unicode_smuggling",
        "1.0.0",
        "unicode_smuggling",
        "Hides content or splits words with invisible code points: zero-width splits, "
        "tag-character "
        "or variation-selector payloads (harmless surrogate text), or bidi-override reordering.",
        ALL,
        (
            Param(
                "method",
                "choice",
                "zero_width_split",
                "Smuggling technique.",
                ("zero_width_split", "tag_payload", "variation_selector_payload", "bidi_reorder"),
            ),
            RATE,
            Param(
                "zero_width_char",
                "choice",
                "zwsp",
                "Invisible separator for word splits.",
                ("zwsp", "zwnj", "wj"),
            ),
            Param(
                "payload",
                "string",
                SURROGATE,
                "Harmless surrogate text to conceal (printable ASCII for tags).",
            ),
        ),
        True,
        True,
    ),
    _smuggling,
    decoder=_smuggling_decode,
)


def decode_payload(output: str) -> str | None:
    """Recover a concealed payload from a smuggled output (for round-trip tests)."""
    tags = "".join(c for c in output if 0xE0000 <= ord(c) <= 0xE007F)
    if tags:
        return decode_tag_run(tags)
    vs = "".join(c for c in output if 0xFE00 <= ord(c) <= 0xFE0F or 0xE0100 <= ord(c) <= 0xE01EF)
    return decode_vs_run(vs)[1] if vs else None


# --------------------------------------------------------------------------- 2. Emoji substitution


@lru_cache(maxsize=8)
def _word_to_emoji(locale: str) -> dict[str, list[str]]:
    """Single-word CLDR names (preferred) and keywords -> emoji, for one locale."""
    table: dict[str, list[str]] = {}
    entries: dict[str, dict[str, Any]] = cldr_data()["locales"].get(locale, {})
    for seq, ann in sorted(entries.items()):
        if any(0x1F3FB <= ord(c) <= 0x1F3FF for c in seq):  # skip skin-tone variants
            continue
        if not emoji.is_emoji(seq):  # CLDR also annotates non-emoji symbols
            continue
        name = str(ann.get("name", "")).lower()
        if name and " " not in name:
            table.setdefault(name, []).insert(0, seq)
        for kw in ann.get("keywords", []):
            kw = str(kw).lower()
            if " " not in kw and seq not in table.get(kw, []):
                table.setdefault(kw, []).append(seq)
    return table


_SUB_LOCALE = {Variety.EN: "en", Variety.HI: "hi", Variety.GU: "gu", Variety.HI_LATN: "hi-Latn"}


def _substitution(
    text: str, v: Variety, rng: random.Random, p: dict[str, Any]
) -> tuple[list[Piece], dict[str, Any]]:
    locale = _SUB_LOCALE.get(v)
    if locale is None:
        return _graphemes(text), {"locale": None, "replaced": []}
    table = _word_to_emoji(locale)
    eligible = [m for m in _words(text) if m.group().lower() in table]
    chosen = _pick(rng, eligible, p["rate"])
    edits: dict[int, tuple[int, str]] = {}
    replaced = []
    for m in chosen:
        options = table[m.group().lower()]
        seq = options[0] if p["prefer_name_match"] else rng.choice(options)
        edits[m.start()] = (m.end(), seq)
        replaced.append({"word": m.group(), "emoji": seq})
    return _replace_spans(text, edits), {"locale": locale, "replaced": replaced}


SUBSTITUTION = Transform(
    TransformSpec(
        "emoji_substitution",
        "1.0.0",
        "emoji_substitution",
        "Replaces words with emoji whose CLDR name or keyword matches, in the text's own locale.",
        (Variety.EN, Variety.HI, Variety.GU, Variety.HI_LATN),
        (
            RATE,
            Param(
                "prefer_name_match",
                "bool",
                True,
                "Prefer the emoji whose CLDR name equals the word.",
            ),
        ),
        True,
        False,
    ),
    _substitution,
)

# --------------------------------------------------------------------------- 3. Emoji cipher

_POOL = [chr(c) for c in range(0x1F600, 0x1F640)] + [chr(c) for c in range(0x1F400, 0x1F43F)]


def _cipher_key(scheme: str, rng: random.Random) -> dict[str, str]:
    letters = "abcdefghijklmnopqrstuvwxyz"
    if scheme == "regional_indicator":
        return {c: chr(0x1F1E6 + i) for i, c in enumerate(letters)}
    if scheme == "squared_letters":
        return {c: chr(0x1F130 + i) for i, c in enumerate(letters)}
    pool = sorted(set(_POOL))
    rng.shuffle(pool)
    return dict(zip(letters, pool[:26], strict=True))


def _cipher(
    text: str, _v: Variety, rng: random.Random, p: dict[str, Any]
) -> tuple[list[Piece], dict[str, Any]]:
    key = _cipher_key(p["scheme"], rng)
    sep = "\u200c" if p["scheme"] == "regional_indicator" else ""
    pieces: list[Piece] = []
    for i, ch in enumerate(text):
        enc = key.get(ch.lower())
        # ZWNJ after each regional indicator stops adjacent letters fusing into flags.
        pieces.append((i, i + 1, enc + sep if enc else ch))
    return pieces, {
        "scheme": p["scheme"],
        "key": key,
        "separator": f"U+{ord(sep):04X}" if sep else None,
    }


def _cipher_decode(out: str, prov: dict[str, Any]) -> str | None:
    inv = {v: k for k, v in prov["key"].items()}
    return "".join(inv.get(c, c) for c in out if c != "\u200c" or not prov.get("separator"))


CIPHER = Transform(
    TransformSpec(
        "emoji_cipher",
        "1.0.0",
        "emoji_cipher",
        "Letter-by-letter substitution cipher into emoji or emoji-like symbols. "
        "The key is stored in "
        "provenance, so decoding is reversible. Letters are lowercased.",
        LATIN,
        (
            Param(
                "scheme",
                "choice",
                "keyed_emoji",
                "Cipher alphabet.",
                ("keyed_emoji", "regional_indicator", "squared_letters"),
            ),
        ),
        True,
        True,  # reversible up to case: letters are lowercased before encoding
    ),
    _cipher,
    decoder=_cipher_decode,
    roundtrip_key=str.lower,
)

# --------------------------------------------------------------------------- 4. Homoglyph


@lru_cache(maxsize=1)
def _homoglyph_map() -> dict[str, list[str]]:
    data: dict[str, list[dict[str, str]]] = json.loads(
        resources.files("confusable_homoglyphs").joinpath("confusables.json").read_text("utf-8")
    )
    out: dict[str, set[str]] = {}
    for ch, entries in data.items():
        if len(ch) != 1 or (unicodedata.category(ch)[0] not in "LM" and not ch.isdigit()):
            continue
        s = script_of(ch)
        for e in entries:
            t = e["c"]
            if len(t) != 1:
                continue
            ts = script_of(t)
            if (
                s in ("Cyrillic", "Greek")
                and unicodedata.category(ch) in ("Lu", "Ll")
                and t.isascii()
                and t.isalpha()
            ) or {s, ts} == {"Devanagari", "Gujarati"}:
                out.setdefault(t, set()).add(ch)
    return {k: sorted(v) for k, v in out.items()}


def _homoglyph(
    text: str, _v: Variety, rng: random.Random, p: dict[str, Any]
) -> tuple[list[Piece], dict[str, Any]]:
    m = _homoglyph_map()
    pieces: list[Piece] = []
    swaps = []
    for s, e, t in _graphemes(text):
        new = []
        for ch in t:
            if ch in m and rng.random() < p["rate"]:
                rep = rng.choice(m[ch])
                swaps.append({"from": f"U+{ord(ch):04X}", "to": f"U+{ord(rep):04X}"})
                new.append(rep)
            else:
                new.append(ch)
        pieces.append((s, e, "".join(new)))
    return pieces, {"swaps": swaps, "data": "confusable_homoglyphs 3.3.1"}


HOMOGLYPH = Transform(
    TransformSpec(
        "homoglyph",
        "1.0.0",
        "homoglyph",
        "Swaps characters for visually confusable ones: Latin to Cyrillic/Greek, and between "
        "Devanagari and Gujarati where confusables data lists a pair.",
        ALL,
        (RATE,),
        True,
        False,
    ),
    _homoglyph,
)

# --------------------------------------------------------------------------- 5. Text obfuscation

_LEET = {"a": "4", "e": "3", "i": "1", "o": "0", "s": "5", "t": "7", "g": "9", "b": "8"}
_STYLE_BASE = {
    "bold": (0x1D400, 0x1D41A),
    "monospace": (0x1D670, 0x1D68A),
    "fullwidth": (0xFF21, 0xFF41),
}


def _styled(ch: str, style: str) -> str:
    upper, lower = _STYLE_BASE[style]
    if "A" <= ch <= "Z":
        return chr(upper + ord(ch) - 65)
    if "a" <= ch <= "z":
        return chr(lower + ord(ch) - 97)
    return ch


def _obfuscation(
    text: str, _v: Variety, rng: random.Random, p: dict[str, Any]
) -> tuple[list[Piece], dict[str, Any]]:
    method, rate = p["method"], p["rate"]
    pieces: list[Piece] = []
    graphemes = _graphemes(text)
    for idx, (s, e, t) in enumerate(graphemes):
        out = t
        if len(t) == 1 and t.isascii() and t.isalpha() and rng.random() < rate:
            if method == "leetspeak":
                out = _LEET.get(t.lower(), t)
            elif method in _STYLE_BASE:
                out = _styled(t, method)
            elif method == "case_noise":
                out = t.swapcase()
            elif method == "separator_insertion":
                nxt = graphemes[idx + 1][2] if idx + 1 < len(graphemes) else ""
                out = t + (p["separator"] if nxt[:1].isalpha() else "")
            elif method == "char_repeat":
                out = t * 3
        pieces.append((s, e, out))
    return pieces, {"method": method}


OBFUSCATION = Transform(
    TransformSpec(
        "text_obfuscation",
        "1.0.0",
        "text_obfuscation",
        "Visible obfuscation of Latin letters: leetspeak, styled mathematical letters, "
        "fullwidth forms, "
        "case noise, separator insertion or character repetition.",
        LATIN,
        (
            Param(
                "method",
                "choice",
                "leetspeak",
                "Obfuscation technique.",
                (
                    "leetspeak",
                    "bold",
                    "monospace",
                    "fullwidth",
                    "case_noise",
                    "separator_insertion",
                    "char_repeat",
                ),
            ),
            RATE,
            Param(
                "separator",
                "choice",
                ".",
                "Separator for separator_insertion.",
                (".", "-", "_", " "),
            ),
        ),
        True,
        False,
    ),
    _obfuscation,
)

# ----------------------------------------------------------- 6. Deliberate code-mixing


def _codemix(
    text: str, v: Variety, rng: random.Random, p: dict[str, Any]
) -> tuple[list[Piece], dict[str, Any]]:
    target = p["target"]
    if target == v.value:
        return _graphemes(text), {"swapped": [], "lexicon": cm.LEXICON_VERSION}
    src = cm.table(v.value)
    eligible = [m for m in _words(text) if m.group().lower() in src]
    chosen = _pick(rng, eligible, p["rate"])
    edits: dict[int, tuple[int, str]] = {}
    swapped = []
    for m in chosen:
        concept = src[m.group().lower()]
        rep = cm.form(concept, target)
        if m.group()[:1].isupper() and rep[:1].isalpha() and rep.isascii():
            rep = rep[:1].upper() + rep[1:]
        edits[m.start()] = (m.end(), rep)
        swapped.append({"concept": concept, "from": m.group(), "to": rep})
    return _replace_spans(text, edits), {"swapped": swapped, "lexicon": cm.LEXICON_VERSION}


CODEMIX = Transform(
    TransformSpec(
        "code_mixing",
        "1.0.0",
        "code_mixing",
        "Deliberately swaps known words for their equivalents in another variety, using a "
        "small curated concept lexicon. Code-mixed language is legitimate; this transform "
        "exists to test consistency.",
        ALL,
        (
            RATE,
            Param("target", "choice", "hi", "Variety to mix in.", tuple(x.value for x in Variety)),
        ),
        True,
        False,
    ),
    _codemix,
)

REGISTRY: dict[str, Transform] = {
    t.spec.id: t
    for t in (IDENTITY, SMUGGLING, SUBSTITUTION, CIPHER, HOMOGLYPH, OBFUSCATION, CODEMIX)
}
FAMILIES = (
    "unicode_smuggling",
    "emoji_substitution",
    "emoji_cipher",
    "homoglyph",
    "text_obfuscation",
    "code_mixing",
)

__all__ = ["FAMILIES", "REGISTRY", "decode_payload"]
