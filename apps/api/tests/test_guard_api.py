"""EmojiGuard API tests on a synthetic fixture (flagged not research-reportable)."""

from __future__ import annotations

import json
import pathlib

from fastapi.testclient import TestClient

FIXTURE = (
    pathlib.Path(__file__).resolve().parents[3]
    / "datasets/fixtures/benign_controls.synthetic.jsonl"
)


def setup(c: TestClient) -> list[str]:
    c.post(
        "/api/v1/datasets",
        json={"slug": "gd", "name": "G", "kind": "synthetic_fixture", "license": "CC0-1.0"},
    )
    c.post(
        "/api/v1/datasets/gd/versions",
        content=FIXTURE.read_bytes(),
        headers={"Content-Type": "application/x-ndjson"},
    )
    c.post("/api/v1/datasets/gd/versions/1/freeze", json={"seed": 7, "ratios": [0.5, 0.25, 0.25]})
    chains = [
        [{"transform_id": "unicode_smuggling", "params": {"rate": 1.0}}],
        [{"transform_id": "homoglyph", "params": {"rate": 0.5}}],
        [{"transform_id": "identity"}],
    ]
    return [
        c.post("/api/v1/datasets/gd/versions/1/variants", json={"seed": 1, "chain": ch}).json()[
            "recipe_hash"
        ]
        for ch in chains
    ]


def test_assess_explains_and_allows_benign(client: TestClient) -> None:
    benign = client.post(
        "/api/v1/guard/assess", json={"text": "ક્\u200cષ \U0001f44d\U0001f3fd"}
    ).json()
    assert benign["recommendation"] in ("allow", "allow_with_information")
    risky = client.post("/api/v1/guard/assess", json={"text": "pass\u200bword reset"}).json()
    assert risky["recommendation"] in ("request_review", "flag_suspicious_transformation")
    assert risky["contributions"][0]["evidence_ids"]
    naive = client.post(
        "/api/v1/guard/assess", json={"text": "ક્\u200cષ", "ablation": {"indic_aware": False}}
    ).json()
    assert naive["rule_score"] > 0


def test_train_detector_and_evaluate_systems(client: TestClient) -> None:
    recipes = setup(client)
    det = client.post(
        "/api/v1/guard/detectors", json={"dataset": "gd", "version": 1, "recipe_hashes": recipes}
    )
    assert det.status_code == 201, det.text
    d = det.json()
    assert d["training_config"]["dataset_kind"] == "synthetic_fixture"
    assert d["evaluation"]["calibrated"] is False
    ev = client.post(
        "/api/v1/guard/evaluations",
        json={
            "dataset": "gd",
            "version": 1,
            "recipe_hashes": recipes,
            "keywords": ["password"],
            "detector_id": d["id"],
            "resamples": 200,
        },
    ).json()
    assert ev["research_reportable"] is False
    systems = ev["results"]["systems"]
    assert {
        "no_defence",
        "strip_invisibles",
        "nfkc_normalization",
        "keyword_filter",
        "emojiguard_full",
        "rules_only",
        "detector_only",
        "without_decoders",
        "without_view_rescoring",
        "without_indic_aware",
    } <= set(systems)
    assert systems["no_defence"]["overall"]["tp"] == 0
    assert "offtheshelf_classifier" in ev["results"]["unavailable"]
    # Group-aware: every evaluated item comes from the requested split only.
    assert all(i.split("#")[0].startswith("benign-") for i in ev["results"]["items"])
    got = client.get(f"/api/v1/guard/evaluations/{ev['id']}").json()
    assert got["results"]["systems"].keys() == systems.keys()


def test_evaluation_requires_frozen_version(client: TestClient) -> None:
    client.post(
        "/api/v1/datasets", json={"slug": "nf", "name": "N", "kind": "evaluation", "license": "x"}
    )
    line = json.dumps({"id": "a", "text": "x", "language": "en", "origin": "o", "license": "l"})
    client.post(
        "/api/v1/datasets/nf/versions",
        content=line.encode(),
        headers={"Content-Type": "application/x-ndjson"},
    )
    r = client.post(
        "/api/v1/guard/evaluations",
        json={"dataset": "nf", "version": 1, "recipe_hashes": ["0" * 64]},
    )
    assert r.status_code == 409
