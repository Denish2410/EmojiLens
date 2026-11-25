"""M4 model validation: preflight, then smoke-run every installed model on all five varieties.

    uv run python scripts/validate_models.py                 # all catalogue models
    uv run python scripts/validate_models.py embed-multilingual-minilm tesseract-ocr
    uv run python scripts/validate_models.py --network       # also probe huggingface.co

Writes var/validation/<UTC timestamp>/{report.md, validation.json}. Models that are not installed
are recorded as skipped with the registry's reason; nothing is filled in. Copy the summary table
into docs/TEST_REPORT.md only after reading the report.
Exit status: 0 if every probe of every available model executed, 1 otherwise.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import UTC, datetime
from pathlib import Path

from emojilens_core.models.catalog import default_registry
from emojilens_core.models.device import select_device
from emojilens_core.repro import environment_metadata, preflight_checks, summarize
from emojilens_core.repro.validation import (
    Renderer,
    render_markdown,
    report_to_dict,
    validate_model,
)

ROOT = Path(__file__).resolve().parents[1]
PINS = ROOT / "var" / "model_pins.json"


def _renderer() -> Renderer | None:
    try:
        from emojilens_core.multimodal import render_chromium
    except ImportError:
        return None

    def render(text: str, out_dir: Path) -> str:
        return render_chromium(text, out_dir).image_path

    return render


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    ap.add_argument("keys", nargs="*", help="catalogue keys (default: all)")
    ap.add_argument("--network", action="store_true")
    ap.add_argument("--device", default="auto", choices=("auto", "cpu", "mps", "cuda"))
    ap.add_argument("--out", type=Path, default=ROOT / "var" / "validation")
    args = ap.parse_args()

    env = environment_metadata(ROOT, args.device)
    pins = json.loads(PINS.read_text("utf-8")).get("pins", {}) if PINS.is_file() else {}
    checks = preflight_checks(env, pins=pins, network=args.network)
    device = select_device(args.device).device
    registry = default_registry(device=device, max_loaded=1, pins_path=PINS)
    keys = args.keys or [c.key for c in registry.configs()]
    unknown = sorted(set(keys) - {c.key for c in registry.configs()})
    if unknown:
        print(f"unknown model keys: {', '.join(unknown)}", file=sys.stderr)
        return 2

    renderer = _renderer()
    reports = []
    for key in keys:
        print(f"validating {key} ...", flush=True)
        reports.append(validate_model(registry, key, renderer=renderer))
        registry.unload_all()

    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    out = args.out / stamp
    out.mkdir(parents=True, exist_ok=True)
    check_dicts = [c.to_dict() for c in checks]
    (out / "validation.json").write_text(
        json.dumps(
            {
                "schema": "emojilens.validation/1",
                "created_at": stamp,
                "preflight": summarize(checks),
                "environment": env,
                "checks": check_dicts,
                "models": report_to_dict(reports),
            },
            indent=2,
            ensure_ascii=False,
            sort_keys=True,
        )
        + "\n",
        "utf-8",
    )
    (out / "report.md").write_text(render_markdown(reports, env, check_dicts), "utf-8")

    for r in reports:
        skipped = len(r.probes) - r.executed - r.failed
        print(f"{r.key:32} executed={r.executed:<3} failed={r.failed:<3} skipped={skipped}")
    print(f"wrote {out / 'report.md'}")
    complete = all(r.failed == 0 for r in reports) and any(r.executed for r in reports)
    return 0 if complete else 1


if __name__ == "__main__":
    sys.exit(main())
