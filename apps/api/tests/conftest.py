from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from emojilens_api.config import Settings
from emojilens_api.db.migrate import upgrade_to_head
from emojilens_api.main import create_app


@pytest.fixture
def db_url(tmp_path: Path) -> str:
    return f"sqlite:///{tmp_path / 'test.db'}"


@pytest.fixture
def migrated_db_url(db_url: str) -> str:
    upgrade_to_head(db_url)
    return db_url


@pytest.fixture
def client(migrated_db_url: str) -> Iterator[TestClient]:
    settings = Settings(
        database_url=migrated_db_url, max_input_codepoints=100, max_upload_bytes=1_000_000
    )
    with TestClient(create_app(settings)) as c:
        yield c


@pytest.fixture
def td_client(migrated_db_url: str) -> Iterator[TestClient]:
    """Client with labelled TEST-DOUBLE adapters registered and the worker driven manually."""
    settings = Settings(
        database_url=migrated_db_url,
        max_upload_bytes=1_000_000,
        run_worker=False,
        device="cpu",
        enable_test_doubles=True,
    )
    with TestClient(create_app(settings)) as c:
        yield c
