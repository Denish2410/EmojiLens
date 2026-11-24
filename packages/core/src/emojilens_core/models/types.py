"""Model adapter contracts: capabilities, configuration, metadata, results and errors."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any


class Capability(StrEnum):
    TOKENIZE = "TOKENIZE"
    CLASSIFY = "CLASSIFY"
    EMBED = "EMBED"
    GENERATE = "GENERATE"
    VISION_INPUT = "VISION_INPUT"
    OCR = "OCR"


class ErrorCode(StrEnum):
    MODEL_UNAVAILABLE = "model_unavailable"
    DEPENDENCY_MISSING = "dependency_missing"
    CAPABILITY_UNSUPPORTED = "capability_unsupported"
    RESOURCES_INSUFFICIENT = "resources_insufficient"
    INPUT_TOO_LONG = "input_too_long"
    INFERENCE_FAILED = "inference_failed"
    TIMEOUT = "timeout"


class ModelError(Exception):
    """Structured inference error. ``code`` is stable; ``message`` is safe to show."""

    def __init__(self, code: ErrorCode, message: str, **details: Any) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.details = details

    def to_dict(self) -> dict[str, Any]:
        return {"code": self.code.value, "message": self.message, "details": self.details}


@dataclass(frozen=True, slots=True)
class ModelConfig:
    """Declarative model entry. ``revision`` pins an exact commit; None means not yet pinned."""

    key: str
    adapter: str
    model_id: str
    capabilities: tuple[Capability, ...]
    license: str
    revision: str | None = None
    tokenizer_revision: str | None = None
    languages: tuple[str, ...] = ()
    approx_ram_gb: float = 0.0
    approx_disk_gb: float = 0.0
    params: dict[str, Any] = field(default_factory=dict)
    notes: str = ""
    test_double: bool = False


@dataclass(frozen=True, slots=True)
class ModelMetadata:
    model_id: str
    revision: str | None
    tokenizer_revision: str | None
    adapter: str
    adapter_version: str
    device: str
    dtype: str | None
    library_versions: dict[str, str]
    test_double: bool


@dataclass(frozen=True, slots=True)
class TokenTrace:
    """Tokenization trace. ``offsets`` are code point spans into the input (None if unknown)."""

    tokens: list[str]
    ids: list[int]
    offsets: list[tuple[int, int] | None]
    unknown_tokens: int

    @property
    def length(self) -> int:
        return len(self.tokens)


class AvailabilityStatus(StrEnum):
    AVAILABLE = "available"
    NOT_DOWNLOADED = "not_downloaded"
    DEPENDENCY_MISSING = "dependency_missing"
    RESOURCES_INSUFFICIENT = "resources_insufficient"


@dataclass(frozen=True, slots=True)
class Availability:
    status: AvailabilityStatus
    detail: str

    @property
    def ok(self) -> bool:
        return self.status is AvailabilityStatus.AVAILABLE


@dataclass(frozen=True, slots=True)
class InferenceResult:
    capability: Capability
    raw_output: Any
    normalized: dict[str, Any]
    latency_ms: float
    metadata: ModelMetadata
    params: dict[str, Any]
    tokenization: TokenTrace | None = None
    error: dict[str, Any] | None = None
