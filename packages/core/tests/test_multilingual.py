from __future__ import annotations

import pytest

from emojilens_core.multilingual import Variety, cldr_version, identify, meaning


@pytest.mark.parametrize(
    ("text", "label"),
    [
        ("Are you coming to the party tonight?", Variety.EN),
        ("kal milte hain, tum kya kar rahe ho?", Variety.HI_LATN),
        ("tame kem cho? hu majama chhu", Variety.GU_LATN),
        ("आज मौसम बहुत अच्छा है", Variety.HI),
        ("આજે હવામાન ખૂબ સરસ છે", Variety.GU),
    ],
)
def test_identifies_each_variety(text: str, label: Variety) -> None:
    result = identify(text)
    assert result.label is label
    assert result.method.startswith("script+lexicon/")


def test_unknown_latin_text_is_uncertain_not_guessed() -> None:
    result = identify("xyzzy plugh")
    assert result.label is None
    assert result.uncertain
    assert "no identifiable tokens" in result.reasons


def test_short_input_records_thin_evidence() -> None:
    result = identify("hai")
    assert result.label is Variety.HI_LATN
    assert result.uncertain
    assert any("thin evidence" in r for r in result.reasons)


def test_ambiguous_tokens_split_mass_and_are_not_forced() -> None:
    result = identify("to")
    tag = result.tokens[0]
    assert tag.tag == "ambiguous"
    assert set(tag.candidates) == {"hi-Latn", "gu-Latn"}


def test_code_mixing_index_and_switch_points() -> None:
    result = identify("aaj मौसम bahut अच्छा hai")
    assert result.code_mixed
    assert result.switch_points == 4
    assert 0 < result.cmi < 100


def test_monolingual_text_has_zero_cmi() -> None:
    result = identify("आज मौसम बहुत अच्छा है")
    assert result.cmi == 0
    assert not result.code_mixed


def test_emoji_tokens_are_language_independent() -> None:
    result = identify("tame kem cho \U0001f60a")
    assert [t.tag for t in result.tokens][-1] == "emoji"
    assert result.label is Variety.GU_LATN


def test_cldr_meanings_in_supported_locales() -> None:
    assert cldr_version().startswith("49")
    en = meaning("\U0001f44d", Variety.EN)
    hi = meaning("\U0001f44d", Variety.HI)
    gu = meaning("\U0001f44d", Variety.GU)
    assert en is not None
    assert en.name == "thumbs up"
    assert not en.fallback
    assert hi is not None
    assert hi.locale == "hi"
    assert gu is not None
    assert gu.locale == "gu"


def test_gu_latn_falls_back_explicitly() -> None:
    m = meaning("\U0001f44d", Variety.GU_LATN)
    assert m is not None
    assert m.fallback
    assert m.locale == "gu"


def test_skin_tone_sequence_uses_derived_annotations() -> None:
    m = meaning("\U0001f44d\U0001f3fd", Variety.EN)
    assert m is not None
    assert "medium skin tone" in m.name


def test_non_emoji_has_no_meaning() -> None:
    assert meaning("x", Variety.EN) is None
