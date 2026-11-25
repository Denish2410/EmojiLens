"""Experiment lifecycle tests. All inference uses labelled TEST DOUBLES (not real models)."""

from __future__ import annotations

import json

from fastapi.testclient import TestClient

from emojilens_api.services.experiments import mark_interrupted

NDJSON = {"Content-Type": "application/x-ndjson"}
TD = "test-double-all"


def dataset(c: TestClient, freeze: bool = True) -> str:
    c.post(
        "/api/v1/datasets",
        json={"slug": "ex", "name": "E", "kind": "synthetic_fixture", "license": "CC0-1.0"},
    )
    lines = [
        json.dumps(
            {
                "id": f"s{i}",
                "text": f"please refuse {i}" if i == 0 else f"hello {i}",
                "language": "en",
                "origin": "synthetic:test",
                "license": "CC0-1.0",
            }
        )
        for i in range(3)
    ]
    c.post("/api/v1/datasets/ex/versions", content="\n".join(lines).encode(), headers=NDJSON)
    if freeze:
        c.post("/api/v1/datasets/ex/versions/1/freeze", json={"seed": 1})
    out = c.post(
        "/api/v1/datasets/ex/versions/1/variants",
        json={"chain": [{"transform_id": "homoglyph", "params": {"rate": 0.5}}]},
    ).json()
    return str(out.get("recipe_hash", ""))


def body(recipe: str, **kw: object) -> dict[str, object]:
    b: dict[str, object] = {
        "name": "td run",
        "dataset": "ex",
        "version": 1,
        "recipe_hashes": [recipe],
        "model_keys": [TD],
        "capabilities": ["CLASSIFY", "GENERATE"],
        "label_map": {"ok": "safe", "flagged": "unsafe"},
    }
    b.update(kw)
    return b


def run_worker(c: TestClient) -> None:
    while c.app.state.worker.run_once() is not None:  # type: ignore[attr-defined]
        pass


def test_models_endpoint_reports_real_catalog_availability(client: TestClient) -> None:
    body = client.get("/api/v1/models").json()
    keys = {m["key"]: m for m in body["models"]}
    assert "tesseract-ocr" in keys
    assert TD not in keys  # test doubles are never registered in normal operation
    hf = keys["embed-multilingual-minilm"]
    assert hf["availability"] in ("dependency_missing", "not_downloaded")
    r = client.post(
        "/api/v1/models/embed-multilingual-minilm/infer", json={"capability": "EMBED", "text": "hi"}
    )
    assert r.status_code == 409


def test_infer_with_test_double_is_flagged(td_client: TestClient) -> None:
    r = td_client.post(
        f"/api/v1/models/{TD}/infer", json={"capability": "TOKENIZE", "text": "kal milte hain"}
    )
    assert r.status_code == 200
    out = r.json()
    assert out["metadata"]["test_double"] is True
    assert out["tokenization"]["tokens"] == ["kal", "milte", "hain"]
    bad = td_client.post(f"/api/v1/models/{TD}/infer", json={"capability": "OCR", "text": "x"})
    assert bad.status_code == 422


def test_experiment_runs_to_completion_with_provenance(td_client: TestClient) -> None:
    recipe = dataset(td_client)
    exp = td_client.post("/api/v1/experiments", json=body(recipe)).json()
    assert exp["status"] == "queued"
    assert exp["total_items"] == (3 + 3) * 2
    assert exp["uses_test_doubles"] is True
    run_worker(td_client)
    done = td_client.get(f"/api/v1/experiments/{exp['id']}").json()
    assert done["status"] == "completed"
    assert done["done_items"] == 12
    page = td_client.get(f"/api/v1/experiments/{exp['id']}/outputs?page_size=200").json()
    assert page["total"] == 12
    assert all(o["test_double"] for o in page["items"])
    gens = [o for o in page["items"] if o["capability"] == "GENERATE"]
    assert {o["behavior"] for o in gens} <= {"answer", "refusal"}
    assert any(o["behavior"] == "refusal" for o in gens if o["source_id"] == "s0")
    cls = [o for o in page["items"] if o["capability"] == "CLASSIFY"]
    assert {o["safety"] for o in cls} <= {"safe", "unsafe"}
    assert all(o["split"] is not None for o in page["items"])


def test_cancel_queued_and_finished(td_client: TestClient) -> None:
    recipe = dataset(td_client)
    exp = td_client.post("/api/v1/experiments", json=body(recipe)).json()
    assert td_client.post(f"/api/v1/experiments/{exp['id']}/cancel").json()["status"] == "cancelled"
    assert td_client.post(f"/api/v1/experiments/{exp['id']}/cancel").status_code == 409
    run_worker(td_client)
    assert td_client.get(f"/api/v1/experiments/{exp['id']}").json()["done_items"] == 0


def test_cancel_running_stops_between_items(td_client: TestClient) -> None:
    from emojilens_api.db.models import Experiment

    recipe = dataset(td_client)
    exp = td_client.post("/api/v1/experiments", json=body(recipe)).json()
    factory = td_client.app.state.sessionmaker  # type: ignore[attr-defined]
    with factory() as s:
        row = s.get(Experiment, exp["id"])
        row.status = "queued"
        row.cancel_requested = True  # simulates a cancel arriving once the run has started
        s.commit()
    run_worker(td_client)
    got = td_client.get(f"/api/v1/experiments/{exp['id']}").json()
    assert got["status"] == "cancelled"
    assert got["done_items"] == 0


def test_interrupted_runs_are_marked_and_resumable(td_client: TestClient) -> None:
    from emojilens_api.db.models import Experiment

    recipe = dataset(td_client)
    exp = td_client.post("/api/v1/experiments", json=body(recipe)).json()
    factory = td_client.app.state.sessionmaker  # type: ignore[attr-defined]
    with factory() as s:
        s.get(Experiment, exp["id"]).status = "running"
        s.commit()
    assert mark_interrupted(factory) == 1
    got = td_client.get(f"/api/v1/experiments/{exp['id']}").json()
    assert got["status"] == "interrupted"
    assert "resume" in got["error"]
    assert td_client.post(f"/api/v1/experiments/{exp['id']}/resume").json()["status"] == "queued"
    run_worker(td_client)
    assert td_client.get(f"/api/v1/experiments/{exp['id']}").json()["status"] == "completed"
    run_again = td_client.get(f"/api/v1/experiments/{exp['id']}/outputs").json()
    assert run_again["total"] == 12  # resume never duplicates outputs


def test_experiment_validation(td_client: TestClient) -> None:
    recipe = dataset(td_client)
    assert (
        td_client.post("/api/v1/experiments", json=body(recipe, model_keys=["nope"])).status_code
        == 404
    )
    unavailable = td_client.post(
        "/api/v1/experiments",
        json=body(recipe, model_keys=["embed-multilingual-minilm"], capabilities=["EMBED"]),
    )
    assert unavailable.status_code == 409
    assert (
        td_client.post("/api/v1/experiments", json=body(recipe, capabilities=["OCR"])).status_code
        == 422
    )
    assert (
        td_client.get("/api/v1/experiments/999").json()["error"]["code"] == "experiment_not_found"
    )


def test_api_registry_applies_model_pins(migrated_db_url: str, tmp_path: object) -> None:
    import pathlib

    from emojilens_api.config import Settings
    from emojilens_api.main import create_app

    pins = pathlib.Path(str(tmp_path)) / "pins.json"
    pins.write_text(json.dumps({"pins": {"embed-multilingual-minilm": {"revision": "b" * 40}}}))
    app = create_app(
        Settings(database_url=migrated_db_url, run_worker=False, model_pins_path=str(pins))
    )
    with TestClient(app) as c:
        models = {m["key"]: m for m in c.get("/api/v1/models").json()["models"]}
    assert models["embed-multilingual-minilm"]["revision"] == "b" * 40


def test_sentiment_classifier_labels_cannot_become_safety_judgments(td_client: TestClient) -> None:
    """Regression: a sentiment model must never feed CRSC-safe through a label map."""
    from emojilens_core.models import Capability, ModelConfig

    reg = td_client.app.state.registry  # type: ignore[attr-defined]
    reg.add(
        ModelConfig(
            key="td-sentiment",
            adapter="test_double",
            model_id="test-double/sentiment",
            capabilities=(Capability.CLASSIFY,),
            license="n/a",
            task="sentiment",
            test_double=True,
        )
    )
    recipe = dataset(td_client)
    r = td_client.post(
        "/api/v1/experiments",
        json=body(recipe, model_keys=["td-sentiment"], capabilities=["CLASSIFY"]),
    )
    assert r.status_code == 422
    assert r.json()["error"]["code"] == "not_a_safety_classifier"
    ok = td_client.post(
        "/api/v1/experiments",
        json=body(recipe, model_keys=["td-sentiment"], capabilities=["CLASSIFY"], label_map=None),
    )
    assert ok.status_code == 201


def test_models_endpoint_reports_task(client: TestClient) -> None:
    models = {m["key"]: m for m in client.get("/api/v1/models").json()["models"]}
    assert models["classifier-xlmr-sentiment"]["task"] == "sentiment"


def test_outputs_record_language_coverage(td_client: TestClient) -> None:
    from emojilens_core.models import Capability, ModelConfig

    td_client.app.state.registry.add(  # type: ignore[attr-defined]
        ModelConfig(
            key="td-en-only",
            adapter="test_double",
            model_id="test-double/en-only",
            capabilities=(Capability.EMBED,),
            license="n/a",
            task="embedding",
            languages=("hi-Latn",),
            test_double=True,
        )
    )
    recipe = dataset(td_client)
    exp = td_client.post(
        "/api/v1/experiments",
        json=body(recipe, model_keys=["td-en-only", TD], capabilities=["EMBED"], label_map=None),
    ).json()
    run_worker(td_client)
    items = td_client.get(f"/api/v1/experiments/{exp['id']}/outputs?page_size=200").json()["items"]
    limited = [o for o in items if o["model_key"] == "td-en-only"]
    assert {o["normalized"]["_language_supported"] for o in limited} == {False}
    undeclared = [o for o in items if o["model_key"] == TD]
    assert {o["normalized"]["_language_supported"] for o in undeclared} == {None}


def test_vlm_modality_validation(td_client: TestClient) -> None:
    from emojilens_core.models import Capability, ModelConfig

    recipe = dataset(td_client)
    post = td_client.post
    no_cap = post("/api/v1/experiments", json=body(recipe, modalities=["vlm"], label_map=None))
    assert no_cap.status_code == 422
    assert no_cap.json()["error"]["code"] == "modality_capability_mismatch"
    no_mod = post(
        "/api/v1/experiments", json=body(recipe, capabilities=["VISION_INPUT"], label_map=None)
    )
    assert no_mod.json()["error"]["code"] == "modality_capability_mismatch"
    stray = post("/api/v1/experiments", json=body(recipe, vlm_prompt="x", label_map=None))
    assert stray.json()["error"]["code"] == "vlm_prompt_without_vlm"
    # The real catalogue classifier has no vision input, so it cannot join a VLM-only run.
    td_client.app.state.registry.add(  # type: ignore[attr-defined]
        ModelConfig(
            key="td-text-only",
            adapter="test_double",
            model_id="test-double/text-only",
            capabilities=(Capability.EMBED,),
            license="n/a",
            task="embedding",
            test_double=True,
        )
    )
    blind = post(
        "/api/v1/experiments",
        json=body(
            recipe,
            model_keys=["td-text-only"],
            capabilities=["VISION_INPUT"],
            modalities=["vlm"],
            label_map=None,
        ),
    )
    assert blind.json()["error"]["code"] == "capability_unsupported"


def test_text_only_config_hash_has_no_vlm_prompt(td_client: TestClient) -> None:
    recipe = dataset(td_client)
    exp = td_client.post("/api/v1/experiments", json=body(recipe)).json()
    assert "vlm_prompt" not in exp["config"]


def test_models_endpoint_hides_absolute_cache_path(client: TestClient) -> None:
    from pathlib import Path

    cache = client.get("/api/v1/models").json()["resources"]["cache_dir"]
    assert not cache.startswith(str(Path.home()))
    assert cache.startswith("~") or cache == "(configured location)"
