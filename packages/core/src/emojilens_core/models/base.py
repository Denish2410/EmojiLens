"""Abstract model adapter with lazy loading, availability detection and uniform results."""

from __future__ import annotations

import threading
import time
from abc import ABC, abstractmethod
from typing import Any

from emojilens_core.models.device import resources
from emojilens_core.models.types import (
    Availability,
    AvailabilityStatus,
    Capability,
    ErrorCode,
    InferenceResult,
    ModelConfig,
    ModelError,
    ModelMetadata,
    TokenTrace,
)
from emojilens_core.unicode import InvalidUnicodeError, validate_unicode


class ModelAdapter(ABC):
    """One model behind a capability-based interface.

    Subclasses implement ``_check_dependencies``, ``_check_present``, ``_load`` and the
    capability methods they support. ``load`` is lazy and thread-safe. ``run`` validates
    input, times the call and converts failures into structured errors.
    """

    adapter_version = "1.0.0"
    max_input_codepoints = 20_000

    def __init__(self, config: ModelConfig, device: str = "cpu") -> None:
        self.config = config
        self.device = device
        self._loaded = False
        self._lock = threading.Lock()

    # ------------------------------------------------------------------ lifecycle
    @abstractmethod
    def _check_dependencies(self) -> str | None:
        """Return a message if a required library or binary is missing."""

    @abstractmethod
    def _check_present(self) -> str | None:
        """Return a message if the model files are not available locally."""

    @abstractmethod
    def _load(self) -> None: ...

    def _unload(self) -> None:  # noqa: B027 - optional hook
        pass

    def availability(self) -> Availability:
        if (msg := self._check_dependencies()) is not None:
            return Availability(AvailabilityStatus.DEPENDENCY_MISSING, msg)
        if (msg := self._check_present()) is not None:
            return Availability(AvailabilityStatus.NOT_DOWNLOADED, msg)
        ram = resources().available_ram_gb
        if ram is not None and self.config.approx_ram_gb and ram < self.config.approx_ram_gb:
            return Availability(
                AvailabilityStatus.RESOURCES_INSUFFICIENT,
                f"needs ~{self.config.approx_ram_gb} GB RAM, {ram:.1f} GB available",
            )
        return Availability(AvailabilityStatus.AVAILABLE, "ready")

    @property
    def loaded(self) -> bool:
        return self._loaded

    def load(self) -> None:
        with self._lock:
            if self._loaded:
                return
            avail = self.availability()
            if not avail.ok:
                code = {
                    AvailabilityStatus.DEPENDENCY_MISSING: ErrorCode.DEPENDENCY_MISSING,
                    AvailabilityStatus.RESOURCES_INSUFFICIENT: ErrorCode.RESOURCES_INSUFFICIENT,
                }.get(avail.status, ErrorCode.MODEL_UNAVAILABLE)
                raise ModelError(code, f"{self.config.key}: {avail.detail}", model=self.config.key)
            self._load()
            self._loaded = True

    def unload(self) -> None:
        with self._lock:
            if self._loaded:
                self._unload()
                self._loaded = False

    # ------------------------------------------------------------------ metadata
    def library_versions(self) -> dict[str, str]:
        return {}

    def dtype(self) -> str | None:
        return None

    def metadata(self) -> ModelMetadata:
        return ModelMetadata(
            model_id=self.config.model_id,
            revision=self.config.revision,
            tokenizer_revision=self.config.tokenizer_revision,
            adapter=self.config.adapter,
            adapter_version=self.adapter_version,
            device=self.device,
            dtype=self.dtype(),
            library_versions=self.library_versions(),
            test_double=self.config.test_double,
        )

    # ------------------------------------------------------------------ capabilities
    def tokenize(self, text: str) -> TokenTrace:
        raise self._unsupported(Capability.TOKENIZE)

    def classify(self, text: str, **params: Any) -> tuple[Any, dict[str, Any]]:
        raise self._unsupported(Capability.CLASSIFY)

    def embed(self, text: str, **params: Any) -> tuple[Any, dict[str, Any]]:
        raise self._unsupported(Capability.EMBED)

    def generate(self, text: str, **params: Any) -> tuple[Any, dict[str, Any]]:
        raise self._unsupported(Capability.GENERATE)

    def ocr(self, image_path: str, **params: Any) -> tuple[Any, dict[str, Any]]:
        raise self._unsupported(Capability.OCR)

    def describe_image(
        self, image_path: str, prompt: str, **params: Any
    ) -> tuple[Any, dict[str, Any]]:
        raise self._unsupported(Capability.VISION_INPUT)

    def _unsupported(self, cap: Capability) -> ModelError:
        return ModelError(
            ErrorCode.CAPABILITY_UNSUPPORTED, f"{self.config.key} does not support {cap.value}"
        )

    # ------------------------------------------------------------------ uniform entry point
    def run(self, capability: Capability, payload: str, **params: Any) -> InferenceResult:
        """Run one capability and always return a result; failures are recorded, not raised."""
        if capability not in self.config.capabilities:
            raise self._unsupported(capability)
        start = time.perf_counter()
        raw: Any = None
        normalized: dict[str, Any] = {}
        trace: TokenTrace | None = None
        error: dict[str, Any] | None = None
        try:
            if capability not in (Capability.OCR, Capability.VISION_INPUT):
                validate_unicode(payload)
                if len(payload) > self.max_input_codepoints:
                    raise ModelError(ErrorCode.INPUT_TOO_LONG, "input exceeds adapter limit")
            self.load()
            if capability is Capability.TOKENIZE:
                trace = self.tokenize(payload)
                raw = trace.tokens
                normalized = {"length": trace.length, "unknown_tokens": trace.unknown_tokens}
            elif capability is Capability.CLASSIFY:
                raw, normalized = self.classify(payload, **params)
            elif capability is Capability.EMBED:
                raw, normalized = self.embed(payload, **params)
            elif capability is Capability.GENERATE:
                raw, normalized = self.generate(payload, **params)
            elif capability is Capability.OCR:
                raw, normalized = self.ocr(payload, **params)
            else:
                prompt = str(params.pop("prompt", ""))
                raw, normalized = self.describe_image(payload, prompt, **params)
        except ModelError as exc:
            error = exc.to_dict()
        except InvalidUnicodeError as exc:
            error = {"code": "invalid_unicode", "message": str(exc), "details": {}}
        except Exception as exc:  # recorded as a structured failure, never swallowed silently
            failure = f"{type(exc).__name__} during inference"
            error = ModelError(ErrorCode.INFERENCE_FAILED, failure).to_dict()
        return InferenceResult(
            capability=capability,
            raw_output=raw,
            normalized=normalized,
            latency_ms=round((time.perf_counter() - start) * 1000, 3),
            metadata=self.metadata(),
            params=dict(params),
            tokenization=trace,
            error=error,
        )
