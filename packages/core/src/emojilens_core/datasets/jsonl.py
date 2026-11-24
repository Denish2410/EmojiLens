"""Strict JSONL parsing with line-numbered, non-echoing errors."""

from __future__ import annotations

import json
from dataclasses import dataclass

from pydantic import ValidationError

from emojilens_core.datasets.records import SourceRecord
from emojilens_core.unicode import InvalidUnicodeError


@dataclass(frozen=True, slots=True)
class LineError:
    line: int
    code: str
    message: str


@dataclass(frozen=True, slots=True)
class ParseResult:
    records: list[SourceRecord]
    errors: list[LineError]


class _StrictDecodeError(ValueError):
    pass


def _reject_constants(token: str) -> float:
    raise _StrictDecodeError(f"non-standard JSON constant {token}")


def parse_jsonl(data: bytes, *, max_records: int = 50_000, max_errors: int = 100) -> ParseResult:
    """Parse JSONL bytes into validated records.

    A UTF-8 byte order mark at the start of the file is accepted as file-encoding metadata.
    Error messages never include record text.
    """
    try:
        content = data.decode("utf-8-sig", errors="strict")
    except UnicodeDecodeError as exc:
        return ParseResult(
            [], [LineError(0, "invalid_utf8", f"File is not valid UTF-8 at byte {exc.start}.")]
        )

    records: list[SourceRecord] = []
    errors: list[LineError] = []
    seen_ids: dict[str, int] = {}
    for lineno, line in enumerate(content.split("\n"), 1):
        if len(errors) >= max_errors:
            errors.append(LineError(lineno, "too_many_errors", "Stopped after too many errors."))
            break
        if not line.strip():
            continue
        if len(records) >= max_records:
            errors.append(
                LineError(lineno, "too_many_records", f"More than {max_records} records.")
            )
            break
        try:
            obj = json.loads(line, parse_constant=_reject_constants)
        except (json.JSONDecodeError, _StrictDecodeError) as exc:
            errors.append(
                LineError(
                    lineno, "invalid_json", f"Invalid JSON at column {getattr(exc, 'colno', 0)}."
                )
            )
            continue
        if not isinstance(obj, dict):
            errors.append(LineError(lineno, "not_an_object", "Each line must be a JSON object."))
            continue
        try:
            record = SourceRecord.model_validate(obj)
        except ValidationError as exc:
            fields = sorted({".".join(str(p) for p in e["loc"]) or "(root)" for e in exc.errors()})
            unicode_failure = any(
                e.get("type") == "string_unicode" or "surrogate" in str(e.get("msg", ""))
                for e in exc.errors()
            )
            code = "invalid_unicode" if unicode_failure else "schema_error"
            errors.append(LineError(lineno, code, f"Invalid field(s): {', '.join(fields)}."))
            continue
        except InvalidUnicodeError:
            errors.append(LineError(lineno, "invalid_unicode", "Text contains a lone surrogate."))
            continue
        if record.id in seen_ids:
            errors.append(
                LineError(
                    lineno,
                    "duplicate_id",
                    f"Id '{record.id}' already used on line {seen_ids[record.id]}.",
                )
            )
            continue
        seen_ids[record.id] = lineno
        records.append(record)
    return ParseResult(records, errors)
