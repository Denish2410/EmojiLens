from __future__ import annotations

import pytest

from emojilens_core.unicode.scripts import has_latin_lookalike, script_of, script_profile


@pytest.mark.parametrize(
    ("char", "script"),
    [
        ("a", "Latin"),
        ("\u0430", "Cyrillic"),
        ("\u03b1", "Greek"),
        ("क", "Devanagari"),
        ("ક", "Gujarati"),
        ("्", "Devanagari"),
        ("1", "Common"),
        ("́", "Inherited"),
        ("\U0001f600", "Common"),
    ],
)
def test_script_of(char: str, script: str) -> None:
    assert script_of(char) == script


def test_latin_lookalikes() -> None:
    assert has_latin_lookalike("\u0430")  # Cyrillic a
    assert has_latin_lookalike("\u03bf")  # Greek omicron
    assert not has_latin_lookalike("क")  # Devanagari KA


def test_script_profile_counts_letters_only_and_finds_dominant() -> None:
    p = script_profile("aaj मौसम acha hai 123 😊")
    assert p.counts["Latin"] == 10
    assert p.counts["Devanagari"] >= 3
    assert "Common" not in p.counts
    assert p.dominant == "Latin"
    assert p.is_mixed is True
