"""Multimodal endpoint tests: real Chromium render and real Tesseract OCR (skipped if absent)."""

from __future__ import annotations

import json
import os
import shutil

import pytest
from fastapi.testclient import TestClient

CHROME = shutil.which("google-chrome")
pytestmark = pytest.mark.skipif(
    CHROME is None and not os.path.exists(os.path.expanduser("~/.cache/ms-playwright")),
    reason="no Chromium",
)


@pytest.fixture(autouse=True)
def _chrome(monkeypatch: pytest.MonkeyPatch) -> None:
    if CHROME:
        monkeypatch.setenv("EMOJILENS_CHROMIUM_PATH", CHROME)


@pytest.mark.real_ocr
@pytest.mark.skipif(shutil.which("tesseract") is None, reason="tesseract not installed")
def test_analyze_renders_ocrs_and_reports_vlm_unavailable(client: TestClient) -> None:
    out = client.post(
        "/api/v1/multimodal/analyze", json={"text": "Meeting moved to five tomorrow"}
    ).json()
    assert out["renderer"] == "chromium"
    assert out["provenance"]["javascript"] is False
    assert out["ocr"]["available"] is True
    assert out["ocr"]["comparison"]["grapheme_error_rate"] < 0.15
    assert out["vlm"]["available"] is False  # no VLM weights here; never simulated
    img = client.get(out["image_url"])
    assert img.status_code == 200
    assert img.headers["content-type"] == "image/png"
    again = client.post(
        "/api/v1/multimodal/analyze", json={"text": "Meeting moved to five tomorrow"}
    ).json()
    assert again["artifact_id"] == out["artifact_id"]  # deduplicated by text + config hash


def test_markup_is_rendered_as_text_and_never_fetched(client: TestClient) -> None:
    out = client.post(
        "/api/v1/multimodal/analyze",
        json={
            "text": '<img src="http://127.0.0.1:9/x"><script>alert(1)</script>',
            "run_ocr": False,
            "run_vlm": False,
        },
    ).json()
    assert out["provenance"]["network_requests_blocked"] == []


def test_missing_artifact_404(client: TestClient) -> None:
    assert (
        client.get("/api/v1/multimodal/artifacts/999/image").json()["error"]["code"]
        == "artifact_not_found"
    )


@pytest.mark.real_ocr
@pytest.mark.skipif(shutil.which("tesseract") is None, reason="tesseract not installed")
def test_ocr_modality_experiment(td_client: TestClient) -> None:
    c = td_client
    c.post(
        "/api/v1/datasets",
        json={"slug": "mm", "name": "M", "kind": "synthetic_fixture", "license": "CC0-1.0"},
    )
    lines = [
        json.dumps(
            {
                "id": "s0",
                "text": "good morning friend",
                "language": "en",
                "origin": "synthetic:test",
                "license": "CC0-1.0",
            }
        )
    ]
    c.post(
        "/api/v1/datasets/mm/versions",
        content="\n".join(lines).encode(),
        headers={"Content-Type": "application/x-ndjson"},
    )
    c.post("/api/v1/datasets/mm/versions/1/freeze", json={"seed": 1})
    exp = c.post(
        "/api/v1/experiments",
        json={
            "name": "ocr",
            "dataset": "mm",
            "version": 1,
            "model_keys": ["test-double-all"],
            "capabilities": ["TOKENIZE"],
            "modalities": ["text", "ocr"],
        },
    ).json()
    while c.app.state.worker.run_once() is not None:  # type: ignore[attr-defined]
        pass
    assert c.get(f"/api/v1/experiments/{exp['id']}").json()["status"] == "completed"
    outs = c.get(f"/api/v1/experiments/{exp['id']}/outputs").json()["items"]
    ocr_row = next(o for o in outs if o["modality"] == "ocr")
    assert ocr_row["normalized"]["_reading"]["ocr_text"].lower().startswith("good morning")


def test_vlm_modality_experiment_with_test_double(td_client: TestClient) -> None:
    """Render -> VISION_INPUT on a labelled TEST DOUBLE. Not real VLM inference."""
    c = td_client
    c.post(
        "/api/v1/datasets",
        json={"slug": "vl", "name": "V", "kind": "synthetic_fixture", "license": "CC0-1.0"},
    )
    line = json.dumps(
        {
            "id": "s0",
            "text": "good morning 🌞",
            "language": "en",
            "origin": "synthetic:test",
            "license": "CC0-1.0",
        }
    )
    c.post(
        "/api/v1/datasets/vl/versions",
        content=line.encode(),
        headers={"Content-Type": "application/x-ndjson"},
    )
    c.post("/api/v1/datasets/vl/versions/1/freeze", json={"seed": 1})
    exp = c.post(
        "/api/v1/experiments",
        json={
            "name": "vlm",
            "dataset": "vl",
            "version": 1,
            "model_keys": ["test-double-all"],
            "capabilities": ["TOKENIZE", "VISION_INPUT"],
            "modalities": ["text", "vlm"],
            "vlm_prompt": "Read the image.",
        },
    ).json()
    assert exp["total_items"] == 2  # TOKENIZE x text, VISION_INPUT x vlm; no cross pairs
    while c.app.state.worker.run_once() is not None:  # type: ignore[attr-defined]
        pass
    assert c.get(f"/api/v1/experiments/{exp['id']}").json()["status"] == "completed"
    outs = c.get(f"/api/v1/experiments/{exp['id']}/outputs").json()["items"]
    assert {(o["capability"], o["modality"]) for o in outs} == {
        ("TOKENIZE", "text"),
        ("VISION_INPUT", "vlm"),
    }
    row = next(o for o in outs if o["modality"] == "vlm")
    assert row["error"] is None
    assert row["test_double"] is True
    assert row["normalized"]["text"].startswith("test-double reading of image")
    reading = row["normalized"]["_reading"]
    assert reading["prompt"] == "Read the image."
    assert len(reading["image_sha256"]) == 64
    assert "/" not in json.dumps(reading).replace("\\/", "")  # no filesystem paths leak
    assert row["safety"] is None
    assert row["behavior"] is None
