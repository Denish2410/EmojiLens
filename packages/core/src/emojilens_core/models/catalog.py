"""Candidate model catalogue for the Apple Silicon M4 target (selection rationale in
docs/MODEL_SETUP_M4.md). Revisions are ``None`` until pinned on the target machine by
``scripts/setup_models.py``, which records the exact commit it downloaded. Licenses marked
"verify" must be checked on the model card before download.
"""

from __future__ import annotations

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


def default_registry(device: str = "cpu", max_loaded: int = 2) -> ModelRegistry:
    reg = ModelRegistry(device=device, max_loaded=max_loaded)
    for name, factory in ADAPTERS.items():
        reg.register_adapter(name, factory)
    for cfg in CATALOG:
        reg.add(cfg)
    return reg
