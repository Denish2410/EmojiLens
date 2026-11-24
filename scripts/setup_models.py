"""Download catalogue models on the target machine and pin their exact revisions.

Run on the Apple Silicon M4 (see docs/MODEL_SETUP_M4.md). For each selected model it:
1. checks free disk against the catalogue estimate (with a 2x safety margin),
2. resolves the repository's current commit SHA via the Hub API,
3. downloads exactly that commit (snapshot_download, no remote code is executed),
4. records {key: {revision, tokenizer_revision, model_id}} in var/model_pins.json.

    uv run python scripts/setup_models.py --list
    uv run python scripts/setup_models.py embed-multilingual-minilm gen-qwen2.5-0.5b-instruct
Requires: uv sync --all-packages --extra models (torch, transformers, sentence-transformers,
huggingface_hub) and network access to huggingface.co.
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
from datetime import UTC, datetime
from pathlib import Path

from emojilens_core.models.catalog import CATALOG
from emojilens_core.models.device import model_cache_dir

PINS = Path(__file__).resolve().parents[1] / "var" / "model_pins.json"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("keys", nargs="*")
    ap.add_argument("--list", action="store_true")
    args = ap.parse_args()
    hf = {c.key: c for c in CATALOG if c.adapter != "tesseract"}
    if args.list or not args.keys:
        for c in hf.values():
            size = f"~{c.approx_disk_gb} GB disk  ~{c.approx_ram_gb} GB RAM"
            print(f"{c.key:32} {c.model_id:55} {size}  {c.license}")
        return 0
    try:
        from huggingface_hub import HfApi, snapshot_download
    except ImportError:
        print(
            "huggingface_hub is not installed: uv sync --all-packages --extra models",
            file=sys.stderr,
        )
        return 2
    pins = json.loads(PINS.read_text()) if PINS.exists() else {"pins": {}}
    cache = model_cache_dir()
    cache.mkdir(parents=True, exist_ok=True)
    for key in args.keys:
        cfg = hf.get(key)
        if cfg is None:
            print(f"unknown model key: {key}", file=sys.stderr)
            return 2
        free_gb = shutil.disk_usage(cache).free / 1e9
        if free_gb < 2 * cfg.approx_disk_gb:
            print(
                f"{key}: needs ~{cfg.approx_disk_gb} GB (x2 margin), only {free_gb:.1f} GB free",
                file=sys.stderr,
            )
            return 3
        sha = HfApi().model_info(cfg.model_id).sha
        if not sha:
            print(f"{key}: could not resolve a commit SHA", file=sys.stderr)
            return 4
        print(f"{key}: downloading {cfg.model_id}@{sha}")
        snapshot_download(cfg.model_id, revision=sha)
        pins["pins"][key] = {
            "model_id": cfg.model_id,
            "revision": sha,
            "tokenizer_revision": sha,
            "pinned_at": datetime.now(UTC).isoformat(),
        }
    PINS.parent.mkdir(parents=True, exist_ok=True)
    PINS.write_text(json.dumps(pins, indent=2) + "\n")
    print(f"pins written to {PINS}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
