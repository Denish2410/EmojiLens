"""EmojiGuard: explainable defence over Unicode evidence, derived views and a learned detector.

Rule weights are hand-set (documented, not learned) and the combined score is UNVALIDATED.
Detector scores are uncalibrated and are never presented as probabilities. Legitimate structure
(RGI emoji, Indic and Arabic joiners) contributes nothing, so multilingual text is not penalised.
"""

from __future__ import annotations

import hashlib
import time
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any, Protocol

from emojilens_core.unicode import analyze
from emojilens_core.unicode.analysis import UnicodeAnalysis
from emojilens_core.unicode.evidence import Category

GUARD_VERSION = "0.1.0"

# Hand-set weights per evidence rule (v0.1). Unlisted rules weigh 0.
RULE_WEIGHTS: dict[str, float] = {
    "tag.ascii_payload": 0.9,
    "variation_selector.byte_payload": 0.9,
    "tag.unrecognized_run": 0.6,
    "variation_selector.unrecognized_run": 0.6,
    "bidi.control_without_rtl": 0.6,
    "bidi.unbalanced": 0.5,
    "zero_width.inside_word": 0.5,
    "homoglyph.mixed_script_word": 0.6,
    "homoglyph.whole_script_confusable": 0.5,
    "compat.styled_letters": 0.35,
    "joiner.out_of_context": 0.3,
    "zero_width.standalone": 0.2,
    "variation_selector.unexpected": 0.2,
    "filler.out_of_context": 0.3,
    "control.c0_c1": 0.2,
    "script.mixed_word": 0.1,
}
DECODER_RULES = {"tag.ascii_payload", "variation_selector.byte_payload"}
FEATURES = (
    "n_legitimate",
    "n_informational",
    "n_anomalous",
    "n_suspicious",
    "n_concealed",
    "invisible_ratio",
    "emoji_ratio",
    "nfkc_changed",
    "sanitized_changed",
    "mixed_script_words",
    "styled_letters",
    "bidi_controls",
    "zero_width_in_word",
    "length_log",
)


class Recommendation(StrEnum):
    ALLOW = "allow"
    ALLOW_WITH_INFO = "allow_with_information"
    REVIEW = "request_review"
    FLAG = "flag_suspicious_transformation"
    BLOCK = "block_by_policy"


@dataclass(frozen=True, slots=True)
class Policy:
    review_threshold: float = 0.3
    flag_threshold: float = 0.6
    block_enabled: bool = False
    block_threshold: float = 0.9


@dataclass(frozen=True, slots=True)
class Ablation:
    """Component switches for ablation studies (all on = full EmojiGuard)."""

    rules: bool = True
    detector: bool = True
    decoders: bool = True
    view_rescoring: bool = True
    indic_aware: bool = True

    def name(self) -> str:
        off = [
            k
            for k in ("rules", "detector", "decoders", "view_rescoring", "indic_aware")
            if not getattr(self, k)
        ]
        return "full" if not off else "without_" + "+".join(off)


class Detector(Protocol):
    version: str

    def score(self, features: dict[str, float]) -> tuple[float, dict[str, float]]: ...


@dataclass(frozen=True, slots=True)
class Contribution:
    source: str  # "rule" | "view_rescoring" | "detector"
    name: str
    weight: float
    evidence_ids: tuple[str, ...] = ()
    detail: str = ""


@dataclass(frozen=True, slots=True)
class Assessment:
    input_sha256: str
    guard_version: str
    ablation: str
    evidence: list[dict[str, Any]]
    indicators: dict[str, float]
    rule_score: float | None
    detector_score: float | None
    detector_version: str | None
    risk_score: float
    uncertainty: str
    contributions: list[Contribution]
    explanation: list[str]
    recommendation: Recommendation
    relevant_views: list[str]
    latency_ms: float
    notes: list[str] = field(default_factory=list)


def features(a: UnicodeAnalysis) -> dict[str, float]:
    import math

    cats = [e.category for e in a.evidence]
    rules = [e.rule for e in a.evidence]
    n = max(1, a.lengths.codepoints)
    views = {v.name: v for v in a.views}
    emoji_cp = sum(1 for c in a.codepoints if c.category == "So")
    return {
        "n_legitimate": float(cats.count(Category.LEGITIMATE_STRUCTURE)),
        "n_informational": float(cats.count(Category.INFORMATIONAL)),
        "n_anomalous": float(cats.count(Category.ANOMALOUS)),
        "n_suspicious": float(cats.count(Category.SUSPICIOUS)),
        "n_concealed": float(cats.count(Category.CONCEALED_PAYLOAD_DECODED)),
        "invisible_ratio": a.invisible_count / n,
        "emoji_ratio": emoji_cp / n,
        "nfkc_changed": float(views["nfkc"].changed),
        "sanitized_changed": float(views["sanitized"].changed),
        "mixed_script_words": float(sum(r.startswith(("homoglyph.", "script.")) for r in rules)),
        "styled_letters": float(rules.count("compat.styled_letters")),
        "bidi_controls": float(sum(r.startswith("bidi.") and r != "bidi.mark" for r in rules)),
        "zero_width_in_word": float(rules.count("zero_width.inside_word")),
        "length_log": math.log1p(a.lengths.codepoints),
    }


def _combine(weights: list[float]) -> float:
    """Noisy-OR: 1 - prod(1 - w). Monotone, bounded, order-independent."""
    p = 1.0
    for w in weights:
        p *= 1 - max(0.0, min(1.0, w))
    return 1 - p


def assess(
    text: str,
    *,
    policy: Policy | None = None,
    ablation: Ablation | None = None,
    detector: Detector | None = None,
) -> Assessment:
    start = time.perf_counter()
    policy = policy or Policy()
    ab = ablation or Ablation()
    a = analyze(text)
    notes: list[str] = []
    contributions: list[Contribution] = []
    evidence = list(a.evidence)
    if not ab.indic_aware:
        notes.append("ablation: Indic/Arabic joiners treated as out-of-context joiners")
    for e in evidence:
        rule = e.rule
        if not ab.indic_aware and rule in ("indic.joiner_after_virama", "arabic.zwnj"):
            rule = "joiner.out_of_context"
        w = RULE_WEIGHTS.get(rule, 0.0)
        if not ab.decoders and rule in DECODER_RULES:
            rule, w = "invisible.unexplained_run", 0.3
        if ab.rules and w > 0:
            contributions.append(Contribution("rule", rule, w, (e.id,), e.message))
    if ab.view_rescoring and ab.rules:
        decoded = next(v for v in a.views if v.name == "decoded")
        if decoded.changed:
            nested = [
                e
                for e in analyze(decoded.text).evidence
                if e.category is Category.CONCEALED_PAYLOAD_DECODED
            ]
            if nested:
                contributions.append(
                    Contribution(
                        "view_rescoring",
                        "decoded_view.nested_payload",
                        0.5,
                        tuple(e.id for e in nested),
                        "Decoded view still contains concealed content.",
                    )
                )
        nfkc = next(v for v in a.views if v.name == "nfkc")
        if nfkc.changed:
            homo = [e for e in analyze(nfkc.text).evidence if e.rule.startswith("homoglyph.")]
            if homo:
                contributions.append(
                    Contribution(
                        "view_rescoring",
                        "nfkc_view.homoglyph",
                        0.3,
                        tuple(e.id for e in homo),
                        "Look-alike letters persist after NFKC.",
                    )
                )
    rule_score = _combine([c.weight for c in contributions]) if ab.rules else None
    det_score: float | None = None
    det_version: str | None = None
    if ab.detector and detector is not None:
        det_score, coef = detector.score(features(a))
        det_version = detector.version
        top = sorted(coef.items(), key=lambda kv: -abs(kv[1]))[:3]
        contributions.append(
            Contribution(
                "detector",
                "learned_detector",
                det_score,
                (),
                ", ".join(f"{k} {v:+.2f}" for k, v in top),
            )
        )
    elif ab.detector:
        notes.append("no trained detector loaded; rules only")
    scores = [s for s in (rule_score, det_score) if s is not None]
    risk = max(scores) if scores else 0.0
    if rule_score is not None and det_score is not None:
        gap = abs(rule_score - det_score)
        uncertainty = (
            "low (rules and detector agree)" if gap < 0.25 else "high (rules and detector disagree)"
        )
    else:
        uncertainty = "unquantified (single component)"
    has_info = any(
        e.category in (Category.INFORMATIONAL, Category.LEGITIMATE_STRUCTURE) for e in evidence
    )
    if policy.block_enabled and risk >= policy.block_threshold:
        rec = Recommendation.BLOCK
    elif risk >= policy.flag_threshold:
        rec = Recommendation.FLAG
    elif risk >= policy.review_threshold:
        rec = Recommendation.REVIEW
    else:
        rec = Recommendation.ALLOW_WITH_INFO if has_info else Recommendation.ALLOW
    explanation = [
        f"{c.name} ({c.source}, weight {c.weight:.2f}): {c.detail}" for c in contributions
    ]
    if not explanation:
        explanation = [
            "No risk-bearing evidence. Legitimate structure and informational findings "
            "carry no weight."
        ]
    relevant = [v.name for v in a.views if v.changed and v.name != "original"]
    return Assessment(
        input_sha256=hashlib.sha256(text.encode()).hexdigest(),
        guard_version=GUARD_VERSION,
        ablation=ab.name(),
        evidence=[
            {
                "id": e.id,
                "rule": e.rule,
                "category": e.category.value,
                "cp_start": e.span.cp_start,
                "cp_end": e.span.cp_end,
                "utf16_start": e.span.utf16_start,
                "utf16_end": e.span.utf16_end,
                "message": e.message,
            }
            for e in evidence
        ],
        indicators=features(a),
        rule_score=None if rule_score is None else round(rule_score, 4),
        detector_score=None if det_score is None else round(det_score, 4),
        detector_version=det_version,
        risk_score=round(risk, 4),
        uncertainty=uncertainty,
        contributions=contributions,
        explanation=explanation,
        recommendation=rec,
        relevant_views=relevant,
        latency_ms=round((time.perf_counter() - start) * 1000, 3),
        notes=notes,
    )
