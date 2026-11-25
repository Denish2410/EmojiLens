"""Preflight for the M4 validation workflow: is this machine ready to run real models?

    uv run python scripts/preflight.py            # checks only, no network
    uv run python scripts/preflight.py --network  # also probe huggingface.co (one HEAD request)
    uv run python scripts/preflight.py --json var/preflight.json

Writes nothing unless --json is given. The JSON holds versions, booleans and coarse hardware
facts only (no paths, user names or hostnames), so it can be attached to a validation report.
Exit status: 0 = pass, 1 = warnings only, 2 = a required check failed.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import UTC, datetime
from pathlib import Path

from emojilens_core.repro import environment_metadata, preflight_checks, summarize

ROOT = Path(__file__).resolve().parents[1]
PINS = ROOT / "var" / "model_pins.json"
MARK = {"pass": "PASS", "warn": "WARN", "fail": "FAIL", "skip": "skip"}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    ap.add_argument("--network", action="store_true", help="probe huggingface.co reachability")
    ap.add_argument("--json", type=Path, help="write environment + checks as JSON here")
    args = ap.parse_args()

    env = environment_metadata(ROOT)
    pins = json.loads(PINS.read_text("utf-8")).get("pins", {}) if PINS.is_file() else {}
    checks = preflight_checks(env, pins=pins, network=args.network)
    overall = summarize(checks)

    width = max(len(c.name) for c in checks)
    for c in checks:
        req = "required" if c.required else "optional"
        print(f"[{MARK[c.status]}] {c.name:<{width}}  {c.detail}  ({req})")
    print(f"\npreflight: {overall.upper()}")

    if args.json:
        args.json.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "schema": "emojilens.preflight/1",
            "created_at": datetime.now(UTC).isoformat(timespec="seconds"),
            "overall": overall,
            "environment": env,
            "checks": [c.to_dict() for c in checks],
        }
        args.json.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", "utf-8")
        print(f"wrote {args.json}")
    return {"pass": 0, "warn": 1, "fail": 2}[overall]


if __name__ == "__main__":
    sys.exit(main())
