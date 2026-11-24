"""Hugging Face adapters (classifier, embedding, generative, vision-language).

Safety rules: ``trust_remote_code=False`` always; ``local_files_only=True`` always (weights are
fetched only by the documented setup script after a resource check); an exact ``revision`` must
be pinned in the config, or the model is reported as not available.

These adapters have **not yet been verified with real weights** (no network access in the
development workspace). Their behaviour is covered by availability/contract tests only.
"""

from __future__ import annotations

import importlib.metadata
import importlib.util
from typing import Any

from emojilens_core.models.base import ModelAdapter
from emojilens_core.models.types import TokenTrace

REQUIRED = {
    "hf_classifier": ("torch", "transformers"),
    "hf_generative": ("torch", "transformers"),
    "hf_vlm": ("torch", "transformers"),
    "st_embedding": ("torch", "sentence_transformers"),
}


def _version(pkg: str) -> str:
    try:
        return importlib.metadata.version(pkg)
    except importlib.metadata.PackageNotFoundError:
        return "missing"


class _HFBase(ModelAdapter):
    _model: Any = None
    _tok: Any = None

    def _check_dependencies(self) -> str | None:
        missing = [m for m in REQUIRED[self.config.adapter] if importlib.util.find_spec(m) is None]
        return f"missing Python packages: {', '.join(missing)}" if missing else None

    def _check_present(self) -> str | None:
        if not self.config.revision:
            return "no exact revision pinned; run scripts/setup_models.py on the target machine"
        if importlib.util.find_spec("huggingface_hub") is None:
            return "huggingface_hub not installed"
        from huggingface_hub import try_to_load_from_cache

        hit = try_to_load_from_cache(
            self.config.model_id, "config.json", revision=self.config.revision
        )
        return (
            None
            if isinstance(hit, str)
            else "weights not in the local cache for the pinned revision"
        )

    def _kw(self) -> dict[str, Any]:
        return {
            "revision": self.config.revision,
            "local_files_only": True,
            "trust_remote_code": False,
        }

    def library_versions(self) -> dict[str, str]:
        return {p: _version(p) for p in ("torch", "transformers", "sentence-transformers")}

    def dtype(self) -> str | None:
        return str(getattr(self._model, "dtype", None)) if self._model is not None else None

    def _unload(self) -> None:
        self._model = None
        self._tok = None

    def tokenize(self, text: str) -> TokenTrace:
        enc = self._tok(text, return_offsets_mapping=True, add_special_tokens=False)
        ids = list(enc["input_ids"])
        offs = [tuple(o) if o[1] > o[0] else None for o in enc["offset_mapping"]]
        unk = getattr(self._tok, "unk_token_id", None)
        return TokenTrace(
            tokens=self._tok.convert_ids_to_tokens(ids),
            ids=ids,
            offsets=offs,
            unknown_tokens=sum(1 for i in ids if unk is not None and i == unk),
        )


class HFClassifierAdapter(_HFBase):
    def _load(self) -> None:
        from transformers import AutoModelForSequenceClassification, AutoTokenizer

        kw = self._kw()
        self._tok = AutoTokenizer.from_pretrained(
            self.config.model_id,
            **{**kw, "revision": self.config.tokenizer_revision or self.config.revision},
        )
        self._model = (
            AutoModelForSequenceClassification.from_pretrained(self.config.model_id, **kw)
            .to(self.device)
            .eval()
        )

    def classify(self, text: str, **params: Any) -> tuple[Any, dict[str, Any]]:
        import torch

        enc = self._tok(
            text,
            return_tensors="pt",
            truncation=True,
            max_length=int(params.get("max_length", 512)),
        )
        with torch.no_grad():
            probs = torch.softmax(self._model(**enc.to(self.device)).logits[0], dim=-1).tolist()
        labels = self._model.config.id2label
        scores = {str(labels[i]): float(p) for i, p in enumerate(probs)}
        label = max(scores, key=lambda k: scores[k])
        return {"scores": scores}, {"label": label, "score": scores[label], "calibrated": False}


class STEmbeddingAdapter(_HFBase):
    def _load(self) -> None:
        from sentence_transformers import SentenceTransformer

        self._model = SentenceTransformer(
            self.config.model_id,
            device=self.device,
            revision=self.config.revision,
            local_files_only=True,
            trust_remote_code=False,
        )
        self._tok = self._model.tokenizer

    def embed(self, text: str, **params: Any) -> tuple[Any, dict[str, Any]]:
        vec = self._model.encode([text], normalize_embeddings=True)[0].tolist()
        return vec, {"dim": len(vec), "normalized": True}


class HFGenerativeAdapter(_HFBase):
    def _load(self) -> None:
        from transformers import AutoModelForCausalLM, AutoTokenizer

        kw = self._kw()
        self._tok = AutoTokenizer.from_pretrained(self.config.model_id, **kw)
        self._model = (
            AutoModelForCausalLM.from_pretrained(self.config.model_id, **kw).to(self.device).eval()
        )

    def generate(self, text: str, **params: Any) -> tuple[Any, dict[str, Any]]:
        import torch

        max_new = int(params.get("max_new_tokens", 64))
        if getattr(self._tok, "chat_template", None):
            prompt = self._tok.apply_chat_template(
                [{"role": "user", "content": text}], tokenize=False, add_generation_prompt=True
            )
        else:
            prompt = text
        enc = self._tok(prompt, return_tensors="pt").to(self.device)
        with torch.no_grad():
            out = self._model.generate(**enc, max_new_tokens=max_new, do_sample=False)
        completion = self._tok.decode(out[0][enc["input_ids"].shape[1] :], skip_special_tokens=True)
        return completion, {"text": completion, "max_new_tokens": max_new, "greedy": True}


class HFVisionLanguageAdapter(_HFBase):
    def _load(self) -> None:
        from transformers import AutoModelForVision2Seq, AutoProcessor

        kw = self._kw()
        self._tok = AutoProcessor.from_pretrained(self.config.model_id, **kw)
        self._model = (
            AutoModelForVision2Seq.from_pretrained(self.config.model_id, **kw)
            .to(self.device)
            .eval()
        )

    def describe_image(
        self, image_path: str, prompt: str, **params: Any
    ) -> tuple[Any, dict[str, Any]]:
        import torch
        from PIL import Image

        image = Image.open(image_path).convert("RGB")
        messages = [
            {"role": "user", "content": [{"type": "image"}, {"type": "text", "text": prompt}]}
        ]
        chat = self._tok.apply_chat_template(messages, add_generation_prompt=True)
        enc = self._tok(text=chat, images=[image], return_tensors="pt").to(self.device)
        with torch.no_grad():
            out = self._model.generate(
                **enc, max_new_tokens=int(params.get("max_new_tokens", 96)), do_sample=False
            )
        text = self._tok.batch_decode(
            out[:, enc["input_ids"].shape[1] :], skip_special_tokens=True
        )[0]
        return text, {"text": text, "greedy": True}
