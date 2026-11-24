"""Multimodal tests: sandbox properties, determinism, real OCR on Chromium renderings."""

from __future__ import annotations

import os
import shutil
from pathlib import Path

import pytest

from emojilens_core.models import Capability
from emojilens_core.models.catalog import default_registry
from emojilens_core.multimodal import (
    RenderConfig,
    build_html,
    compare,
    levenshtein,
    render_chromium,
    visible_form,
)

CHROME = os.environ.get("EMOJILENS_CHROMIUM_PATH") or shutil.which("google-chrome")
needs_browser = pytest.mark.skipif(
    not CHROME and not Path.home().joinpath(".cache/ms-playwright").exists(),
    reason="no Chromium available",
)


def test_html_escapes_markup_and_forbids_network() -> None:
    doc = build_html("<img src=http://evil/x onerror=alert(1)><script>x()</script>", RenderConfig())
    assert "<img" not in doc
    assert "<script>" not in doc
    assert "&lt;img" in doc
    assert "default-src 'none'" in doc


def test_render_config_validation() -> None:
    with pytest.raises(ValueError, match="font names"):
        RenderConfig(fonts=("x'); background:url(http://a)",)).validate()
    with pytest.raises(ValueError, match="colors"):
        RenderConfig(color="red").validate()
    with pytest.raises(ValueError, match="out of bounds"):
        RenderConfig(width=10).validate()


def test_levenshtein_and_visible_form() -> None:
    assert levenshtein(list("kitten"), list("sitting")) == 3
    assert visible_form("pass\u200bword\ufe0f  x") == "password x"


def test_compare_excludes_hidden_from_error_rate() -> None:
    c = compare("hi\u200bthere" + "".join(chr(0xE0000 + ord(x)) for x in "ab"), "hithere")
    assert c.grapheme_error_rate == 0.0
    assert c.hidden_codepoints_in_original == 3
    assert c.hidden_codepoints_recovered == 0


@needs_browser
def test_chromium_render_is_deterministic_and_sandboxed(tmp_path: Path) -> None:
    if CHROME:
        os.environ.setdefault("EMOJILENS_CHROMIUM_PATH", CHROME)
    text = 'Hello <b>world</b> \U0001f44d <img src="http://127.0.0.1:9/x">'
    a = render_chromium(text, tmp_path / "a")
    b = render_chromium(text, tmp_path / "b")
    assert a.image_sha256 == b.image_sha256
    assert a.width == 900
    assert a.provenance["javascript"] is False
    assert a.provenance["network_requests_blocked"] == []  # escaped markup never triggers a fetch


@pytest.mark.real_ocr
@needs_browser
@pytest.mark.skipif(shutil.which("tesseract") is None, reason="tesseract not installed")
def test_real_render_then_ocr_english(tmp_path: Path) -> None:
    if CHROME:
        os.environ.setdefault("EMOJILENS_CHROMIUM_PATH", CHROME)
    text = "Meeting moved to five tomorrow"
    r = render_chromium(text, tmp_path)
    ocr = default_registry().run("tesseract-ocr", Capability.OCR, r.image_path)
    assert ocr.error is None, ocr.error
    cmp = compare(text, ocr.normalized["text"])
    assert cmp.grapheme_error_rate is not None
    assert cmp.grapheme_error_rate < 0.15


@pytest.mark.real_ocr
@needs_browser
@pytest.mark.skipif(shutil.which("tesseract") is None, reason="tesseract not installed")
def test_real_render_then_ocr_hindi(tmp_path: Path) -> None:
    if CHROME:
        os.environ.setdefault("EMOJILENS_CHROMIUM_PATH", CHROME)
    reg = default_registry()
    if "hin" not in reg.adapter("tesseract-ocr").usable_langs():  # type: ignore[attr-defined]
        pytest.skip("hin traineddata not installed")
    text = (
        "\u0906\u091c \u092e\u094c\u0938\u092e "
        "\u092c\u0939\u0941\u0924 \u0905\u091a\u094d\u091b\u093e \u0939\u0948"
    )
    r = render_chromium(text, tmp_path)
    ocr = reg.run("tesseract-ocr", Capability.OCR, r.image_path)
    cmp = compare(text, ocr.normalized["text"])
    assert cmp.grapheme_error_rate is not None
    assert cmp.grapheme_error_rate < 0.2
