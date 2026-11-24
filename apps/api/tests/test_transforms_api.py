from __future__ import annotations

import json

from fastapi.testclient import TestClient

NDJSON = {"Content-Type": "application/x-ndjson"}
CHAIN = [{"transform_id": "unicode_smuggling", "params": {"method": "tag_payload"}}]


def setup_dataset(client: TestClient, freeze: bool = True) -> None:
    client.post(
        "/api/v1/datasets",
        json={"slug": "dd", "name": "D", "kind": "synthetic_fixture", "license": "CC0-1.0"},
    )
    lines = [
        json.dumps(
            {
                "id": f"s{i}",
                "text": f"good morning friend {i}",
                "language": "en",
                "source_group": f"g{i // 2}",
                "origin": "synthetic:test",
                "license": "CC0-1.0",
            }
        )
        for i in range(20)
    ]
    client.post("/api/v1/datasets/dd/versions", content="\n".join(lines).encode(), headers=NDJSON)
    if freeze:
        client.post("/api/v1/datasets/dd/versions/1/freeze", json={"seed": 5})


def test_list_transforms(client: TestClient) -> None:
    specs = client.get("/api/v1/transforms").json()
    assert {s["family"] for s in specs} == {
        "identity",
        "unicode_smuggling",
        "emoji_substitution",
        "emoji_cipher",
        "homoglyph",
        "text_obfuscation",
        "code_mixing",
    }
    smuggling = next(s for s in specs if s["id"] == "unicode_smuggling")
    assert {p["name"] for p in smuggling["params"]} >= {"method", "rate", "payload"}


def test_apply_chain_is_reproducible(client: TestClient) -> None:
    body = {
        "text": "Today is good",
        "variety": "en",
        "seed": 3,
        "chain": [
            {"transform_id": "code_mixing", "params": {"target": "hi-Latn", "rate": 1.0}},
            {"transform_id": "homoglyph", "params": {"rate": 0.5}},
        ],
    }
    a = client.post("/api/v1/transforms/apply", json=body).json()
    b = client.post("/api/v1/transforms/apply", json=body).json()
    assert a["output"] == b["output"]
    assert a["chain_hash"] == b["chain_hash"]
    assert a["valid"] is True
    assert len(a["steps"]) == 2
    assert "".join(p[2] for p in a["pieces"]) == a["output"]


def test_apply_rejects_bad_params(client: TestClient) -> None:
    r = client.post(
        "/api/v1/transforms/apply",
        json={
            "text": "x",
            "variety": "en",
            "chain": [{"transform_id": "homoglyph", "params": {"rate": 3}}],
        },
    )
    assert r.status_code == 422
    assert r.json()["error"]["code"] == "transform_error"


def test_variants_require_frozen_version(client: TestClient) -> None:
    setup_dataset(client, freeze=False)
    r = client.post("/api/v1/datasets/dd/versions/1/variants", json={"chain": CHAIN})
    assert r.status_code == 409
    assert r.json()["error"]["code"] == "version_not_frozen"


def test_generate_variants_inherit_splits_without_leakage(client: TestClient) -> None:
    setup_dataset(client)
    r = client.post("/api/v1/datasets/dd/versions/1/variants", json={"seed": 1, "chain": CHAIN})
    assert r.status_code == 201
    out = r.json()
    assert out["created"] == 20
    assert out["invalid"] == 0
    again = client.post(
        "/api/v1/datasets/dd/versions/1/variants", json={"seed": 1, "chain": CHAIN}
    ).json()
    assert again["created"] == 0
    assert again["skipped_existing"] == 20

    sources = {
        s["external_id"]: s["split"]
        for s in client.get("/api/v1/datasets/dd/versions/1/sources?page_size=200").json()["items"]
    }
    page = client.get(
        f"/api/v1/datasets/dd/versions/1/variants?recipe_hash={out['recipe_hash']}&page_size=200"
    ).json()
    assert page["total"] == 20
    for v in page["items"]:
        assert v["split"] == sources[v["source_id"]]
        assert v["text"] != v["source_text"]
    detail = client.get("/api/v1/datasets/dd/versions/1").json()
    assert detail["leakage"] == []
    assert sum(detail["stats"]["variants_by_split"].values()) == 20


def test_list_recipes(client: TestClient) -> None:
    setup_dataset(client)
    client.post("/api/v1/datasets/dd/versions/1/variants", json={"seed": 1, "chain": CHAIN})
    recipes = client.get("/api/v1/datasets/dd/versions/1/recipes").json()
    assert len(recipes) == 1
    assert recipes[0]["families"] == "unicode_smuggling"
    assert recipes[0]["variants"] == 20
    assert recipes[0]["seed"] == 1
