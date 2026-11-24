"""Evidence classification. Written before the implementation (test-first).

Principle under test: legitimate structure is recognised and never escalated,
while concealed or deceptive structure is located precisely.
"""

from __future__ import annotations

import pytest

from emojilens_core.unicode import analyze
from emojilens_core.unicode.evidence import Category, Evidence


def ev(text: str) -> list[Evidence]:
    return analyze(text).evidence


def rules(text: str) -> set[str]:
    return {e.rule for e in ev(text)}


def worst(text: str) -> Category | None:
    order = list(Category)
    found = [e.category for e in ev(text)]
    return max(found, key=order.index) if found else None


# --------------------------------------------------------------------------- benign


@pytest.mark.parametrize(
    "text",
    [
        "Hello, world!",
        "नमस्ते दुनिया",
        "નમસ્તે દુનિયા",
        "kal milte hain 😊",
        "aavjo, kem cho? 🙏\U0001f3fd",
        "Party tonight 🎉🎉🎉🥳🍕🍕",
    ],
)
def test_clean_and_code_mixed_text_has_no_findings_above_informational(text: str) -> None:
    w = worst(text)
    assert w in (None, Category.LEGITIMATE_STRUCTURE, Category.INFORMATIONAL)


@pytest.mark.parametrize(
    ("text", "subtype"),
    [
        ("\U0001f468\u200d\U0001f469\u200d\U0001f467", "zwj_sequence"),
        ("\U0001f44d\U0001f3fd", "modifier_sequence"),
        ("1\ufe0f\u20e3", "keycap_sequence"),
        ("\U0001f1ee\U0001f1f3", "flag_sequence"),
        ("\U0001f3f4\U000e0067\U000e0062\U000e0065\U000e006e\U000e0067\U000e007f", "tag_sequence"),
        ("❤\ufe0f", "presentation_sequence"),
    ],
)
def test_rgi_emoji_sequences_are_legitimate_structure(text: str, subtype: str) -> None:
    found = ev(text)
    assert [e.category for e in found] == [Category.LEGITIMATE_STRUCTURE]
    assert found[0].rule == "emoji.rgi_sequence"
    assert found[0].details["subtype"] == subtype
    assert (found[0].span.cp_start, found[0].span.cp_end) == (0, len(text))


@pytest.mark.parametrize(
    "text",
    [
        "क्\u200dष",  # Devanagari KA VIRAMA ZWJ SSA (half form)
        "क्\u200cष",  # Devanagari KA VIRAMA ZWNJ SSA (explicit virama)
        "ક્\u200cષ",  # Gujarati KA VIRAMA ZWNJ SSA
        "ક્\u200dષ",  # Gujarati KA VIRAMA ZWJ SSA
    ],
)
def test_indic_joiners_after_virama_are_legitimate(text: str) -> None:
    found = ev(text)
    assert [e.rule for e in found] == ["indic.joiner_after_virama"]
    assert found[0].category is Category.LEGITIMATE_STRUCTURE
    assert found[0].span.cp_start == 2


def test_bom_at_start_is_informational() -> None:
    found = ev("\ufeffhello")
    assert [(e.rule, e.category) for e in found] == [
        ("zero_width.leading_bom", Category.INFORMATIONAL)
    ]


# --------------------------------------------------------------------------- anomalous / suspicious


def test_zero_width_space_inside_word_is_suspicious_with_exact_location() -> None:
    found = ev("pass\u200bword")
    assert [(e.rule, e.category) for e in found] == [
        ("zero_width.inside_word", Category.SUSPICIOUS)
    ]
    assert (found[0].span.cp_start, found[0].span.cp_end) == (4, 5)


def test_zero_width_space_between_words_is_anomalous() -> None:
    assert ("zero_width.standalone", Category.ANOMALOUS) in {
        (e.rule, e.category) for e in ev("hello \u200b world")
    }


def test_zwj_inside_latin_word_is_anomalous_not_legitimate() -> None:
    found = ev("ig\u200dnore")
    assert [(e.rule, e.category) for e in found] == [("joiner.out_of_context", Category.ANOMALOUS)]


def test_bidi_override_in_ltr_text_is_suspicious() -> None:
    assert ("bidi.control_without_rtl", Category.SUSPICIOUS) in {
        (e.rule, e.category) for e in ev("access \u202eolleh\u202c granted")
    }


def test_unbalanced_bidi_is_suspicious_even_with_rtl_text() -> None:
    assert "bidi.unbalanced" in rules("שלום \u202b abc")


def test_balanced_isolate_in_rtl_text_is_informational() -> None:
    found = ev("שלום \u2067abc\u2069 עולם")
    assert {e.category for e in found} == {Category.INFORMATIONAL}


def test_unbalanced_detector_counts_pdi_as_closing_isolates() -> None:
    assert "bidi.unbalanced" not in rules("שלום \u2066x\u2069")


def test_control_character_is_anomalous() -> None:
    assert ("control.c0_c1", Category.ANOMALOUS) in {(e.rule, e.category) for e in ev("a\x07b")}


def test_styled_mathematical_letters_are_anomalous() -> None:
    found = [
        e
        for e in ev("\U0001d407\U0001d41e\U0001d425\U0001d425\U0001d428")
        if e.rule == "compat.styled_letters"
    ]
    assert len(found) == 1
    assert found[0].category is Category.ANOMALOUS
    assert found[0].details["nfkc"] == "Hello"


def test_mixed_script_word_with_lookalike_is_suspicious() -> None:
    # Cyrillic \u0430 (U+0430) inside a Latin word.
    found = [e for e in ev("login at p\u0430ypal now") if e.rule == "homoglyph.mixed_script_word"]
    assert len(found) == 1
    assert found[0].category is Category.SUSPICIOUS
    assert found[0].details["scripts"] == ["Cyrillic", "Latin"]
    assert (found[0].span.cp_start, found[0].span.cp_end) == (9, 15)


def test_whole_word_in_other_script_does_not_trigger_mixed_word() -> None:
    assert "homoglyph.mixed_script_word" not in rules("Hello \u043c\u0438\u0440")


def test_hinglish_and_devanagari_words_side_by_side_are_not_suspicious() -> None:
    assert worst("aaj मौसम acha hai") in (None, Category.INFORMATIONAL)


# --------------------------------------------------------------------------- concealed payloads


def test_tag_characters_outside_flag_decode_to_ascii() -> None:
    hidden = "".join(chr(0xE0000 + ord(c)) for c in "hi there")
    found = [e for e in ev("Nice day" + hidden) if e.category is Category.CONCEALED_PAYLOAD_DECODED]
    assert len(found) == 1
    assert found[0].rule == "tag.ascii_payload"
    assert found[0].details["decoded"] == "hi there"
    assert found[0].span.cp_start == 8


def test_variation_selector_byte_payload_decodes() -> None:
    def vs(b: int) -> str:
        return chr(0xFE00 + b) if b < 16 else chr(0xE0100 + b - 16)

    hidden = "".join(vs(b) for b in b"secret")
    found = [
        e for e in ev("\U0001f600" + hidden) if e.category is Category.CONCEALED_PAYLOAD_DECODED
    ]
    assert len(found) == 1
    assert found[0].rule == "variation_selector.byte_payload"
    assert found[0].details["decoded"] == "secret"
    assert found[0].span.cp_start == 1


def test_invalid_variation_selector_run_is_suspicious_but_not_decoded() -> None:
    hidden = "\ufe0f" * 1 + chr(0xE0100 + 0xFF - 16) * 3  # bytes 0x0F,0xFF,0xFF,0xFF: not UTF-8
    found = ev("x" + hidden)
    assert {e.rule for e in found} >= {"variation_selector.unrecognized_run"}
    assert all(e.category is not Category.CONCEALED_PAYLOAD_DECODED for e in found)


def test_evidence_is_sorted_and_ids_are_unique() -> None:
    text = "a\u200bb \u202ex\u202c " + "".join(chr(0xE0000 + ord(c)) for c in "zz")
    found = ev(text)
    assert [e.span.cp_start for e in found] == sorted(e.span.cp_start for e in found)
    assert len({e.id for e in found}) == len(found)
