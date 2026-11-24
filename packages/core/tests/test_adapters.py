"""Adapter tests.

* Hugging Face adapters: availability/contract only (no weights available here). These are NOT
  real-model verification.
* Tesseract: REAL local OCR inference on an image rendered in the test (skipped if absent).
"""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest

from emojilens_core.models import AvailabilityStatus, Capability
from emojilens_core.models.catalog import CATALOG, default_registry


def test_catalog_entries_are_complete_and_safe() -> None:
    keys = [c.key for c in CATALOG]
    assert len(keys) == len(set(keys))
    caps = {cap for c in CATALOG for cap in c.capabilities}
    assert caps >= {
        Capability.CLASSIFY,
        Capability.EMBED,
        Capability.GENERATE,
        Capability.OCR,
        Capability.VISION_INPUT,
    }
    for c in CATALOG:
        assert c.license
        assert not c.test_double


def test_unpinned_or_missing_hf_models_are_not_available() -> None:
    reg = default_registry()
    for c in CATALOG:
        if c.adapter == "tesseract":
            continue
        a = reg.availability(c.key)
        assert a.status in (
            AvailabilityStatus.DEPENDENCY_MISSING,
            AvailabilityStatus.NOT_DOWNLOADED,
        )
        r = reg.run(c.key, c.capabilities[-1], "hello")
        assert r.error is not None
        assert r.error["code"] in ("dependency_missing", "model_unavailable")


def _render(text: str, path: Path, font: str, size: int = 44) -> None:
    from PIL import Image, ImageDraw, ImageFont

    img = Image.new("RGB", (900, 120), "white")
    ImageDraw.Draw(img).text((20, 30), text, fill="black", font=ImageFont.truetype(font, size))
    img.save(path)


requires_tesseract = pytest.mark.skipif(
    shutil.which("tesseract") is None, reason="tesseract not installed"
)
DEJAVU = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"


@pytest.mark.real_ocr
@requires_tesseract
@pytest.mark.skipif(not Path(DEJAVU).exists(), reason="DejaVu font missing")
def test_real_tesseract_ocr_english(tmp_path: Path) -> None:
    img = tmp_path / "en.png"
    _render("Meeting at five tomorrow", img, DEJAVU)
    r = default_registry().run("tesseract-ocr", Capability.OCR, str(img))
    assert r.error is None, r.error
    assert "Meeting" in r.normalized["text"]
    assert r.normalized["mean_confidence"] is not None
    assert r.metadata.test_double is False
    assert r.metadata.library_versions["tesseract"]


@requires_tesseract
def test_tesseract_missing_file_is_structured_error() -> None:
    r = default_registry().run("tesseract-ocr", Capability.OCR, "/nonexistent.png")
    assert r.error is not None
    assert r.error["code"] == "inference_failed"


def test_pins_file_sets_exact_revisions(tmp_path: Path) -> None:
    import json

    pins = tmp_path / "pins.json"
    pins.write_text(json.dumps({"pins": {"embed-multilingual-minilm": {"revision": "a" * 40}}}))
    reg = default_registry(pins_path=pins)
    cfg = reg.config("embed-multilingual-minilm")
    assert cfg.revision == "a" * 40
    assert cfg.tokenizer_revision == "a" * 40
    # Pinned but absent from the cache (or deps missing) is still not available.
    assert reg.availability(cfg.key).status in (
        AvailabilityStatus.DEPENDENCY_MISSING,
        AvailabilityStatus.NOT_DOWNLOADED,
    )
