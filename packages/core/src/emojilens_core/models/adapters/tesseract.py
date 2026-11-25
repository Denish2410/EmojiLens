"""Tesseract OCR adapter (real, local inference via the tesseract CLI).

The binary is invoked with a fixed argument list (no shell). Image paths must point to an
existing regular file; callers restrict them to the artifacts directory.
"""

from __future__ import annotations

import csv
import io
import shutil
import subprocess
from functools import lru_cache
from pathlib import Path
from typing import Any

from emojilens_core.models.base import ModelAdapter
from emojilens_core.models.types import Capability, ErrorCode, ModelConfig, ModelError

TESSERACT_CONFIG = ModelConfig(
    key="tesseract-ocr",
    adapter="tesseract",
    model_id="tesseract",
    capabilities=(Capability.OCR,),
    task="ocr",
    license="Apache-2.0 (Tesseract); traineddata per tessdata license (Apache-2.0)",
    languages=("en", "hi", "gu"),
    params={"langs": "eng+hin+guj", "psm": 6, "timeout_s": 60},
    notes="Local CLI. Language packs: eng, hin, guj (guj may be missing; see availability).",
)


@lru_cache(maxsize=4)
def _cli(binary: str, *args: str) -> str:
    out = subprocess.run([binary, *args], capture_output=True, text=True, timeout=30, check=False)  # noqa: S603
    return out.stdout + out.stderr


class TesseractAdapter(ModelAdapter):
    adapter_version = "1.0.0"

    def __init__(self, config: ModelConfig, device: str = "cpu") -> None:
        super().__init__(config, "cpu")  # Tesseract is CPU-only
        self.binary = shutil.which(str(config.params.get("binary", "tesseract")))

    def installed_langs(self) -> list[str]:
        if not self.binary:
            return []
        lines = _cli(self.binary, "--list-langs").splitlines()
        return sorted(ln.strip() for ln in lines[1:] if ln.strip() and " " not in ln.strip())

    def requested_langs(self) -> list[str]:
        return str(self.config.params.get("langs", "eng")).split("+")

    def usable_langs(self) -> list[str]:
        have = set(self.installed_langs())
        return [lang for lang in self.requested_langs() if lang in have]

    def _check_dependencies(self) -> str | None:
        return None if self.binary else "tesseract binary not found on PATH"

    def _check_present(self) -> str | None:
        return None if self.usable_langs() else "no requested language pack installed"

    def _load(self) -> None:
        pass

    def library_versions(self) -> dict[str, str]:
        if not self.binary:
            return {}
        first = _cli(self.binary, "--version").splitlines()
        return {
            "tesseract": first[0].split()[-1] if first else "unknown",
            "langs": "+".join(self.usable_langs()),
        }

    def ocr(self, image_path: str, **params: Any) -> tuple[Any, dict[str, Any]]:
        path = Path(image_path)
        if not path.is_file():
            raise ModelError(ErrorCode.INFERENCE_FAILED, "image file not found")
        langs = "+".join(self.usable_langs())
        missing = sorted(set(self.requested_langs()) - set(self.usable_langs()))
        psm = int(params.get("psm", self.config.params.get("psm", 6)))
        timeout = float(params.get("timeout_s", self.config.params.get("timeout_s", 60)))
        assert self.binary is not None
        try:
            proc = subprocess.run(  # noqa: S603 - fixed argv, validated path
                [self.binary, str(path), "stdout", "-l", langs, "--psm", str(psm), "tsv"],
                capture_output=True,
                text=True,
                timeout=timeout,
                check=False,
            )
        except subprocess.TimeoutExpired as exc:
            raise ModelError(ErrorCode.TIMEOUT, f"tesseract exceeded {timeout}s") from exc
        if proc.returncode != 0:
            raise ModelError(ErrorCode.INFERENCE_FAILED, "tesseract returned an error")
        words, confs = [], []
        lines: dict[tuple[str, str, str], list[str]] = {}
        for row in csv.DictReader(io.StringIO(proc.stdout), delimiter="\t", quoting=csv.QUOTE_NONE):
            if row.get("level") == "5" and (row.get("text") or "").strip():
                key = (row["block_num"], row["par_num"], row["line_num"])
                lines.setdefault(key, []).append(row["text"])
                words.append(row["text"])
                conf = float(row.get("conf") or -1)
                if conf >= 0:
                    confs.append(conf)
        text = "\n".join(" ".join(ws) for ws in lines.values())
        normalized = {
            "text": text,
            "word_count": len(words),
            "mean_confidence": round(sum(confs) / len(confs), 2) if confs else None,
            "langs": langs,
            "missing_langs": missing,
            "psm": psm,
        }
        return {"tsv_rows": len(words)}, normalized
