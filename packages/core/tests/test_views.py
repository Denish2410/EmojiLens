"""Derived views must be reversible: every view segment maps back to original offsets."""

from __future__ import annotations

import unicodedata

from hypothesis import given, settings
from hypothesis import strategies as st

from emojilens_core.unicode import analyze
from emojilens_core.unicode.views import DerivedView

scalar_text = st.text(alphabet=st.characters(codec="utf-8"), max_size=80)


def view(text: str, name: str) -> DerivedView:
    return next(v for v in analyze(text).views if v.name == name)


def test_view_names_are_complete_and_original_is_identity() -> None:
    views = analyze("x").views
    assert [v.name for v in views] == [
        "original",
        "nfc",
        "nfkc",
        "sanitized",
        "demojized",
        "decoded",
    ]
    assert views[0].text == "x"


@settings(max_examples=150)
@given(scalar_text)
def test_segments_cover_original_and_reconstruct_view(text: str) -> None:
    for v in analyze(text).views:
        assert "".join(s.text for s in v.segments) == v.text
        # Segments tile the original without gaps or overlaps.
        pos = 0
        for s in v.segments:
            assert s.original.cp_start == pos
            pos = s.original.cp_end
        assert pos == len(text)
        # View offsets are consistent with segment text.
        for s in v.segments:
            assert v.text[s.view.cp_start : s.view.cp_end] == s.text


@settings(max_examples=150)
@given(scalar_text)
def test_normalized_views_equal_whole_string_normalization(text: str) -> None:
    assert view(text, "nfc").text == unicodedata.normalize("NFC", text)
    assert view(text, "nfkc").text == unicodedata.normalize("NFKC", text)


def test_sanitized_keeps_legitimate_joiners_and_removes_concealment() -> None:
    family = "\U0001f468\u200d\U0001f469\u200d\U0001f467"
    gujarati = "ક્\u200cષ"
    text = f"pass\u200bword {family} {gujarati}\u202e"
    sanitized = view(text, "sanitized")
    assert sanitized.text == f"password {family} {gujarati}"
    removed = [
        s for s in sanitized.segments if s.text == "" and s.original.cp_end > s.original.cp_start
    ]
    assert {text[s.original.cp_start] for s in removed} == {"\u200b", "\u202e"}


def test_demojized_maps_emoji_back_to_original_span() -> None:
    text = "ok \U0001f44d\U0001f3fd!"
    d = view(text, "demojized")
    assert d.text == "ok :thumbs_up_medium_skin_tone:!"
    seg = next(s for s in d.segments if s.text.startswith(":"))
    assert (seg.original.cp_start, seg.original.cp_end) == (3, 5)


def test_decoded_view_reveals_tag_payload_in_place() -> None:
    hidden = "".join(chr(0xE0000 + ord(c)) for c in "run")
    d = view("hi" + hidden + "!", "decoded")
    assert d.text == "hi⟦run⟧!"


def test_original_view_never_changes_input() -> None:
    text = " \u200b é "
    assert view(text, "original").text == text
    assert analyze(text).original == text
