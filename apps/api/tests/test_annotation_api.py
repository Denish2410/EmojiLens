"""Annotation workflow tests. Labels here are test inputs in a temporary database."""

from __future__ import annotations

import json

import pytest
from fastapi.testclient import TestClient

NDJSON = {"Content-Type": "application/x-ndjson"}
A = "/api/v1/annotation"


@pytest.fixture
def tasks(client: TestClient) -> list[int]:
    client.post(
        "/api/v1/datasets",
        json={"slug": "ann", "name": "A", "kind": "synthetic_fixture", "license": "CC0-1.0"},
    )
    lines = [
        json.dumps(
            {
                "id": f"s{i}",
                "text": f"good morning friend {i}",
                "language": "en" if i % 2 else "hi-Latn",
                "origin": "synthetic:test",
                "license": "CC0-1.0",
            }
        )
        for i in range(8)
    ]
    client.post("/api/v1/datasets/ann/versions", content="\n".join(lines).encode(), headers=NDJSON)
    client.post("/api/v1/datasets/ann/versions/1/freeze", json={"seed": 1})
    recipe = client.post(
        "/api/v1/datasets/ann/versions/1/variants",
        json={"seed": 2, "chain": [{"transform_id": "homoglyph", "params": {"rate": 0.3}}]},
    ).json()["recipe_hash"]
    client.post(
        f"{A}/guidelines",
        json={"version": "g1", "title": "Equivalence", "body": "Judge meaning only."},
    )
    out = client.post(
        f"{A}/tasks",
        json={
            "dataset": "ann",
            "version": 1,
            "recipe_hash": recipe,
            "guideline_version": "g1",
            "per_language": 2,
        },
    ).json()
    assert out == {"created": 4, "existing": 0, "by_language": {"en": 2, "hi-Latn": 2}}
    for p in ("rater1", "rater2"):
        assert (
            client.post(
                f"{A}/annotators",
                json={"pseudonym": p, "proficiency": {"en": "fluent", "hi-Latn": "native"}},
            ).status_code
            == 201
        )
    ids = []
    while (item := client.get(f"{A}/queue?annotator=rater1").json()) is not None:
        ids.append(item["task_id"])
        client.post(
            f"{A}/tasks/{item['task_id']}/annotations",
            json={"annotator": "rater1", "semantic_label": "equivalent", "safety_label": "safe"},
        )
    return ids


def test_queue_is_blinded_and_exhausts(client: TestClient, tasks: list[int]) -> None:
    assert len(tasks) == 4
    item = client.get(f"{A}/queue?annotator=rater2").json()
    assert set(item) == {
        "task_id",
        "guideline_version",
        "language",
        "source_text",
        "variant_text",
        "remaining",
    }
    assert item["remaining"] == 4
    assert client.get(f"{A}/queue?annotator=rater1").json() is None


def test_duplicate_annotation_rejected_and_unknown_annotator(
    client: TestClient, tasks: list[int]
) -> None:
    r = client.post(
        f"{A}/tasks/{tasks[0]}/annotations",
        json={"annotator": "rater1", "semantic_label": "partial", "safety_label": "safe"},
    )
    assert r.json()["error"]["code"] == "already_annotated"
    assert client.get(f"{A}/queue?annotator=ghost").json()["error"]["code"] == "annotator_not_found"
    bad = client.post(
        f"{A}/tasks/{tasks[0]}/annotations",
        json={"annotator": "rater2", "semantic_label": "maybe", "safety_label": "safe"},
    )
    assert bad.status_code == 422


def test_agreement_disagreements_and_adjudication(client: TestClient, tasks: list[int]) -> None:
    labels = ["equivalent", "not_equivalent", "equivalent", "unsure"]
    for tid, lab in zip(sorted(tasks), labels, strict=True):
        client.post(
            f"{A}/tasks/{tid}/annotations",
            json={"annotator": "rater2", "semantic_label": lab, "safety_label": "safe"},
        )
    ag = client.get(f"{A}/agreement").json()
    assert ag["annotations"] == 8
    assert ag["tasks_with_two_or_more"] == 4
    assert ag["unsure_treated_as_missing"] is True
    pair = ag["pairwise_kappa"][0]
    assert pair["annotators"] == ["rater1", "rater2"]
    assert pair["items"] == 3
    dis = client.get(f"{A}/disagreements").json()
    assert {d["task_id"] for d in dis} == {sorted(tasks)[1], sorted(tasks)[3]}
    tid = sorted(tasks)[1]
    r = client.post(
        f"{A}/tasks/{tid}/adjudication",
        json={
            "adjudicator": "lead",
            "semantic_label": "partial",
            "safety_label": "safe",
            "rationale": "Look-alike letters keep meaning.",
        },
    )
    assert r.status_code == 201
    assert tid not in {d["task_id"] for d in client.get(f"{A}/disagreements").json()}
    assert client.get(f"{A}/agreement").json()["adjudicated"] == 1


def test_guidelines_are_immutable_versions(client: TestClient) -> None:
    body = {"version": "g9", "title": "t", "body": "b"}
    assert client.post(f"{A}/guidelines", json=body).status_code == 201
    assert client.post(f"{A}/guidelines", json=body).json()["error"]["code"] == "guideline_exists"


def test_agreement_with_no_data_is_undefined(client: TestClient) -> None:
    ag = client.get(f"{A}/agreement").json()
    assert ag["alpha_nominal"] is None
    assert ag["annotations"] == 0
