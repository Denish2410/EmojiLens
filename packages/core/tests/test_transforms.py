from __future__ import annotations

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from emojilens_core.multilingual import Variety
from emojilens_core.transforms import (
    FAMILIES,
    REGISTRY,
    ChainStep,
    TransformError,
    compose,
    decode_payload,
    run_chain,
    tiles,
)
from emojilens_core.unicode import analyze

TEXT = "Today the weather is very good, my friend \U0001f468\u200d\U0001f469\u200d\U0001f467"
scalar_text = st.text(alphabet=st.characters(codec="utf-8"), max_size=60)


def test_registry_has_identity_and_six_families() -> None:
    assert set(FAMILIES) == {s.spec.family for s in REGISTRY.values()} - {"identity"}
    assert len(FAMILIES) == 6
    for t in REGISTRY.values():
        assert t.spec.version
        assert t.spec.description
        assert t.spec.varieties


@settings(max_examples=60, deadline=None)
@given(
    scalar_text,
    st.integers(0, 10_000),
    st.sampled_from(sorted(REGISTRY)),
    st.sampled_from(list(Variety)),
)
def test_every_transform_is_deterministic_and_tiles(
    text: str, seed: int, tid: str, v: Variety
) -> None:
    a = REGISTRY[tid].apply(text, v, seed=seed)
    b = REGISTRY[tid].apply(text, v, seed=seed)
    assert a.output == b.output
    assert a.provenance == b.provenance
    assert tiles(a.pieces, len(text))
    assert "".join(p[2] for p in a.pieces) == a.output
    assert a.validation.checks["output_well_formed"]
    assert a.input == text


def test_identity_is_perfectly_consistent() -> None:
    r = REGISTRY["identity"].apply(TEXT, Variety.EN, seed=99)
    assert r.output == TEXT
    assert r.validation.valid
    assert r.edits == 0


def test_seed_changes_output_for_seeded_transforms() -> None:
    outs = {REGISTRY["homoglyph"].apply(TEXT, Variety.EN, seed=s).output for s in range(5)}
    assert len(outs) > 1


@pytest.mark.parametrize("method", ["tag_payload", "variation_selector_payload"])
def test_smuggled_payload_round_trips_and_is_detected(method: str) -> None:
    r = REGISTRY["unicode_smuggling"].apply(TEXT, Variety.EN, seed=1, params={"method": method})
    assert r.validation.checks["round_trip"] is True
    assert decode_payload(r.output) == "SURROGATE-TOKEN"
    rules = {e.rule for e in analyze(r.output).evidence}
    assert rules & {"tag.ascii_payload", "variation_selector.byte_payload"}


def test_zero_width_split_is_flagged_by_evidence() -> None:
    r = REGISTRY["unicode_smuggling"].apply(
        "password reset", Variety.EN, seed=2, params={"rate": 1.0}
    )
    assert r.output != "password reset"
    assert "zero_width.inside_word" in {e.rule for e in analyze(r.output).evidence}


def test_bidi_reorder_wraps_words() -> None:
    r = REGISTRY["unicode_smuggling"].apply(
        "access granted now", Variety.EN, seed=0, params={"method": "bidi_reorder", "rate": 1.0}
    )
    assert "\u202e" in r.output
    assert "bidi.control_without_rtl" in {e.rule for e in analyze(r.output).evidence}


def test_emoji_substitution_uses_only_emoji() -> None:
    import emoji

    r = REGISTRY["emoji_substitution"].apply(TEXT, Variety.EN, seed=1, params={"rate": 1.0})
    assert r.edits >= 2
    for rep in r.provenance["replaced"]:
        assert emoji.is_emoji(rep["emoji"])


def test_emoji_substitution_gu_latn_is_unsupported_noop() -> None:
    r = REGISTRY["emoji_substitution"].apply("tame kem cho", Variety.GU_LATN, seed=1)
    assert r.output == "tame kem cho"
    assert any("not a supported variety" in n for n in r.validation.notes)


@pytest.mark.parametrize("scheme", ["keyed_emoji", "regional_indicator", "squared_letters"])
def test_cipher_round_trips_up_to_case(scheme: str) -> None:
    r = REGISTRY["emoji_cipher"].apply(
        "Meet at Nine", Variety.EN, seed=4, params={"scheme": scheme}
    )
    assert r.validation.checks["round_trip"] is True
    assert r.validation.valid


def test_regional_indicator_cipher_does_not_form_flags() -> None:
    r = REGISTRY["emoji_cipher"].apply(
        "in", Variety.EN, seed=0, params={"scheme": "regional_indicator"}
    )
    assert not any(e.details.get("subtype") == "flag_sequence" for e in analyze(r.output).evidence)


def test_homoglyph_latin_output_is_flagged_mixed_script() -> None:
    r = REGISTRY["homoglyph"].apply("paypal", Variety.EN, seed=3, params={"rate": 0.5})
    assert r.output != "paypal"
    rules = {e.rule for e in analyze(r.output).evidence}
    assert rules & {"homoglyph.mixed_script_word", "homoglyph.whole_script_confusable"}


def test_homoglyph_covers_devanagari_gujarati_pairs() -> None:
    r = REGISTRY["homoglyph"].apply("कुछ", Variety.HI, seed=0, params={"rate": 1.0})
    assert r.output == "कુछ"


@pytest.mark.parametrize(
    "method", ["leetspeak", "bold", "fullwidth", "case_noise", "separator_insertion", "char_repeat"]
)
def test_obfuscation_methods(method: str) -> None:
    r = REGISTRY["text_obfuscation"].apply(
        "secret code", Variety.EN, seed=5, params={"method": method, "rate": 1.0}
    )
    assert r.output != "secret code"
    assert r.validation.valid


def test_styled_obfuscation_is_detected() -> None:
    r = REGISTRY["text_obfuscation"].apply(
        "hello", Variety.EN, seed=0, params={"method": "bold", "rate": 1.0}
    )
    found = [e for e in analyze(r.output).evidence if e.rule == "compat.styled_letters"]
    assert found
    assert found[0].details["nfkc"] == "hello"


def test_code_mixing_swaps_concepts_and_keeps_offsets() -> None:
    r = REGISTRY["code_mixing"].apply(
        "Today is good", Variety.EN, seed=0, params={"target": "gu", "rate": 1.0}
    )
    assert r.output == "આજે is સારું"
    assert (0, 5, "આજે") in r.pieces


def test_params_are_validated() -> None:
    t = REGISTRY["homoglyph"]
    with pytest.raises(TransformError, match="Unknown parameter"):
        t.apply("x", Variety.EN, params={"nope": 1})
    with pytest.raises(TransformError, match=r"<= 1\.0"):
        t.apply("x", Variety.EN, params={"rate": 2})
    with pytest.raises(TransformError, match="must be one of"):
        REGISTRY["text_obfuscation"].apply("x", Variety.EN, params={"method": "rot13"})
    with pytest.raises(TransformError, match="surrogate"):
        t.apply("a\ud800", Variety.EN)


def test_chain_is_reproducible_and_maps_to_original() -> None:
    chain = [
        ChainStep("code_mixing", {"target": "hi-Latn", "rate": 1.0}),
        ChainStep("emoji_substitution", {"rate": 1.0}),
        ChainStep("unicode_smuggling", {"rate": 0.5}),
    ]
    a = run_chain(REGISTRY, TEXT, Variety.EN, chain, seed=3)
    b = run_chain(REGISTRY, TEXT, Variety.EN, chain, seed=3)
    assert a.output == b.output
    assert a.chain_hash == b.chain_hash
    assert a.valid
    assert tiles(a.pieces, len(TEXT))
    assert "".join(p[2] for p in a.pieces) == a.output
    c = run_chain(REGISTRY, TEXT, Variety.EN, chain, seed=4)
    assert c.chain_hash != a.chain_hash


def test_chain_limits() -> None:
    with pytest.raises(TransformError, match="at least one"):
        run_chain(REGISTRY, "x", Variety.EN, [])
    with pytest.raises(TransformError, match="Unknown transformation"):
        run_chain(REGISTRY, "x", Variety.EN, [ChainStep("nope")])


@settings(max_examples=80, deadline=None)
@given(
    scalar_text,
    st.lists(st.sampled_from(sorted(REGISTRY)), min_size=1, max_size=4),
    st.integers(0, 50),
)
def test_composed_chains_always_tile(text: str, ids: list[str], seed: int) -> None:
    r = run_chain(REGISTRY, text, Variety.EN, [ChainStep(i) for i in ids], seed=seed)
    assert tiles(r.pieces, len(text))
    assert "".join(p[2] for p in r.pieces) == r.output


def test_compose_handles_deletions_and_insertions() -> None:
    first = [(0, 1, "a"), (1, 2, ""), (2, 3, "c")]  # delete original index 1
    second = [(0, 1, "A"), (1, 1, "+"), (1, 2, "C")]  # insert before mid index 1
    out = compose(first, second)
    assert tiles(out, 3)
    assert "".join(p[2] for p in out) == "A+C"
