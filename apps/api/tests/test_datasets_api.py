from __future__ import annotations

import json

from alembic.autogenerate import compare_metadata
from alembic.migration import MigrationContext
from fastapi.testclient import TestClient

from emojilens_api.db import Base, make_engine
from emojilens_api.db import models as _models  # noqa: F401

NDJSON = {"Content-Type": "application/x-ndjson"}


def rec(i: str, text: str, **kw: object) -> str:
    base: dict[str, object] = {
        "id": i,
        "text": text,
        "language": "en",
        "origin": "synthetic:test",
        "license": "CC0-1.0",
    }
    base.update(kw)
    return json.dumps(base, ensure_ascii=False)


def make(client: TestClient, slug: str = "demo", kind: str = "synthetic_fixture") -> None:
    r = client.post(
        "/api/v1/datasets",
        json={"slug": slug, "name": "Demo", "kind": kind, "license": "CC0-1.0"},
    )
    assert r.status_code == 201, r.text


def upload(client: TestClient, lines: list[str], slug: str = "demo") -> dict[str, object]:
    r = client.post(
        f"/api/v1/datasets/{slug}/versions", content="\n".join(lines).encode(), headers=NDJSON
    )
    assert r.status_code == 201, r.text
    body: dict[str, object] = r.json()
    return body


def test_orm_matches_migrations(migrated_db_url: str) -> None:
    engine = make_engine(migrated_db_url)
    with engine.connect() as conn:
        diff = compare_metadata(MigrationContext.configure(conn), Base.metadata)
    assert diff == []


def test_create_list_and_duplicate_slug(client: TestClient) -> None:
    make(client)
    assert (
        client.post(
            "/api/v1/datasets",
            json={"slug": "demo", "name": "x", "kind": "evaluation", "license": "x"},
        ).json()["error"]["code"]
        == "dataset_exists"
    )
    assert [d["slug"] for d in client.get("/api/v1/datasets").json()] == ["demo"]
    bad = client.post(
        "/api/v1/datasets",
        json={"slug": "../etc", "name": "x", "kind": "evaluation", "license": "x"},
    )
    assert bad.status_code == 422


def test_import_preserves_text_and_reports_duplicates(client: TestClient) -> None:
    make(client)
    text = " kal milte hain \U0001f44d\U0001f3fd "
    body = upload(
        client,
        [
            rec("a", text, language="hi-Latn", source_group="g1"),
            rec("b", "Hello World", source_group="g1"),
            rec("c", "hello   world"),
        ],
    )
    version = body["version"]
    assert isinstance(version, dict)
    assert version["number"] == 1
    assert version["record_count"] == 3
    assert body["duplicates"] == [{"kind": "normalized", "ids": ["b", "c"]}]
    page = client.get("/api/v1/datasets/demo/versions/1/sources?q=milte").json()
    assert page["total"] == 1
    assert page["items"][0]["text"] == text
    assert page["items"][0]["detected_language"] == "hi-Latn"


def test_invalid_upload_imports_nothing(client: TestClient) -> None:
    make(client)
    r = client.post(
        "/api/v1/datasets/demo/versions",
        content="\n".join([rec("a", "ok"), "{bad"]).encode(),
        headers=NDJSON,
    )
    assert r.status_code == 422
    err = r.json()["error"]
    assert err["code"] == "dataset_validation_failed"
    assert err["details"]["errors"] == [
        {"line": 2, "code": "invalid_json", "message": "Invalid JSON at column 2."}
    ]
    assert client.get("/api/v1/datasets/demo").json()["versions"] == []


def test_upload_size_limit(client: TestClient) -> None:
    make(client)
    big = rec("a", "x" * 3000).encode() * 400
    r = client.post("/api/v1/datasets/demo/versions", content=big, headers=NDJSON)
    assert r.status_code == 413
    assert r.json()["error"]["code"] == "upload_too_large"


def test_freeze_assigns_group_aware_splits_and_passes_leakage(client: TestClient) -> None:
    make(client)
    lines = [rec(f"s{i}", f"text number {i}", source_group=f"g{i // 4}") for i in range(80)]
    upload(client, lines)
    before = client.get("/api/v1/datasets/demo/versions/1").json()
    assert before["leakage_checked"] is False
    r = client.post("/api/v1/datasets/demo/versions/1/freeze", json={"seed": 42})
    assert r.status_code == 200
    detail = r.json()
    assert detail["version"]["split_method"] == "sha256-group-bucket/1"
    assert detail["leakage_checked"] is True
    assert detail["leakage"] == []
    assert sum(detail["stats"]["split"].values()) == 80
    items = client.get("/api/v1/datasets/demo/versions/1/sources?page_size=200").json()["items"]
    by_group: dict[str, set[str]] = {}
    for it in items:
        by_group.setdefault(it["source_group"], set()).add(it["split"])
    assert all(len(s) == 1 for s in by_group.values())
    again = client.post("/api/v1/datasets/demo/versions/1/freeze", json={"seed": 1})
    assert again.status_code == 409


def test_freeze_reports_cross_split_duplicate_text(client: TestClient) -> None:
    make(client)
    lines = [
        rec(f"s{i}", "same text" if i in (0, 1) else f"t{i}", source_group=f"g{i}")
        for i in range(60)
    ]
    upload(client, lines)
    # Find a seed that separates the two duplicate groups so the check has something to catch.
    from emojilens_core.datasets import assign_split

    seed = next(
        s
        for s in range(1000)
        if assign_split("g0", s, (0.5, 0.25, 0.25)) != assign_split("g1", s, (0.5, 0.25, 0.25))
    )
    detail = client.post(
        "/api/v1/datasets/demo/versions/1/freeze", json={"seed": seed, "ratios": [0.5, 0.25, 0.25]}
    ).json()
    assert {"kind": "exact_text_across_splits", "ids": ["s0", "s1"]} in [
        {"kind": i["kind"], "ids": i["ids"]} for i in detail["leakage"]
    ]


def test_bad_ratios_and_missing_resources(client: TestClient) -> None:
    make(client)
    upload(client, [rec("a", "x")])
    r = client.post(
        "/api/v1/datasets/demo/versions/1/freeze", json={"seed": 1, "ratios": [0.5, 0.5, 0.5]}
    )
    assert r.json()["error"]["code"] == "invalid_split_ratios"
    assert client.get("/api/v1/datasets/nope").json()["error"]["code"] == "dataset_not_found"
    assert (
        client.get("/api/v1/datasets/demo/versions/9").json()["error"]["code"]
        == "version_not_found"
    )


def test_source_filters_and_pagination(client: TestClient) -> None:
    make(client)
    lines = [
        rec(
            f"s{i:02d}",
            f"t{i}",
            language="hi" if i % 2 else "en",
            control="clean" if i < 5 else None,
        )
        for i in range(30)
    ]
    upload(client, lines)
    p = client.get(
        "/api/v1/datasets/demo/versions/1/sources?language=hi&page=2&page_size=10"
    ).json()
    assert p["total"] == 15
    assert len(p["items"]) == 5
    c = client.get("/api/v1/datasets/demo/versions/1/sources?control=clean").json()
    assert c["total"] == 5
    assert client.get("/api/v1/datasets/demo/versions/1/sources?q=%25").json()["total"] == 0


def test_versions_increment(client: TestClient) -> None:
    make(client)
    upload(client, [rec("a", "x")])
    body = upload(client, [rec("a", "y")])
    version = body["version"]
    assert isinstance(version, dict)
    assert version["number"] == 2


def test_multilingual_analyze(client: TestClient) -> None:
    r = client.post("/api/v1/multilingual/analyze", json={"text": "tame kem cho \U0001f44d"})
    body = r.json()
    assert body["identification"]["label"] == "gu-Latn"
    assert body["cldr_version"].startswith("49")
    thumbs = body["emoji"][0]
    assert {m["variety"] for m in thumbs["meanings"]} == {"en", "hi", "gu", "hi-Latn", "gu-Latn"}
    gu_latn = next(m for m in thumbs["meanings"] if m["variety"] == "gu-Latn")
    assert gu_latn["fallback"] is True
    assert len(client.get("/api/v1/multilingual/varieties").json()) == 5
