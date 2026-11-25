from __future__ import annotations

from pathlib import Path

import pytest

from emojilens_core.repro.freeze import check, freeze, load_lock


def test_freeze_then_check_detects_modification_and_removal(tmp_path: Path) -> None:
    lock = tmp_path / "configs" / "LOCK.json"
    a, b = tmp_path / "a.json", tmp_path / "plan.md"
    a.write_text('{"x": 1}\n')
    b.write_text("plan\n")
    freeze(tmp_path, lock, [a, b], note="first")
    assert set(load_lock(lock)["files"]) == {"a.json", "plan.md"}
    assert check(tmp_path, lock) == []
    a.write_text('{"x": 2}\n')
    b.unlink()
    assert {(p.path, p.problem) for p in check(tmp_path, lock)} == {
        ("a.json", "modified"),
        ("plan.md", "missing"),
    }


def test_refreezing_a_changed_file_is_refused(tmp_path: Path) -> None:
    lock = tmp_path / "LOCK.json"
    a = tmp_path / "a.json"
    a.write_text("1")
    freeze(tmp_path, lock, [a])
    freeze(tmp_path, lock, [a])  # unchanged: no-op
    a.write_text("2")
    with pytest.raises(ValueError, match="add a new file"):
        freeze(tmp_path, lock, [a])


def test_unknown_lock_schema_is_rejected(tmp_path: Path) -> None:
    lock = tmp_path / "LOCK.json"
    lock.write_text('{"schema": "other", "files": {}}')
    with pytest.raises(ValueError, match="unsupported lock schema"):
        load_lock(lock)
