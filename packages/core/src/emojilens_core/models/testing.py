"""TEST DOUBLES for automated tests only.

Every config built here has ``test_double=True`` and a ``test-double/`` model id. Results from
these adapters are never real model predictions and must never be displayed or reported as such.
The API refuses to register them unless ``EMOJILENS_ENABLE_TEST_DOUBLES`` is set (tests only).
"""

from __future__ import annotations

import hashlib
from typing import Any

from emojilens_core.models.base import ModelAdapter
from emojilens_core.models.types import Capability, ModelConfig, TokenTrace


class TestDoubleAdapter(ModelAdapter):
    """Deterministic, input-hash-based fake outputs. Not a model."""

    __test__ = False  # keep pytest from collecting this class

    def _check_dependencies(self) -> str | None:
        return None

    def _check_present(self) -> str | None:
        return None if self.config.params.get("present", True) else "test double marked absent"

    def _load(self) -> None:
        if self.config.params.get("fail_load"):
            raise RuntimeError("simulated load failure")

    def _h(self, text: str) -> int:
        return int(hashlib.sha256(text.encode()).hexdigest()[:8], 16)

    def tokenize(self, text: str) -> TokenTrace:
        toks, offs, pos = [], [], 0
        for part in text.split(" "):
            if part:
                toks.append(part)
                offs.append((pos, pos + len(part)))
            pos += len(part) + 1
        return TokenTrace(toks, [self._h(t) % 30000 for t in toks], list(offs), 0)

    def classify(self, text: str, **params: Any) -> tuple[Any, dict[str, Any]]:
        score = (self._h(text) % 1000) / 1000
        label = "flagged" if score >= 0.5 else "ok"
        return {"scores": {"flagged": score, "ok": 1 - score}}, {"label": label, "score": score}

    def embed(self, text: str, **params: Any) -> tuple[Any, dict[str, Any]]:
        h = hashlib.sha256(text.encode()).digest()
        vec = [b / 255 - 0.5 for b in h[:16]]
        return vec, {"dim": len(vec)}

    def generate(self, text: str, **params: Any) -> tuple[Any, dict[str, Any]]:
        if "refuse" in text.lower():
            out = "I can't help with that request."
        elif "boom" in text.lower():
            raise RuntimeError("simulated inference failure")
        else:
            out = f"echo:{text[:40]}"
        return out, {"text": out}


def make_test_double_config(key: str = "test-double-all", **params: Any) -> ModelConfig:
    return ModelConfig(
        key=key,
        adapter="test_double",
        model_id=f"test-double/{key}",
        capabilities=(
            Capability.TOKENIZE,
            Capability.CLASSIFY,
            Capability.EMBED,
            Capability.GENERATE,
        ),
        license="n/a (test double)",
        task="safety",  # simulated safety classifier, for automated tests only
        revision="test-double",
        params=params,
        notes="TEST DOUBLE: not a model; for automated tests only.",
        test_double=True,
    )
