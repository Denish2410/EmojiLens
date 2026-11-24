"""Candidate model catalogue for the Apple Silicon M4 target (selection rationale in
docs/MODEL_SETUP_M4.md). Revisions are ``None`` until pinned on the target machine by
``scripts/setup_models.py``, which records the exact commit it downloaded. Licenses marked
"verify" must be checked on the model card before download.
"""

from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path

from emojilens_core.models.adapters.huggingface import (
    HFClassifierAdapter,
    HFGenerativeAdapter,
    HFVisionLanguageAdapter,
    STEmbeddingAdapter,
)
from emojilens_core.models.adapters.tesseract import TESSERACT_CONFIG, TesseractAdapter
from emojilens_core.models.registry import ModelRegistry
from emojilens_core.models.types import Capability, ModelConfig

CATALOG: tuple[ModelConfig, ...] = (
    ModelConfig(
        key="classifier-xlmr-sentiment",
        adapter="hf_classifier",
        model_id="cardiffnlp/twitter-xlm-roberta-base-sentiment",
        capabilities=(Capability.TOKENIZE, Capability.CLASSIFY),
        license="verify on model card before download",
        languages=("en", "hi"),
        approx_ram_gb=1.5,
        approx_disk_gb=1.1,
        notes="Multilingual XLM-R sequence classifier: a candidate surrogate-task classifier. "
        "Gujarati coverage comes from XLM-R pretraining only.",
    ),
    ModelConfig(
        key="embed-multilingual-minilm",
        adapter="st_embedding",
        model_id="sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",
        capabilities=(Capability.TOKENIZE, Capability.EMBED),
        license="Apache-2.0 (verify)",
        languages=("en", "hi", "gu"),
        approx_ram_gb=1.0,
        approx_disk_gb=0.5,
    ),
    ModelConfig(
        key="gen-qwen2.5-0.5b-instruct",
        adapter="hf_generative",
        model_id="Qwen/Qwen2.5-0.5B-Instruct",
        capabilities=(Capability.TOKENIZE, Capability.GENERATE),
        license="Apache-2.0 (verify)",
        languages=("en", "hi"),
        approx_ram_gb=2.5,
        approx_disk_gb=1.0,
        params={"max_new_tokens": 64},
    ),
    TESSERACT_CONFIG,
    ModelConfig(
        key="vlm-smolvlm-256m",
        adapter="hf_vlm",
        model_id="HuggingFaceTB/SmolVLM-256M-Instruct",
        capabilities=(Capability.VISION_INPUT,),
        license="Apache-2.0 (verify)",
        languages=("en",),
        approx_ram_gb=2.0,
        approx_disk_gb=0.6,
        notes="Smallest candidate VLM; multilingual reading of Indic scripts is not expected.",
    ),
)

ADAPTERS = {
    "hf_classifier": HFClassifierAdapter,
    "st_embedding": STEmbeddingAdapter,
    "hf_generative": HFGenerativeAdapter,
    "hf_vlm": HFVisionLanguageAdapter,
    "tesseract": TesseractAdapter,
}


def load_pins(path: Path | None) -> dict[str, dict[str, str]]:
    """Read revisions pinned by scripts/setup_models.py ({key: {revision, tokenizer_revision}})."""
    if path is None or not path.is_file():
        return {}
    data = json.loads(path.read_text("utf-8"))
    return {
        k: v for k, v in data.get("pins", {}).items() if isinstance(v, dict) and v.get("revision")
    }


def default_registry(
    device: str = "cpu", max_loaded: int = 2, pins_path: Path | None = None
) -> ModelRegistry:
    reg = ModelRegistry(device=device, max_loaded=max_loaded)
    for name, factory in ADAPTERS.items():
        reg.register_adapter(name, factory)
    pins = load_pins(pins_path)
    for cfg in CATALOG:
        pin = pins.get(cfg.key)
        if pin:
            cfg = replace(
                cfg,
                revision=pin["revision"],
                tokenizer_revision=pin.get("tokenizer_revision") or pin["revision"],
            )
        reg.add(cfg)
    return reg
