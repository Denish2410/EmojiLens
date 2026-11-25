"""Freezing research configurations: a lock file of SHA-256 digests that CI re-verifies.

A frozen file may not change. To change a frozen config, add a new file (and log the deviation in
the analysis plan) rather than editing the old one. Digests are over the exact bytes on disk.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

LOCK_SCHEMA = "emojilens.lock/1"


@dataclass(frozen=True, slots=True)
class LockProblem:
    path: str
    problem: str  # "missing" | "modified"


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_lock(lock_path: Path) -> dict[str, Any]:
    if not lock_path.is_file():
        return {"schema": LOCK_SCHEMA, "files": {}}
    data: dict[str, Any] = json.loads(lock_path.read_text("utf-8"))
    if data.get("schema") != LOCK_SCHEMA:
        raise ValueError(f"unsupported lock schema: {data.get('schema')!r}")
    return data


def freeze(root: Path, lock_path: Path, files: list[Path], *, note: str = "") -> dict[str, Any]:
    """Add files to the lock. Re-freezing an unchanged file is a no-op; a changed one is refused."""
    lock = load_lock(lock_path)
    for f in files:
        rel = f.resolve().relative_to(root.resolve()).as_posix()
        d = digest(f)
        prev = lock["files"].get(rel)
        if prev and prev["sha256"] != d:
            raise ValueError(f"{rel} is already frozen with a different digest; add a new file")
        if not prev:
            lock["files"][rel] = {
                "sha256": d,
                "frozen_at": datetime.now(UTC).isoformat(timespec="seconds"),
                "note": note,
            }
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    lock_path.write_text(json.dumps(lock, indent=2, sort_keys=True) + "\n", "utf-8")
    return lock


def check(root: Path, lock_path: Path) -> list[LockProblem]:
    problems = []
    for rel, entry in sorted(load_lock(lock_path)["files"].items()):
        p = root / rel
        if not p.is_file():
            problems.append(LockProblem(rel, "missing"))
        elif digest(p) != entry["sha256"]:
            problems.append(LockProblem(rel, "modified"))
    return problems
