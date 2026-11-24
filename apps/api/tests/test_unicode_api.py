from __future__ import annotations

import hashlib
import json

from fastapi.testclient import TestClient

URL = "/api/v1/unicode/analyze"


def test_analyze_preserves_input_and_hash(client: TestClient) -> None:
    text = "  hi​ \U0001f468‍\U0001f469‍\U0001f467 ક્‌ષ\n"
    r = client.post(URL, json={"text": text})
    assert r.status_code == 200
    body = r.json()
    assert body["original"] == text
    assert body["sha256"] == hashlib.sha256(text.encode("utf-8")).hexdigest()
    assert body["lengths"]["utf16_units"] == len(text.encode("utf-16-le")) // 2
    assert "".join(g["text"] for g in body["graphemes"]) == text


def test_analyze_returns_utf16_spans_for_astral(client: TestClient) -> None:
    r = client.post(URL, json={"text": "a\U0001f600b"})
    cps = r.json()["codepoints"]
    assert [c["span"]["utf16_start"] for c in cps] == [0, 1, 3]
    assert cps[1]["utf8_hex"] == "F0 9F 98 80"


def test_lone_surrogate_yields_invalid_unicode(client: TestClient) -> None:
    raw = json.dumps({"text": "ok\ud800"})  # serialised as "ok\ud800" escape
    r = client.post(URL, content=raw, headers={"Content-Type": "application/json"})
    assert r.status_code == 422
    err = r.json()["error"]
    assert err["code"] == "invalid_unicode"


def test_input_size_limit(client: TestClient) -> None:
    r = client.post(URL, json={"text": "x" * 101})
    assert r.status_code == 413
    assert r.json()["error"]["code"] == "input_too_large"


def test_missing_field_is_structured_validation_error(client: TestClient) -> None:
    r = client.post(URL, json={})
    assert r.status_code == 422
    assert r.json()["error"]["code"] == "validation_error"


def test_empty_string_is_valid(client: TestClient) -> None:
    r = client.post(URL, json={"text": ""})
    assert r.status_code == 200
    assert r.json()["lengths"]["codepoints"] == 0


def test_openapi_documents_endpoint(client: TestClient) -> None:
    spec = client.get("/api/v1/openapi.json").json()
    assert URL in spec["paths"]
