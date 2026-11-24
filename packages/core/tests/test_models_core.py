"""Adapter-contract tests. Everything here uses explicitly labelled TEST DOUBLES."""

from __future__ import annotations

import pytest

from emojilens_core.models import (
    AvailabilityStatus,
    Capability,
    ErrorCode,
    ModelError,
    ModelRegistry,
    ResponseBehavior,
    SafetyJudge,
    SafetyJudgment,
    select_device,
)
from emojilens_core.models.testing import TestDoubleAdapter, make_test_double_config


def registry(**params: object) -> ModelRegistry:
    reg = ModelRegistry(device="cpu", max_loaded=1)
    reg.register_adapter("test_double", TestDoubleAdapter)
    reg.add(make_test_double_config("td-a", **params))
    reg.add(make_test_double_config("td-b"))
    return reg


def test_metadata_marks_test_doubles() -> None:
    r = registry().adapter("td-a").run(Capability.CLASSIFY, "hello")
    assert r.metadata.test_double is True
    assert r.metadata.model_id.startswith("test-double/")
    assert r.metadata.revision == "test-double"
    assert r.latency_ms >= 0
    assert r.error is None


def test_lazy_loading_and_lru_eviction() -> None:
    reg = registry()
    a = reg.adapter("td-a")
    assert not a.loaded
    reg.run("td-a", Capability.EMBED, "x")
    assert reg.adapter("td-a").loaded
    reg.run("td-b", Capability.EMBED, "x")
    assert not a.loaded  # max_loaded=1 evicts the least recently used


def test_tokenization_trace_offsets_point_into_input() -> None:
    text = "kal milte hain"
    r = registry().adapter("td-a").run(Capability.TOKENIZE, text)
    assert r.tokenization is not None
    for tok, off in zip(r.tokenization.tokens, r.tokenization.offsets, strict=True):
        assert off is not None
        assert text[off[0] : off[1]] == tok
    assert r.normalized["length"] == 3


def test_errors_are_structured_not_raised() -> None:
    reg = registry(fail_load=True)
    r = reg.adapter("td-a").run(Capability.GENERATE, "hi")
    assert r.error is not None
    assert r.error["code"] == "inference_failed"
    bad = registry().adapter("td-b").run(Capability.GENERATE, "boom")
    assert bad.error is not None
    assert bad.error["code"] == "inference_failed"
    sur = registry().adapter("td-b").run(Capability.CLASSIFY, "a\ud800")
    assert sur.error is not None
    assert sur.error["code"] == "invalid_unicode"


def test_unavailable_model_reports_status_and_refuses_to_load() -> None:
    reg = registry(present=False)
    assert reg.availability("td-a").status is AvailabilityStatus.NOT_DOWNLOADED
    with pytest.raises(ModelError) as info:
        reg.adapter("td-a").load()
    assert info.value.code is ErrorCode.MODEL_UNAVAILABLE


def test_unsupported_capability_and_unknown_model() -> None:
    reg = registry()
    with pytest.raises(ModelError) as info:
        reg.adapter("td-a").run(Capability.OCR, "x.png")
    assert info.value.code is ErrorCode.CAPABILITY_UNSUPPORTED
    with pytest.raises(ModelError):
        reg.adapter("nope")


def test_device_selection_never_assumes_cuda() -> None:
    assert select_device("cpu").device == "cpu"
    choice = select_device("auto")
    assert choice.device in ("cpu", "mps", "cuda")
    assert select_device("cuda").device in ("cpu", "cuda")
    with pytest.raises(ValueError, match="unknown device"):
        select_device("tpu")


def test_safety_judge_separates_refusal_from_safety() -> None:
    reg = registry()
    gen = reg.adapter("td-b").run(Capability.GENERATE, "please refuse this")
    cls = reg.adapter("td-b").run(Capability.CLASSIFY, "please refuse this")
    judge = SafetyJudge({"ok": "safe", "flagged": "unsafe"}, unsafe_threshold=0.5)
    j = judge.judge(cls, gen)
    assert j.behavior is ResponseBehavior.REFUSAL
    # Safety comes only from the classifier, regardless of the refusal.
    expected = (
        SafetyJudgment.UNSAFE if cls.normalized["label"] == "flagged" else SafetyJudgment.SAFE
    )
    assert j.safety is expected


def test_safety_judge_unknown_cases() -> None:
    reg = registry()
    judge = SafetyJudge({"ok": "safe"})
    cls = reg.adapter("td-b").run(Capability.CLASSIFY, "x")
    j = judge.judge(cls if cls.normalized["label"] == "flagged" else None)
    assert j.safety is SafetyJudgment.UNKNOWN
    err = registry(fail_load=True).adapter("td-a").run(Capability.CLASSIFY, "x")
    assert judge.judge(err).safety is SafetyJudgment.UNKNOWN
    with pytest.raises(ValueError, match="safe' or 'unsafe"):
        SafetyJudge({"x": "maybe"})


@pytest.mark.parametrize(
    "text",
    [
        "I can't help with that.",
        "I'm sorry, but no.",
        "मैं इसमें मदद नहीं कर सकता",
        "main madad nahi kar sakta",
    ],
)
def test_refusal_patterns(text: str) -> None:
    from emojilens_core.models import response_behavior
    from emojilens_core.models.types import InferenceResult

    meta = registry().adapter("td-a").metadata()
    r = InferenceResult(Capability.GENERATE, text, {"text": text}, 1.0, meta, {})
    assert response_behavior(r)[0] is ResponseBehavior.REFUSAL
