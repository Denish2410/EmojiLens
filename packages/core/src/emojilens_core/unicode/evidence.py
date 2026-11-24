"""Contextual evidence classification.

Each finding has a stable ``rule`` id, a ``category`` and an exact ``span``. The categories
are ordered by concern:

``legitimate_structure`` < ``informational`` < ``anomalous`` < ``suspicious``
< ``concealed_payload_decoded``

Legitimate structure (RGI emoji sequences, ZWJ/ZWNJ after an Indic virama, ZWNJ in Arabic
script) is recognised first, and the code points it covers are never escalated. All other
findings describe observations. None of them is a verdict about intent.
"""

from __future__ import annotations

import unicodedata
from dataclasses import dataclass, field
from enum import StrEnum

import emoji
import regex

from emojilens_core.unicode.decoders import (
    decode_tag_run,
    decode_vs_run,
    is_tag,
    is_variation_selector,
)
from emojilens_core.unicode.graphemes import Grapheme
from emojilens_core.unicode.offsets import OffsetTable, Span
from emojilens_core.unicode.scripts import (
    NEUTRAL_SCRIPTS,
    latin_lookalikes,
    script_of,
    script_profile,
)

RULESET_VERSION = "0.2.0"


class Category(StrEnum):
    LEGITIMATE_STRUCTURE = "legitimate_structure"
    INFORMATIONAL = "informational"
    ANOMALOUS = "anomalous"
    SUSPICIOUS = "suspicious"
    CONCEALED_PAYLOAD_DECODED = "concealed_payload_decoded"


CATEGORY_ORDER = {c: i for i, c in enumerate(Category)}


@dataclass(frozen=True, slots=True)
class Evidence:
    id: str
    rule: str
    category: Category
    message: str
    span: Span
    details: dict[str, object] = field(default_factory=dict)


ZWNJ, ZWJ = 0x200C, 0x200D
_ZERO_WIDTH = {0x200B, 0x2060, 0xFEFF, 0x2061, 0x2062, 0x2063, 0x2064, 0x180E, 0x00AD}
_BIDI_EMBED_OPEN = {0x202A, 0x202B, 0x202D, 0x202E}
_BIDI_POP = 0x202C
_BIDI_ISOLATE_OPEN = {0x2066, 0x2067, 0x2068}
_BIDI_PDI = 0x2069
_BIDI_MARKS = {0x200E, 0x200F, 0x061C}
_BIDI_ALL = _BIDI_EMBED_OPEN | _BIDI_ISOLATE_OPEN | {_BIDI_POP, _BIDI_PDI} | _BIDI_MARKS
_HANGUL_FILLERS = {0x115F, 0x1160, 0x3164, 0xFFA0}
_PICTO = regex.compile(r"\p{Extended_Pictographic}")
_WORDCHAR = regex.compile(r"[\p{L}\p{M}\p{N}]")
_WORD = regex.compile(r"[\p{L}\p{M}\u200c\u200d]+")
_LETTER = regex.compile(r"\p{L}")


def _rgi_subtype(seq: str) -> str:
    cps = [ord(c) for c in seq]
    if ZWJ in cps:
        return "zwj_sequence"
    if any(is_tag(cp) for cp in cps):
        return "tag_sequence"
    if 0x20E3 in cps:
        return "keycap_sequence"
    if all(0x1F1E6 <= cp <= 0x1F1FF for cp in cps):
        return "flag_sequence"
    if any(0x1F3FB <= cp <= 0x1F3FF for cp in cps):
        return "modifier_sequence"
    return "presentation_sequence"


class _Builder:
    def __init__(self, text: str, table: OffsetTable) -> None:
        self.text = text
        self.table = table
        self.items: list[Evidence] = []

    def add(
        self,
        rule: str,
        category: Category,
        start: int,
        end: int,
        message: str,
        **details: object,
    ) -> None:
        self.items.append(
            Evidence(
                id=f"{rule}@{start}-{end}",
                rule=rule,
                category=category,
                message=message,
                span=self.table.span(start, end),
                details={
                    "codepoints": [f"U+{ord(c):04X}" for c in self.text[start:end]],
                    **details,
                },
            )
        )


def classify(text: str, graphemes: list[Grapheme], table: OffsetTable) -> list[Evidence]:
    b = _Builder(text, table)
    covered: set[int] = set()
    n = len(text)

    # 1. Legitimate emoji sequences (RGI per the ``emoji`` package data).
    for g in graphemes:
        if g.codepoint_count > 1 and g.text in emoji.EMOJI_DATA:
            subtype = _rgi_subtype(g.text)
            b.add(
                "emoji.rgi_sequence",
                Category.LEGITIMATE_STRUCTURE,
                g.span.cp_start,
                g.span.cp_end,
                f"Recommended-for-general-interchange emoji {subtype.replace('_', ' ')}.",
                subtype=subtype,
                name=emoji.EMOJI_DATA[g.text].get("en", ""),
            )
            covered.update(range(g.span.cp_start, g.span.cp_end))

    def cp(i: int) -> int | None:
        return ord(text[i]) if 0 <= i < n else None

    def is_wordchar(i: int) -> bool:
        return 0 <= i < n and bool(_WORDCHAR.match(text[i]))

    has_rtl = any(unicodedata.bidirectional(c) in ("R", "AL") for c in text)

    i = 0
    while i < n:
        if i in covered:
            i += 1
            continue
        c = ord(text[i])

        # Joiners.
        if c in (ZWJ, ZWNJ):
            prev = cp(i - 1)
            prev_char = text[i - 1] if i > 0 else ""
            next_char = text[i + 1] if i + 1 < n else ""
            name = "ZWJ" if c == ZWJ else "ZWNJ"
            if prev is not None and unicodedata.combining(chr(prev)) == 9:
                b.add(
                    "indic.joiner_after_virama",
                    Category.LEGITIMATE_STRUCTURE,
                    i,
                    i + 1,
                    f"{name} after a virama selects a conjunct/half form ({script_of(prev_char)}).",
                    script=script_of(prev_char),
                )
            elif (
                c == ZWNJ
                and script_of(prev_char) in ("Arabic", "Syriac")
                and script_of(next_char) in ("Arabic", "Syriac")
            ):
                b.add(
                    "arabic.zwnj",
                    Category.LEGITIMATE_STRUCTURE,
                    i,
                    i + 1,
                    "ZWNJ between Arabic-script letters prevents joining (common in Persian).",
                )
            elif c == ZWJ and _PICTO.match(prev_char or " ") and _PICTO.match(next_char or " "):
                b.add(
                    "emoji.non_rgi_zwj_sequence",
                    Category.INFORMATIONAL,
                    i,
                    i + 1,
                    "ZWJ joins emoji into a sequence that is not in the RGI set.",
                )
            else:
                b.add(
                    "joiner.out_of_context",
                    Category.ANOMALOUS,
                    i,
                    i + 1,
                    f"{name} outside any recognised emoji or script context.",
                )
            i += 1
            continue

        # Variation selector runs.
        if is_variation_selector(c):
            j = i
            while j < n and j not in covered and is_variation_selector(ord(text[j])):
                j += 1
            run = text[i:j]
            base = text[i - 1] if i > 0 else ""
            if len(run) == 1:
                if c in (0xFE0E, 0xFE0F):
                    b.add(
                        "variation_selector.presentation",
                        Category.INFORMATIONAL,
                        i,
                        j,
                        "Text/emoji presentation selector outside a recognised RGI sequence.",
                    )
                elif script_of(base) == "Han":
                    b.add(
                        "variation_selector.ideographic",
                        Category.INFORMATIONAL,
                        i,
                        j,
                        "Ideographic variation selector after a Han character.",
                    )
                else:
                    b.add(
                        "variation_selector.unexpected",
                        Category.ANOMALOUS,
                        i,
                        j,
                        "Variation selector with no recognised base.",
                    )
            else:
                data, decoded = decode_vs_run(run)
                if decoded:
                    b.add(
                        "variation_selector.byte_payload",
                        Category.CONCEALED_PAYLOAD_DECODED,
                        i,
                        j,
                        f"{len(run)} variation selectors decode as UTF-8 bytes "
                        "(one byte per selector).",
                        decoded=decoded,
                        byte_length=len(data),
                        encoding="variation_selector_bytes",
                    )
                else:
                    b.add(
                        "variation_selector.unrecognized_run",
                        Category.SUSPICIOUS,
                        i,
                        j,
                        f"Run of {len(run)} variation selectors that does not decode as UTF-8.",
                        byte_hex=data.hex(),
                    )
            i = j
            continue

        # Tag character runs outside valid emoji tag sequences.
        if is_tag(c):
            j = i
            while j < n and j not in covered and is_tag(ord(text[j])):
                j += 1
            decoded_tags = decode_tag_run(text[i:j])
            if decoded_tags:
                b.add(
                    "tag.ascii_payload",
                    Category.CONCEALED_PAYLOAD_DECODED,
                    i,
                    j,
                    f"{j - i} invisible tag characters mirror ASCII text.",
                    decoded=decoded_tags,
                    encoding="unicode_tags_ascii",
                )
            else:
                b.add(
                    "tag.unrecognized_run",
                    Category.SUSPICIOUS,
                    i,
                    j,
                    "Tag characters outside an emoji tag sequence.",
                )
            i = j
            continue

        # Zero-width and invisible operators.
        if c in _ZERO_WIDTH:
            if c == 0xFEFF and i == 0:
                b.add(
                    "zero_width.leading_bom",
                    Category.INFORMATIONAL,
                    i,
                    i + 1,
                    "Byte order mark at the start of the text.",
                )
            elif c == 0x00AD and is_wordchar(i - 1) and is_wordchar(i + 1):
                b.add(
                    "soft_hyphen.inside_word",
                    Category.INFORMATIONAL,
                    i,
                    i + 1,
                    "Soft hyphen (line-break hint) inside a word.",
                )
            elif is_wordchar(i - 1) and is_wordchar(i + 1):
                b.add(
                    "zero_width.inside_word",
                    Category.SUSPICIOUS,
                    i,
                    i + 1,
                    f"{unicodedata.name(chr(c), 'invisible character')} splits a word "
                    "invisibly; tokenizers see two tokens.",
                )
            else:
                b.add(
                    "zero_width.standalone",
                    Category.ANOMALOUS,
                    i,
                    i + 1,
                    f"Invisible {unicodedata.name(chr(c), 'character')}.",
                )
            i += 1
            continue

        if c in _BIDI_ALL:
            if c in _BIDI_MARKS:
                b.add("bidi.mark", Category.INFORMATIONAL, i, i + 1, "Directional mark.")
            elif not has_rtl:
                b.add(
                    "bidi.control_without_rtl",
                    Category.SUSPICIOUS,
                    i,
                    i + 1,
                    "Bidirectional control in text with no right-to-left characters; "
                    "display order can differ from logical order.",
                )
            else:
                b.add(
                    "bidi.control",
                    Category.INFORMATIONAL,
                    i,
                    i + 1,
                    "Bidirectional formatting control in right-to-left text.",
                )
            i += 1
            continue

        if c in _HANGUL_FILLERS:
            neighbours = {script_of(text[k]) for k in (i - 1, i + 1) if 0 <= k < n}
            if "Hangul" not in neighbours:
                b.add(
                    "filler.out_of_context",
                    Category.ANOMALOUS,
                    i,
                    i + 1,
                    "Hangul filler (renders blank) outside Hangul text.",
                )
            i += 1
            continue

        cat = unicodedata.category(text[i])
        if cat == "Cc" and c not in (0x09, 0x0A, 0x0D):
            b.add("control.c0_c1", Category.ANOMALOUS, i, i + 1, f"Control character U+{c:04X}.")
        elif cat == "Cf":
            b.add(
                "format.other",
                Category.INFORMATIONAL,
                i,
                i + 1,
                f"Format character {unicodedata.name(text[i], f'U+{c:04X}')}.",
            )
        i += 1

    _bidi_balance(text, b)
    _styled_letters(text, b)
    _mixed_scripts(text, b)

    b.items.sort(key=lambda e: (e.span.cp_start, e.span.cp_end, CATEGORY_ORDER[e.category]))
    return b.items


def _bidi_balance(text: str, b: _Builder) -> None:
    embeds: list[int] = []
    isolates: list[int] = []
    for i, ch in enumerate(text):
        c = ord(ch)
        if c in _BIDI_EMBED_OPEN:
            embeds.append(i)
        elif c == _BIDI_POP and embeds:
            embeds.pop()
        elif c in _BIDI_ISOLATE_OPEN:
            isolates.append(i)
        elif c == _BIDI_PDI and isolates:
            isolates.pop()
            embeds.clear()  # PDI also terminates embeddings opened inside the isolate
        elif ch in "\n\u2029":
            embeds.clear()
            isolates.clear()
    for i in sorted(embeds + isolates):
        b.add(
            "bidi.unbalanced",
            Category.SUSPICIOUS,
            i,
            i + 1,
            "Bidirectional control is never closed; it affects the rest of the paragraph.",
        )


def _styled_letters(text: str, b: _Builder) -> None:
    i, n = 0, len(text)
    while i < n:
        j = i
        while j < n and _LETTER.match(text[j]):
            nf = unicodedata.normalize("NFKC", text[j])
            if nf == text[j] or not nf.isascii():
                break
            j += 1
        if j > i:
            b.add(
                "compat.styled_letters",
                Category.ANOMALOUS,
                i,
                j,
                "Compatibility-styled letters (e.g. mathematical or fullwidth) that NFKC "
                "maps to plain ASCII; keyword filters on the raw text miss them.",
                nfkc=unicodedata.normalize("NFKC", text[i:j]),
            )
            i = j
        else:
            i += 1


def _mixed_scripts(text: str, b: _Builder) -> None:
    dominant = script_profile(text).dominant
    for m in _WORD.finditer(text):
        word = m.group()
        letters = [ch for ch in word if _LETTER.match(ch)]
        scripts = {script_of(ch) for ch in letters} - NEUTRAL_SCRIPTS
        lookalikes = {ch: latin_lookalikes(ch)[0] for ch in letters if latin_lookalikes(ch)}
        if len(scripts) > 1:
            deceptive = "Latin" in scripts and bool(lookalikes)
            b.add(
                "homoglyph.mixed_script_word" if deceptive else "script.mixed_word",
                Category.SUSPICIOUS if deceptive else Category.ANOMALOUS,
                m.start(),
                m.end(),
                (
                    "Word mixes Latin with look-alike letters from another script."
                    if deceptive
                    else "Word mixes letters from more than one script."
                ),
                scripts=sorted(scripts),
                lookalikes={f"U+{ord(k):04X}": v for k, v in lookalikes.items()},
                skeleton="".join(lookalikes.get(ch, ch) for ch in word),
            )
        elif (
            dominant == "Latin"
            and scripts
            and scripts != {"Latin"}
            and len(letters) >= 2
            and all(ch in lookalikes for ch in letters)
        ):
            b.add(
                "homoglyph.whole_script_confusable",
                Category.SUSPICIOUS,
                m.start(),
                m.end(),
                "Word written entirely in look-alike letters of another script inside Latin text.",
                scripts=sorted(scripts),
                skeleton="".join(lookalikes[ch] for ch in word),
            )
