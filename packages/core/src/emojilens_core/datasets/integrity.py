"""Dataset hashing, manifests, duplicate detection, group-aware splits and leakage checks."""

from __future__ import annotations

import hashlib
import json
import re
import unicodedata
from collections import Counter, defaultdict
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from enum import StrEnum

from emojilens_core.datasets.records import SourceRecord

SPLIT_METHOD = "sha256-group-bucket/1"


class Split(StrEnum):
    TRAIN = "train"
    VALIDATION = "validation"
    TEST = "test"


def text_sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


_WS = re.compile(r"\s+")


def normalized_key(text: str) -> str:
    """Near-duplicate key: NFKC, casefold, collapsed whitespace. Used only for comparison."""
    return text_sha256(_WS.sub(" ", unicodedata.normalize("NFKC", text).casefold()).strip())


def canonical_line(record: SourceRecord) -> str:
    return json.dumps(
        record.model_dump(mode="json"), ensure_ascii=False, sort_keys=True, separators=(",", ":")
    )


def content_hash(records: Iterable[SourceRecord]) -> str:
    """Order-independent SHA-256 over canonical JSON lines sorted by id."""
    h = hashlib.sha256()
    for rec in sorted(records, key=lambda r: r.id):
        h.update(canonical_line(rec).encode("utf-8"))
        h.update(b"\n")
    return h.hexdigest()


@dataclass(frozen=True, slots=True)
class DuplicateGroup:
    kind: str  # "exact" | "normalized"
    ids: tuple[str, ...]


def find_duplicates(records: Sequence[SourceRecord]) -> list[DuplicateGroup]:
    exact: dict[str, list[str]] = defaultdict(list)
    norm: dict[str, list[str]] = defaultdict(list)
    for r in records:
        exact[text_sha256(r.text)].append(r.id)
        norm[normalized_key(r.text)].append(r.id)
    out = [DuplicateGroup("exact", tuple(ids)) for ids in exact.values() if len(ids) > 1]
    exact_sets = {frozenset(d.ids) for d in out}
    out += [
        DuplicateGroup("normalized", tuple(ids))
        for ids in norm.values()
        if len(ids) > 1 and frozenset(ids) not in exact_sets
    ]
    return sorted(out, key=lambda d: (d.kind, d.ids))


def assign_split(group: str, seed: int, ratios: tuple[float, float, float]) -> Split:
    """Deterministic split for a source group, independent of every other group.

    Hashes ``seed:group`` to a uniform value in [0, 1) and buckets it by the ratios, so adding
    records never moves existing groups, and every member of a group lands in the same split.
    """
    if abs(sum(ratios) - 1.0) > 1e-9 or any(r < 0 for r in ratios):
        raise ValueError("ratios must be non-negative and sum to 1")
    digest = hashlib.sha256(f"{seed}:{group}".encode()).digest()
    u = int.from_bytes(digest[:8], "big") / 2**64
    if u < ratios[0]:
        return Split.TRAIN
    if u < ratios[0] + ratios[1]:
        return Split.VALIDATION
    return Split.TEST


@dataclass(frozen=True, slots=True)
class LeakageRow:
    id: str
    group: str
    split: str | None
    text: str


@dataclass(frozen=True, slots=True)
class LeakageIssue:
    kind: str  # group_split_conflict | exact_text_across_splits | normalized_text_across_splits
    ids: tuple[str, ...]
    splits: tuple[str, ...]


def check_leakage(rows: Sequence[LeakageRow]) -> list[LeakageIssue]:
    issues: list[LeakageIssue] = []
    by_group: dict[str, list[LeakageRow]] = defaultdict(list)
    for r in rows:
        by_group[r.group].append(r)
    for members in by_group.values():
        splits = {m.split for m in members}
        if len(splits) > 1:
            issues.append(
                LeakageIssue(
                    "group_split_conflict",
                    tuple(sorted(m.id for m in members)),
                    tuple(sorted(str(s) for s in splits)),
                )
            )
    for kind, key in (
        ("exact_text_across_splits", lambda t: text_sha256(t)),
        ("normalized_text_across_splits", normalized_key),
    ):
        buckets: dict[str, list[LeakageRow]] = defaultdict(list)
        for r in rows:
            buckets[key(r.text)].append(r)
        for members in buckets.values():
            cross = {m.split for m in members if m.split is not None}
            if len(cross) > 1:
                issues.append(
                    LeakageIssue(kind, tuple(sorted(m.id for m in members)), tuple(sorted(cross)))
                )
    # A normalized collision that is also an exact one is reported once, as exact.
    exact_ids = {i.ids for i in issues if i.kind == "exact_text_across_splits"}
    return [
        i for i in issues if not (i.kind == "normalized_text_across_splits" and i.ids in exact_ids)
    ]


def distribution(values: Iterable[str | None]) -> dict[str, int]:
    return dict(sorted(Counter("(none)" if v is None else str(v) for v in values).items()))
