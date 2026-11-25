from __future__ import annotations

from fastapi.testclient import TestClient
from sqlalchemy import inspect, text

from emojilens_api.config import Settings
from emojilens_api.db import make_engine
from emojilens_api.db.migrate import (
    alembic_config,
    current_revision,
    head_revision,
    upgrade_to_head,
)
from emojilens_api.main import create_app


def test_health(client: TestClient) -> None:
    r = client.get("/api/v1/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_ready_when_migrated(client: TestClient) -> None:
    r = client.get("/api/v1/ready")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ready"
    assert any("journal_mode=wal" in c["detail"] for c in body["checks"])


def test_not_ready_without_migrations(db_url: str) -> None:
    with TestClient(create_app(Settings(database_url=db_url))) as c:
        r = c.get("/api/v1/ready")
    assert r.status_code == 503
    assert r.json()["status"] == "not_ready"


def test_unknown_route_structured_404(client: TestClient) -> None:
    r = client.get("/api/v1/nope")
    assert r.status_code == 404
    assert r.json()["error"]["code"] == "not_found"


def test_fresh_migration_creates_m0(db_url: str) -> None:
    upgrade_to_head(db_url)
    engine = make_engine(db_url)
    assert "app_meta" in inspect(engine).get_table_names()
    assert current_revision(engine) == head_revision(db_url)
    with engine.connect() as conn:
        assert conn.execute(text("PRAGMA journal_mode")).scalar() == "wal"
        assert conn.execute(text("PRAGMA foreign_keys")).scalar() == 1


def test_migration_downgrade_and_reupgrade(db_url: str) -> None:
    from alembic import command

    upgrade_to_head(db_url)
    command.downgrade(alembic_config(db_url), "base")
    engine = make_engine(db_url)
    assert "app_meta" not in inspect(engine).get_table_names()
    upgrade_to_head(db_url)
    assert "app_meta" in inspect(engine).get_table_names()


def test_system_info_reports_runtime_without_private_details(client: TestClient) -> None:
    import getpass
    import socket

    res = client.get("/api/v1/system/info")
    assert res.status_code == 200
    info = res.json()
    assert info["version"]
    assert info["database"]["ok"] is True
    assert info["database"]["journal_mode"] == "wal"
    assert info["database"]["migration"] == info["database"]["head"]
    assert {m["key"] for m in info["models"]} >= {"tesseract-ocr", "vlm-smolvlm-256m"}
    assert all("task" in m and "revision" in m for m in info["models"])
    assert info["test_doubles_enabled"] is False
    assert info["renderer"]["javascript"] is False
    assert info["renderer"]["network"] is False
    assert {d["name"] for d in info["dependencies"]} >= {"torch", "sklearn"}
    assert info["artifacts"] == {"files": 0, "bytes": 0}
    raw = res.text
    for private in ("/home/", "/tmp", "/Users/", "sqlite:///", socket.gethostname()):
        assert private not in raw
    assert f'"{getpass.getuser()}"' not in raw
