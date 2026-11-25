"""Dashboard summary tests. Inference uses labelled TEST DOUBLES only, so nothing is reportable."""

from __future__ import annotations

from fastapi.testclient import TestClient
from test_experiments_api import body, dataset, run_worker


def test_empty_summary_reports_zero_and_not_ready(client: TestClient) -> None:
    out = client.get("/api/v1/dashboard/summary").json()
    assert out["datasets"]["total"] == 0
    assert out["languages"] == {}
    assert out["experiments"]["outputs"] == 0
    assert set(out["experiments"]["by_status"]) >= {"completed", "interrupted"}
    assert out["reportable"] is False
    ready = {r["key"]: r["ok"] for r in out["readiness"]}
    assert ready["evaluation_dataset"] is False
    assert ready["human_annotation"] is False
    assert ready["reportable_experiment"] is False
    assert out["models"]["test_doubles"] == 0
    assert out["models"]["catalogue"] >= 5


def test_fixture_and_test_double_runs_are_counted_but_never_reportable(
    td_client: TestClient,
) -> None:
    recipe = dataset(td_client)
    td_client.post("/api/v1/experiments", json=body(recipe))
    run_worker(td_client)
    out = td_client.get("/api/v1/dashboard/summary").json()
    assert out["datasets"]["by_kind"] == {"synthetic_fixture": 1}
    assert out["datasets"]["frozen_versions"] == 1
    assert out["datasets"]["sources"] == 3
    assert out["languages"] == {"en": 3}
    assert out["transforms"]["families"] == ["homoglyph"]
    assert out["experiments"]["by_status"]["completed"] == 1
    assert out["experiments"]["outputs"] > 0
    assert out["experiments"]["test_double_outputs"] == out["experiments"]["outputs"]
    assert out["experiments"]["reportable"] == 0
    assert out["reportable"] is False
    ready = {r["key"]: r for r in out["readiness"]}
    assert ready["evaluation_dataset"]["ok"] is False
    assert ready["real_model"]["ok"] is False  # the test double never counts as a real model
    assert out["models"]["test_doubles"] == 1


def test_summary_exposes_no_paths(client: TestClient) -> None:
    raw = client.get("/api/v1/dashboard/summary").text
    assert "/home/" not in raw
    assert "/tmp" not in raw
