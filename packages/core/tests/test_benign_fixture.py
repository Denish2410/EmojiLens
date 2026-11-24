"""Benign controls must never be escalated above informational by the evidence classifier."""

from __future__ import annotations

import pathlib

import pytest

from emojilens_core.datasets import parse_jsonl
from emojilens_core.multilingual import identify
from emojilens_core.unicode import analyze
from emojilens_core.unicode.evidence import CATEGORY_ORDER, Category

FIXTURE = (
    pathlib.Path(__file__).resolve().parents[3]
    / "datasets/fixtures/benign_controls.synthetic.jsonl"
)
RECORDS = parse_jsonl(FIXTURE.read_bytes()).records


def test_fixture_parses_cleanly() -> None:
    result = parse_jsonl(FIXTURE.read_bytes())
    assert result.errors == []
    assert len(result.records) >= 25
    assert {r.language.value for r in result.records} == {"en", "hi", "gu", "hi-Latn", "gu-Latn"}
    assert all(r.origin.startswith("synthetic:") for r in result.records)


@pytest.mark.parametrize("record", RECORDS, ids=[r.id for r in RECORDS])
def test_benign_control_not_escalated(record: object) -> None:
    text = record.text  # type: ignore[attr-defined]
    worst = max(
        (CATEGORY_ORDER[e.category] for e in analyze(text).evidence),
        default=0,
    )
    assert worst <= CATEGORY_ORDER[Category.INFORMATIONAL], record.id  # type: ignore[attr-defined]
    identify(text)  # must not raise
