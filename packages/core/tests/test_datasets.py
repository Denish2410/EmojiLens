from __future__ import annotations

import json

import pytest
from hypothesis import given
from hypothesis import strategies as st

from emojilens_core.datasets import (
    LeakageRow,
    Split,
    assign_split,
    check_leakage,
    content_hash,
    find_duplicates,
    parse_jsonl,
)


def line(**kw: object) -> str:
    base: dict[str, object] = {
        "id": "r1",
        "text": "hello",
        "language": "en",
        "origin": "synthetic:test",
        "license": "CC0-1.0",
    }
    base.update(kw)
    return json.dumps(base, ensure_ascii=False)


def parse(*lines: str) -> tuple[list[str], list[tuple[int, str]]]:
    res = parse_jsonl("\n".join(lines).encode())
    return [r.id for r in res.records], [(e.line, e.code) for e in res.errors]


def test_valid_records_preserve_text_exactly() -> None:
    text = "  kal milte hain \u200d\U0001f44d\U0001f3fd \n"
    res = parse_jsonl(line(text=text, language="hi-Latn").encode())
    assert res.errors == []
    assert res.records[0].text == text


def test_errors_are_line_numbered_and_do_not_echo_text() -> None:
    secret = "do-not-echo-this"
    ids, errors = parse(
        line(id="a"),
        "{not json",
        line(id="b", language="fr", text=secret),
        line(id="c", extra=1),
        "[1, 2]",
        line(id="a"),
    )
    assert ids == ["a"]
    assert errors == [
        (2, "invalid_json"),
        (3, "schema_error"),
        (4, "schema_error"),
        (5, "not_an_object"),
        (6, "duplicate_id"),
    ]
    res = parse_jsonl(line(id="b", language="fr", text=secret).encode())
    assert all(secret not in e.message for e in res.errors)


def test_lone_surrogate_in_text_is_rejected() -> None:
    raw = '{"id":"x","text":"a\\ud800","language":"en","origin":"o","license":"l"}'
    _, errors = parse(raw)
    assert errors == [(1, "invalid_unicode")]


def test_invalid_utf8_file_rejected() -> None:
    res = parse_jsonl(b"\xff\xfe")
    assert [e.code for e in res.errors] == ["invalid_utf8"]


def test_bom_and_blank_lines_accepted() -> None:
    res = parse_jsonl(("\ufeff" + line() + "\n\n").encode())
    assert [r.id for r in res.records] == ["r1"]


def test_nan_constant_rejected() -> None:
    _, errors = parse(
        '{"id":"x","text":"a","language":"en","origin":"o","license":"l","meta":{"v":NaN}}'
    )
    assert errors == [(1, "invalid_json")]


def test_content_hash_is_order_independent_and_sensitive() -> None:
    a = parse_jsonl("\n".join([line(id="a"), line(id="b", text="x")]).encode()).records
    b = parse_jsonl("\n".join([line(id="b", text="x"), line(id="a")]).encode()).records
    c = parse_jsonl("\n".join([line(id="a"), line(id="b", text="x ")]).encode()).records
    assert content_hash(a) == content_hash(b)
    assert content_hash(a) != content_hash(c)


def test_duplicates_exact_and_normalized() -> None:
    recs = parse_jsonl(
        "\n".join(
            [
                line(id="a", text="Hello World"),
                line(id="b", text="Hello World"),
                line(id="c", text="hello   world"),
                line(id="d", text="\uff28ello world"),
                line(id="e", text="other"),
            ]
        ).encode()
    ).records
    dups = find_duplicates(recs)
    assert ("exact", ("a", "b")) in [(d.kind, d.ids) for d in dups]
    assert ("normalized", ("a", "b", "c", "d")) in [(d.kind, d.ids) for d in dups]


@given(st.text(min_size=1, max_size=40), st.integers(0, 2**31))
def test_split_assignment_is_deterministic(group: str, seed: int) -> None:
    ratios = (0.7, 0.15, 0.15)
    assert assign_split(group, seed, ratios) == assign_split(group, seed, ratios)


def test_split_ratios_roughly_respected() -> None:
    counts = {s: 0 for s in Split}
    for i in range(6000):
        counts[assign_split(f"g{i}", 13, (0.7, 0.15, 0.15))] += 1
    assert 0.67 < counts[Split.TRAIN] / 6000 < 0.73
    assert 0.12 < counts[Split.TEST] / 6000 < 0.18


def test_bad_ratios_rejected() -> None:
    with pytest.raises(ValueError, match="sum to 1"):
        assign_split("g", 1, (0.5, 0.5, 0.5))


def test_leakage_detects_group_conflicts_and_cross_split_text() -> None:
    rows = [
        LeakageRow("a", "g1", "train", "same text"),
        LeakageRow("b", "g1", "test", "different"),
        LeakageRow("c", "g2", "train", "Shared"),
        LeakageRow("d", "g3", "test", "Shared"),
        LeakageRow("e", "g4", "train", "near dup"),
        LeakageRow("f", "g5", "validation", "NEAR   dup"),
    ]
    kinds = {(i.kind, i.ids) for i in check_leakage(rows)}
    assert ("group_split_conflict", ("a", "b")) in kinds
    assert ("exact_text_across_splits", ("c", "d")) in kinds
    assert ("normalized_text_across_splits", ("e", "f")) in kinds
    assert ("normalized_text_across_splits", ("c", "d")) not in kinds


def test_group_aware_assignment_never_leaks() -> None:
    rows = [
        LeakageRow(
            f"r{i}", f"g{i // 3}", assign_split(f"g{i // 3}", 7, (0.6, 0.2, 0.2)).value, f"t{i}"
        )
        for i in range(300)
    ]
    assert check_leakage(rows) == []
