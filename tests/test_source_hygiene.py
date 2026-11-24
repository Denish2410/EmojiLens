"""Repository guard: no raw invisible, bidi or confusable characters in source code."""

from __future__ import annotations

import importlib.util
import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("source_hygiene", ROOT / "scripts/source_hygiene.py")
assert spec is not None
assert spec.loader is not None
hygiene = importlib.util.module_from_spec(spec)
spec.loader.exec_module(hygiene)


def test_detector_flags_hidden_characters() -> None:
    assert hygiene.dangerous("\u200b")
    assert hygiene.dangerous("\u202e")
    assert hygiene.dangerous("\U000e0041")
    assert hygiene.dangerous("\u0430")
    assert not hygiene.dangerous("a")
    assert not hygiene.dangerous("क")  # Devanagari is readable, not flagged


def test_repository_sources_are_clean() -> None:
    dirty = {str(p): hygiene.findings(p) for p in hygiene.source_files()}
    assert {k: v for k, v in dirty.items() if v} == {}
