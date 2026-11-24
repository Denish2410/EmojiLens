"""Model registry: configuration-driven, lazy construction, bounded number of loaded models."""

from __future__ import annotations

from collections import OrderedDict
from collections.abc import Callable
from typing import Any

from emojilens_core.models.base import ModelAdapter
from emojilens_core.models.types import (
    Availability,
    Capability,
    ErrorCode,
    InferenceResult,
    ModelConfig,
    ModelError,
)

AdapterFactory = Callable[[ModelConfig, str], ModelAdapter]


class ModelRegistry:
    def __init__(self, device: str = "cpu", max_loaded: int = 2) -> None:
        self.device = device
        self.max_loaded = max_loaded
        self._configs: dict[str, ModelConfig] = {}
        self._factories: dict[str, AdapterFactory] = {}
        self._adapters: OrderedDict[str, ModelAdapter] = OrderedDict()

    def register_adapter(self, name: str, factory: AdapterFactory) -> None:
        self._factories[name] = factory

    def add(self, config: ModelConfig) -> None:
        if config.adapter not in self._factories:
            raise ValueError(f"no adapter '{config.adapter}' registered for {config.key}")
        self._configs[config.key] = config

    def configs(self) -> list[ModelConfig]:
        return list(self._configs.values())

    def config(self, key: str) -> ModelConfig:
        if key not in self._configs:
            raise ModelError(ErrorCode.MODEL_UNAVAILABLE, f"unknown model '{key}'")
        return self._configs[key]

    def adapter(self, key: str) -> ModelAdapter:
        """Return the adapter (constructed lazily; weights load on first use)."""
        cfg = self.config(key)
        if key not in self._adapters:
            self._adapters[key] = self._factories[cfg.adapter](cfg, self.device)
        self._adapters.move_to_end(key)
        self._evict()
        return self._adapters[key]

    def run(self, key: str, capability: Capability, payload: str, **params: Any) -> InferenceResult:
        """Run a capability, then enforce the loaded-model bound (most recent stays loaded)."""
        result = self.adapter(key).run(capability, payload, **params)
        self._evict()
        return result

    def _evict(self) -> None:
        loaded = [k for k, a in self._adapters.items() if a.loaded]
        while len(loaded) > self.max_loaded:
            self._adapters[loaded.pop(0)].unload()

    def availability(self, key: str) -> Availability:
        return self.adapter(key).availability()

    def unload_all(self) -> None:
        for a in self._adapters.values():
            a.unload()
