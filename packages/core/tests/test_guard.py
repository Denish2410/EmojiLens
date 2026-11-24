"""EmojiGuard tests on constructed inputs and the synthetic benign fixture (not research data)."""

from __future__ import annotations

import pathlib

import pytest

from emojilens_core.datasets import parse_jsonl
from emojilens_core.eval.classification import Item, evaluate
from emojilens_core.guard import Ablation, Policy, Recommendation, assess, features
from emojilens_core.guard.baselines import (
    keyword_filter,
    nfkc_normalization,
    no_defence,
    strip_invisibles,
)
from emojilens_core.multilingual import Variety
from emojilens_core.transforms import REGISTRY
from emojilens_core.unicode import analyze

FIXTURE = (
    pathlib.Path(__file__).resolve().parents[3]
    / "datasets/fixtures/benign_controls.synthetic.jsonl"
)
BENIGN = [r.text for r in parse_jsonl(FIXTURE.read_bytes()).records]
GUJ = "ક્\u200cષ"


@pytest.mark.parametrize("text", BENIGN)
def test_benign_controls_are_allowed(text: str) -> None:
    a = assess(text)
    assert a.recommendation in (Recommendation.ALLOW, Recommendation.ALLOW_WITH_INFO)
    assert a.rule_score == 0.0


def test_concealed_payload_is_flagged_with_located_evidence() -> None:
    out = (
        REGISTRY["unicode_smuggling"]
        .apply("Nice day", Variety.EN, params={"method": "tag_payload"})
        .output
    )
    a = assess(out)
    assert a.recommendation is Recommendation.FLAG
    tag = next(c for c in a.contributions if c.name == "tag.ascii_payload")
    assert tag.evidence_ids
    assert "decoded" in a.relevant_views


def test_block_only_when_policy_enables_it() -> None:
    out = (
        REGISTRY["unicode_smuggling"]
        .apply("Nice day", Variety.EN, params={"method": "tag_payload"})
        .output
    )
    assert assess(out).recommendation is not Recommendation.BLOCK
    strict = Policy(block_enabled=True, block_threshold=0.85)
    assert assess(out, policy=strict).recommendation is Recommendation.BLOCK


def test_indic_awareness_ablation_shows_false_positive_risk() -> None:
    assert assess(GUJ).rule_score == 0.0
    naive = assess(GUJ, ablation=Ablation(indic_aware=False))
    assert naive.rule_score is not None
    assert naive.rule_score > 0
    assert naive.ablation == "without_indic_aware"


def test_decoder_ablation_lowers_payload_weight() -> None:
    out = (
        REGISTRY["unicode_smuggling"]
        .apply("Nice day", Variety.EN, params={"method": "tag_payload"})
        .output
    )
    full, nodec = assess(out), assess(out, ablation=Ablation(decoders=False))
    assert full.rule_score is not None
    assert nodec.rule_score is not None
    assert nodec.rule_score < full.rule_score


def test_rules_off_without_detector_gives_no_score() -> None:
    a = assess("p\u0430ypal", ablation=Ablation(rules=False))
    assert a.rule_score is None
    assert a.risk_score == 0.0
    assert "no trained detector" in " ".join(a.notes)


def test_baselines() -> None:
    assert no_defence("x")[0] is False
    assert strip_invisibles("a\u200bb")[0] is True
    assert strip_invisibles(GUJ)[0] is True  # the naive sanitizer flags legitimate Gujarati
    assert nfkc_normalization("\uff28i")[0] is True
    kw = keyword_filter(("password",))
    assert kw("reset your password")[0] is True
    assert kw("reset your pass\u200bword")[0] is False  # evaded by a zero-width split


def test_learned_detector_trains_and_explains() -> None:
    pytest.importorskip("sklearn")
    from emojilens_core.guard.detector import train

    pos = [
        REGISTRY["unicode_smuggling"].apply(t, Variety.EN, seed=i, params={"rate": 1.0}).output
        for i, t in enumerate(BENIGN)
    ]
    rows = [(features(analyze(t)), 0) for t in BENIGN] + [(features(analyze(t)), 1) for t in pos]
    det = train(rows, seed=0)
    a = assess(pos[0], detector=det)
    assert a.detector_score is not None
    assert a.detector_version is not None
    assert any(c.source == "detector" for c in a.contributions)
    with pytest.raises(ValueError, match="both positive and negative"):
        train(rows[:3])


def test_detector_artifact_hash_is_verified(tmp_path: pathlib.Path) -> None:
    pytest.importorskip("sklearn")
    from emojilens_core.guard.detector import load, save, train

    rows = [(features(analyze("hello")), 0), (features(analyze("he\u200bllo")), 1)] * 3
    det = train(rows)
    path = tmp_path / "d.joblib"
    sha = save(det, path, {"note": "test"})
    assert load(path, sha).version == det.version
    with pytest.raises(ValueError, match="hash mismatch"):
        load(path, "0" * 64)


def test_classification_metrics_hand_computed() -> None:
    items = [
        Item("a", "g1", 1, 1, 0.9),
        Item("b", "g2", 1, 0, 0.2),
        Item("c", "g3", 0, 1, 0.7),
        Item("d", "g4", 0, 0, 0.1),
    ]
    m = evaluate(items, resamples=200)
    assert (m.tp, m.fp, m.tn, m.fn) == (1, 1, 1, 1)
    assert m.precision == pytest.approx(0.5)
    assert m.recall == pytest.approx(0.5)
    assert m.f1 == pytest.approx(0.5)
    assert m.fpr == pytest.approx(0.5)
    assert m.false_positives == ["c"]
    assert m.false_negatives == ["b"]
