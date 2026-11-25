"""Smoke-validation tests. All inference here uses labelled TEST DOUBLES, never real models."""

from __future__ import annotations

from pathlib import Path

from emojilens_core.models import Capability, ModelRegistry
from emojilens_core.models.testing import TestDoubleAdapter, make_test_double_config
from emojilens_core.repro.validation import PROBES, render_markdown, validate_model

ENV = {
    "python": "3.11.9",
    "os": "Darwin",
    "machine": "arm64",
    "device": {"selected": "cpu", "reason": "requested"},
    "git": {"commit": "a" * 40, "dirty": False},
    "packages": {"numpy": "2.1.0", "torch": None},
}


def registry(**params: object) -> ModelRegistry:
    reg = ModelRegistry()
    reg.register_adapter("test_double", TestDoubleAdapter)
    reg.add(make_test_double_config("td", **params))
    return reg


def fake_renderer(text: str, out_dir: Path) -> str:
    path = out_dir / "probe.png"
    path.write_bytes(text.encode("utf-8"))  # the test double only hashes the bytes
    return str(path)


def test_probes_cover_all_five_varieties() -> None:
    assert set(PROBES) == {"en", "hi", "gu", "hi-Latn", "gu-Latn"}


def test_available_model_executes_every_probe_deterministically() -> None:
    rep = validate_model(registry(), "td", renderer=fake_renderer)
    caps = len(make_test_double_config().capabilities)
    assert len(rep.probes) == caps * 5
    assert rep.executed == caps * 5
    assert rep.failed == 0
    assert all(p.deterministic for p in rep.probes)
    assert all(p.language_declared is None for p in rep.probes)  # double declares no languages
    vision = [p for p in rep.probes if p.capability == Capability.VISION_INPUT.value]
    assert {p.summary["exact_readback"] for p in vision} == {False}


def test_image_capabilities_skip_without_renderer() -> None:
    rep = validate_model(registry(), "td")
    vision = [p for p in rep.probes if p.capability == "VISION_INPUT"]
    assert {p.status for p in vision} == {"skipped"}
    assert vision[0].detail == "no renderer available"


def test_unavailable_model_is_skipped_with_registry_reason() -> None:
    rep = validate_model(registry(present=False), "td")
    assert rep.executed == 0
    assert {p.status for p in rep.probes} == {"skipped"}
    assert rep.probes[0].detail == "test double marked absent"


def test_load_failure_is_recorded_not_hidden() -> None:
    rep = validate_model(registry(fail_load=True), "td", languages=("en",), renderer=fake_renderer)
    assert rep.failed == len(rep.probes) > 0
    assert rep.probes[0].detail == "inference_failed"


def test_markdown_labels_test_doubles_and_disclaims_research() -> None:
    rep = validate_model(registry(), "td", languages=("en",))
    md = render_markdown([rep], ENV, [{"name": "python", "status": "pass", "detail": "3.11"}])
    assert "(TEST DOUBLE)" in md
    assert "not** a research result" in md
    assert "| td (TEST DOUBLE) |" in md
