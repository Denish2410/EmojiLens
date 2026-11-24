"""CRSC endpoint tests on TEST-DOUBLE outputs (flagged as not research-reportable)."""

from __future__ import annotations

import json

from fastapi.testclient import TestClient

NDJSON = {"Content-Type": "application/x-ndjson"}


def setup(c: TestClient) -> int:
    c.post(
        "/api/v1/datasets",
        json={"slug": "cr", "name": "C", "kind": "synthetic_fixture", "license": "CC0-1.0"},
    )
    lines = [
        json.dumps(
            {
                "id": f"s{i}",
                "text": f"good morning friend {i}",
                "language": "en" if i % 2 else "hi-Latn",
                "source_group": f"g{i}",
                "origin": "synthetic:test",
                "license": "CC0-1.0",
            }
        )
        for i in range(6)
    ]
    c.post("/api/v1/datasets/cr/versions", content="\n".join(lines).encode(), headers=NDJSON)
    c.post("/api/v1/datasets/cr/versions/1/freeze", json={"seed": 1})
    ident = c.post(
        "/api/v1/datasets/cr/versions/1/variants", json={"chain": [{"transform_id": "identity"}]}
    ).json()["recipe_hash"]
    homo = c.post(
        "/api/v1/datasets/cr/versions/1/variants",
        json={"chain": [{"transform_id": "homoglyph", "params": {"rate": 1.0}}]},
    ).json()["recipe_hash"]
    exp = c.post(
        "/api/v1/experiments",
        json={
            "name": "crsc",
            "dataset": "cr",
            "version": 1,
            "recipe_hashes": [ident, homo],
            "model_keys": ["test-double-all"],
            "capabilities": ["EMBED", "CLASSIFY"],
            "label_map": {"ok": "safe", "flagged": "unsafe"},
        },
    ).json()
    while c.app.state.worker.run_once() is not None:  # type: ignore[attr-defined]
        pass
    return int(exp["id"])


def test_crsc_requires_completed_experiment(td_client: TestClient) -> None:
    exp_id = setup(td_client)
    td_client.post(f"/api/v1/experiments/{exp_id}/cancel")
    empty = td_client.get(f"/api/v1/experiments/{exp_id}/crsc").json()
    assert empty["results"] == []
    assert empty["experimental"] is True


def test_crsc_computed_stored_and_flagged(td_client: TestClient) -> None:
    exp_id = setup(td_client)
    out = td_client.post(
        f"/api/v1/experiments/{exp_id}/crsc", json={"resamples": 200, "seed": 3}
    ).json()
    assert out["research_reportable"] is False
    assert out["synthetic_fixture"] is True
    assert out["test_double"] is True
    res = {(r["metric"], r["stratum"], r["stratum_value"]): r for r in out["results"]}
    identity = res[("crsc_sem", "family", "identity")]
    assert identity["value"] == 1.0  # identical inputs give identical deterministic embeddings
    assert identity["details"]["identity_failures"] == 0
    assert identity["n"] == 6
    assert identity["n_groups"] == 6
    safe_id = res[("crsc_safe", "family", "identity")]
    assert safe_id["value"] == 1.0
    assert safe_id["details"]["unsafe_to_safe"] == 0
    overall = res[("crsc_sem", "overall", "all")]
    assert overall["n"] == 12
    assert overall["ci_low"] <= overall["value"] <= overall["ci_high"]
    assert res[("crsc_sem", "human", "unannotated")]["n"] == 12
    again = td_client.get(f"/api/v1/experiments/{exp_id}/crsc").json()
    assert len(again["results"]) == len(out["results"])
