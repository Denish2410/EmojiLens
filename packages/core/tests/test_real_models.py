"""Real-model integration tests: execute each Hugging Face adapter on its pinned revision.

Marked ``real_model``; excluded from default CI and skipped unless the model is installed and
pinned (see docs/MODEL_SETUP_M4.md). Run on the M4 with:

    uv run pytest -m real_model
"""

from __future__ import annotations

from pathlib import Path

import pytest

from emojilens_core.models import Capability
from emojilens_core.models.catalog import CATALOG, default_registry
from emojilens_core.repro.validation import validate_model

ROOT = Path(__file__).resolve().parents[3]
PINS = ROOT / "var" / "model_pins.json"
HF_KEYS = [c.key for c in CATALOG if c.adapter != "tesseract"]

pytestmark = pytest.mark.real_model


def _renderer(text: str, out_dir: Path) -> str:
    from emojilens_core.multimodal import render_chromium

    return render_chromium(text, out_dir).image_path


@pytest.mark.parametrize("key", HF_KEYS)
def test_model_executes_every_probe_on_its_pinned_revision(key: str) -> None:
    registry = default_registry(pins_path=PINS)
    availability = registry.availability(key)
    if not availability.ok:
        pytest.skip(f"{key}: {availability.detail}")
    report = validate_model(registry, key, renderer=_renderer)
    assert report.revision, "real-model runs must use a pinned revision"
    assert report.failed == 0, [p for p in report.probes if p.status == "failed"]
    assert report.executed == len(report.probes)
    for probe in report.probes:
        if probe.capability in (Capability.TOKENIZE.value, Capability.CLASSIFY.value):
            assert probe.deterministic, (
                f"{key} {probe.capability} {probe.language} not deterministic"
            )
    registry.unload_all()
