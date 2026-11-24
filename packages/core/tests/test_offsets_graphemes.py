import pytest
from hypothesis import given
from hypothesis import strategies as st

from emojilens_core.unicode import OffsetTable, analyze, segment_graphemes

scalar_text = st.text(alphabet=st.characters(codec="utf-8"), max_size=200)


def utf16_len(s: str) -> int:
    return len(s.encode("utf-16-le")) // 2


@given(scalar_text)
def test_graphemes_reconstruct_original(text: str) -> None:
    assert "".join(g.text for g in segment_graphemes(text)) == text


@given(scalar_text)
def test_spans_agree_with_encoders(text: str) -> None:
    table = OffsetTable.build(text)
    for g in segment_graphemes(text, table):
        s = g.span
        assert text[s.cp_start : s.cp_end] == g.text
        assert text.encode("utf-8")[s.utf8_start : s.utf8_end] == g.text.encode("utf-8")
        assert s.utf16_start == utf16_len(text[: s.cp_start])
        assert s.utf16_end - s.utf16_start == utf16_len(g.text)


@given(scalar_text)
def test_utf16_roundtrip(text: str) -> None:
    table = OffsetTable.build(text)
    for i in range(len(text) + 1):
        assert table.cp_from_utf16(table.utf16[i]) == i


def test_utf16_offset_inside_surrogate_pair_rejected() -> None:
    table = OffsetTable.build("a\U0001f600")
    with pytest.raises(ValueError, match="not a code point boundary"):
        table.cp_from_utf16(2)


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        # Family ZWJ sequence is one grapheme
        ("\U0001f468\u200d\U0001f469\u200d\U0001f467", 1),
        # Thumbs up + skin tone modifier
        ("\U0001f44d\U0001f3fd", 1),
        # Keycap one: 1 + VS16 + U+20E3
        ("1\ufe0f\u20e3", 1),
        # Flag of India: regional indicators I + N
        ("\U0001f1ee\U0001f1f3", 1),
        # Subdivision flag (England): black flag + tag sequence
        ("\U0001f3f4\U000e0067\U000e0062\U000e0065\U000e006e\U000e0067\U000e007f", 1),
        # Red heart with emoji presentation selector
        ("❤\ufe0f", 1),
    ],
)
def test_emoji_sequences_are_single_graphemes(text: str, expected: int) -> None:
    assert len(segment_graphemes(text)) == expected


def test_devanagari_conjunct_with_zwj_preserved() -> None:
    # क्\u200dष : KA + VIRAMA + ZWJ + SSA — legitimate half-form request.
    text = "क्\u200dष"
    result = analyze(text)
    assert result.original == text
    joined = "".join(g.text for g in result.graphemes)
    assert joined == text
    zwj = [c for c in result.codepoints if c.codepoint == "U+200D"]
    assert len(zwj) == 1
    assert "joiner" in zwj[0].kinds


def test_gujarati_with_zwnj_preserved() -> None:
    # ક્\u200cષ : Gujarati KA + VIRAMA + ZWNJ + SSA
    text = "ક્\u200cષ"
    result = analyze(text)
    assert result.original == text
    assert result.lengths.codepoints == 4
    assert any(c.codepoint == "U+200C" for c in result.codepoints)


def test_analysis_lengths_and_normalization() -> None:
    text = "é\U0001f600"
    result = analyze(text)
    assert result.lengths.codepoints == 3
    assert result.lengths.graphemes == 2
    assert result.lengths.utf8_bytes == len(text.encode("utf-8"))
    assert result.lengths.utf16_units == 4
    assert result.normalization.is_nfc is False
    assert result.normalization.is_nfd is True


def test_invisible_markers_are_descriptive_not_verdicts() -> None:
    text = "a\u200bb\u202ec\U000e0041"
    result = analyze(text)
    kinds = {c.codepoint: c.kinds for c in result.codepoints}
    assert "zero_width" in kinds["U+200B"]
    assert "bidi_control" in kinds["U+202E"]
    assert "tag" in kinds["U+E0041"]
    assert result.invisible_count == 3


def test_unnamed_control_gets_label() -> None:
    result = analyze("\x07")
    assert result.codepoints[0].name == "<control-0007>"
    assert "control" in result.codepoints[0].kinds
