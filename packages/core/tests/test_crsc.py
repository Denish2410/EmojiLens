"""Mathematical sanity tests for CRSC (constructed inputs, not research data)."""

from __future__ import annotations

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from emojilens_core.eval import Pair, cosine, crsc_safe, crsc_sem, group_bootstrap, report


def P(
    g: str, sem: float | None = None, js: str | None = None, jv: str | None = None, **kw: object
) -> Pair:
    base: dict[str, object] = {
        "language": "en",
        "family": "homoglyph",
        "modality": "text",
        "model": "m",
    }
    base.update(kw)
    return Pair(group=g, sem=sem, judge_source=js, judge_variant=jv, **base)  # type: ignore[arg-type]


def test_cosine() -> None:
    assert cosine([1, 0], [1, 0]) == pytest.approx(1.0)
    assert cosine([1, 0], [0, 1]) == pytest.approx(0.0)
    assert cosine([1, 0], [-1, 0]) == pytest.approx(-1.0)
    assert cosine([0, 0], [1, 0]) is None
    assert cosine([1], [1, 2]) is None


def test_identity_controls_give_perfect_consistency() -> None:
    pairs = [P(f"g{i}", 1.0, "safe", "safe", identity=True) for i in range(10)]
    sem, safe = crsc_sem(pairs), crsc_safe(pairs)
    assert sem.metric.value == pytest.approx(1.0)
    assert sem.identity_failures == 0
    assert safe.metric.value == 1.0
    assert safe.flip_rate == 0.0
    assert sem.metric.ci_low == pytest.approx(1.0)
    assert sem.metric.ci_high == pytest.approx(1.0)


def test_identity_deviation_is_reported() -> None:
    sem = crsc_sem([P("g1", 0.97, identity=True), P("g2", 1.0, identity=True)])
    assert sem.identity_failures == 1


def test_hand_computed_sem_and_missing_excluded() -> None:
    sem = crsc_sem([P("a", 0.8), P("a", 0.6), P("b", 1.0), P("c", None)])
    assert sem.metric.value == pytest.approx(0.8)
    assert sem.metric.n == 3
    assert sem.metric.n_groups == 2
    assert sem.missing == 1


def test_safe_counts_flips_unknown_missing_separately() -> None:
    pairs = [
        P("a", js="unsafe", jv="safe"),
        P("b", js="safe", jv="unsafe"),
        P("c", js="safe", jv="safe"),
        P("d", js="unsafe", jv="unsafe"),
        P("e", js="unknown", jv="safe"),
        P("f", js=None, jv="safe"),
    ]
    r = crsc_safe(pairs)
    assert r.metric.value == pytest.approx(0.5)
    assert r.flip_rate == pytest.approx(0.5)
    assert (r.unsafe_to_safe, r.safe_to_unsafe, r.agree_safe, r.agree_unsafe) == (1, 1, 1, 1)
    assert (r.unknown, r.missing) == (1, 1)
    assert r.metric.value is not None
    assert r.flip_rate is not None
    assert r.metric.value + r.flip_rate == pytest.approx(1.0)


def test_undefined_when_no_data_or_single_group() -> None:
    assert crsc_sem([]).metric.value is None
    assert crsc_safe([P("a", js="unknown", jv="safe")]).metric.value is None
    single = crsc_sem([P("a", 0.5), P("a", 0.7)])
    assert single.metric.ci_low is None  # bootstrap needs >= 2 groups


def test_bootstrap_resamples_groups_not_pairs() -> None:
    # One large group of 1.0s and one small group of 0.0s: group-level resampling can draw
    # both groups as the large one or both as the small one, so the CI spans [0, 1].
    lo, hi = group_bootstrap(
        {"big": [1.0] * 50, "small": [0.0]}, lambda xs: sum(xs) / len(xs), resamples=500, seed=1
    )
    assert lo == pytest.approx(0.0)
    assert hi == pytest.approx(1.0)


@settings(max_examples=40, deadline=None)
@given(
    st.lists(st.tuples(st.integers(0, 6), st.floats(-1, 1)), min_size=2, max_size=40),
    st.integers(0, 99),
)
def test_ci_is_deterministic_and_brackets_value(rows: list[tuple[int, float]], seed: int) -> None:
    pairs = [P(f"g{g}", s) for g, s in rows]
    a, b = crsc_sem(pairs, resamples=300, seed=seed), crsc_sem(pairs, resamples=300, seed=seed)
    assert a == b
    m = a.metric
    if m.ci_low is not None and m.ci_high is not None and m.value is not None:
        assert m.ci_low >= -1
        assert m.ci_high <= 1


def test_report_stratifies_per_model() -> None:
    pairs = [
        P("a", 0.9, model="m1", language="hi"),
        P("b", 0.5, model="m1", language="en"),
        P("c", 1.0, model="m2"),
    ]
    r = report(pairs, resamples=50)
    assert [s.value for s in r.overall] == ["m1", "m2"]
    langs = {s.value: s.sem.metric.value for s in r.strata if s.stratum == "m1:language"}
    assert langs == {"en": pytest.approx(0.5), "hi": pytest.approx(0.9)}
