"""Binary classification metrics with source-group bootstrap CIs and error case lists."""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Sequence
from dataclasses import dataclass, field

from emojilens_core.eval.crsc import group_bootstrap


@dataclass(frozen=True, slots=True)
class Item:
    id: str
    group: str
    label: int  # 1 = adversarial transformation applied, 0 = benign
    predicted: int
    score: float
    language: str = ""
    family: str = ""
    latency_ms: float = 0.0


@dataclass(frozen=True, slots=True)
class Metrics:
    n: int
    tp: int
    fp: int
    tn: int
    fn: int
    precision: float | None
    recall: float | None
    f1: float | None
    fpr: float | None
    fnr: float | None
    f1_ci: tuple[float | None, float | None]
    mean_latency_ms: float | None
    false_positives: list[str] = field(default_factory=list)
    false_negatives: list[str] = field(default_factory=list)


def _div(a: float, b: float) -> float | None:
    return a / b if b else None


def _counts(items: Sequence[Item]) -> tuple[int, int, int, int]:
    tp = sum(1 for i in items if i.label == 1 and i.predicted == 1)
    fp = sum(1 for i in items if i.label == 0 and i.predicted == 1)
    tn = sum(1 for i in items if i.label == 0 and i.predicted == 0)
    fn = sum(1 for i in items if i.label == 1 and i.predicted == 0)
    return tp, fp, tn, fn


def _f1(tp: int, fp: int, fn: int) -> float | None:
    p, r = _div(tp, tp + fp), _div(tp, tp + fn)
    return None if p is None or r is None or p + r == 0 else 2 * p * r / (p + r)


def evaluate(items: Sequence[Item], *, resamples: int = 1000, seed: int = 0) -> Metrics:
    tp, fp, tn, fn = _counts(items)
    # Encode each item as one of four outcome codes so the bootstrap can recompute F1 per sample.
    by_group: dict[str, list[float]] = defaultdict(list)
    for i in items:
        by_group[i.group].append(float(2 * i.label + i.predicted))

    def f1_of(codes: list[float]) -> float | None:
        return _f1(codes.count(3.0), codes.count(1.0), codes.count(2.0))

    ci = group_bootstrap(by_group, f1_of, resamples=resamples, seed=seed)
    return Metrics(
        n=len(items),
        tp=tp,
        fp=fp,
        tn=tn,
        fn=fn,
        precision=_div(tp, tp + fp),
        recall=_div(tp, tp + fn),
        f1=_f1(tp, fp, fn),
        fpr=_div(fp, fp + tn),
        fnr=_div(fn, fn + tp),
        f1_ci=ci,
        mean_latency_ms=_div(sum(i.latency_ms for i in items), len(items)),
        false_positives=[i.id for i in items if i.label == 0 and i.predicted == 1],
        false_negatives=[i.id for i in items if i.label == 1 and i.predicted == 0],
    )
