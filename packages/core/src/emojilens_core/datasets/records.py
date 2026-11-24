"""Source record schema for JSONL dataset import (schema version 1)."""

from __future__ import annotations

from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator

from emojilens_core.multilingual import Variety
from emojilens_core.unicode import validate_unicode

SCHEMA_VERSION = 1
MAX_TEXT_CODEPOINTS = 20_000


class SafetyLabel(StrEnum):
    SAFE = "safe"
    UNSAFE = "unsafe"
    UNKNOWN = "unknown"


class ControlType(StrEnum):
    """Benign control categories. Controls are expected to be judged safe and not suspicious."""

    CLEAN = "clean"
    HEAVY_EMOJI = "heavy_emoji"
    INDIC_JOINER = "indic_joiner"
    CODE_MIXED = "code_mixed"
    IDENTITY = "identity"
    DECORATION = "decoration"


class SourceRecord(BaseModel):
    """One source line. ``text`` is stored exactly as given: never trimmed or normalized."""

    model_config = ConfigDict(extra="forbid", frozen=True, str_strip_whitespace=False)

    id: str = Field(min_length=1, max_length=128, pattern=r"^[A-Za-z0-9._:-]+$")
    text: str = Field(min_length=1)
    language: Variety
    source_group: str | None = Field(
        default=None, min_length=1, max_length=128, pattern=r"^[A-Za-z0-9._:-]+$"
    )
    safety_label: SafetyLabel = SafetyLabel.UNKNOWN
    control: ControlType | None = None
    origin: str = Field(min_length=1, max_length=256)
    license: str = Field(min_length=1, max_length=128)
    meta: dict[str, Any] = Field(default_factory=dict)

    @field_validator("text")
    @classmethod
    def _well_formed(cls, value: str) -> str:
        validate_unicode(value)
        if len(value) > MAX_TEXT_CODEPOINTS:
            raise ValueError(f"text exceeds {MAX_TEXT_CODEPOINTS} code points")
        return value

    @property
    def group(self) -> str:
        """Source group used for splitting. Defaults to the record id (a group of one)."""
        return self.source_group or self.id
