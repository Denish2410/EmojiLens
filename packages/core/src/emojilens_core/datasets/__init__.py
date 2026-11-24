"""Dataset management: schema, strict JSONL import, integrity, splits and leakage checks."""

from emojilens_core.datasets.integrity import (
    SPLIT_METHOD,
    DuplicateGroup,
    LeakageIssue,
    LeakageRow,
    Split,
    assign_split,
    check_leakage,
    content_hash,
    distribution,
    find_duplicates,
    normalized_key,
    text_sha256,
)
from emojilens_core.datasets.jsonl import LineError, ParseResult, parse_jsonl
from emojilens_core.datasets.records import (
    SCHEMA_VERSION,
    ControlType,
    SafetyLabel,
    SourceRecord,
)

__all__ = [
    "SCHEMA_VERSION",
    "SPLIT_METHOD",
    "ControlType",
    "DuplicateGroup",
    "LeakageIssue",
    "LeakageRow",
    "LineError",
    "ParseResult",
    "SafetyLabel",
    "SourceRecord",
    "Split",
    "assign_split",
    "check_leakage",
    "content_hash",
    "distribution",
    "find_duplicates",
    "normalized_key",
    "parse_jsonl",
    "text_sha256",
]
