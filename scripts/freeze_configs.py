"""Freeze research configurations and verify that frozen files have not changed.

    uv run python scripts/freeze_configs.py validate research/configs/h4.json
    uv run python scripts/freeze_configs.py freeze research/ANALYSIS_PLAN.md \
        research/configs/h4.json --note "H4 confirmatory run"
    uv run python scripts/freeze_configs.py check      # CI: fails if a frozen file changed

The lock is research/configs/LOCK.json. A config is validated against the API's experiment schema
before it can be frozen. A label map is accepted only for models whose task is `safety`.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from pydantic import ValidationError

from emojilens_api.routers.experiments import ExperimentIn
from emojilens_core.models import SAFETY_TASK
from emojilens_core.models.catalog import CATALOG
from emojilens_core.repro.freeze import check, freeze

ROOT = Path(__file__).resolve().parents[1]
LOCK = ROOT / "research" / "configs" / "LOCK.json"
META_KEYS = {"hypothesis", "card", "description"}


def validate(path: Path) -> list[str]:
    try:
        data = json.loads(path.read_text("utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return [f"{path}: unreadable ({type(exc).__name__})"]
    errors: list[str] = []
    if not str(data.get("hypothesis", "")).strip():
        errors.append(f"{path}: 'hypothesis' is required (an H-id or 'exploratory')")
    body = {k: v for k, v in data.items() if k not in META_KEYS}
    try:
        cfg = ExperimentIn.model_validate(body)
    except ValidationError as exc:
        return errors + [f"{path}: {e['loc']}: {e['msg']}" for e in exc.errors()]
    catalog = {c.key: c for c in CATALOG}
    for key in cfg.model_keys:
        if key not in catalog:
            errors.append(f"{path}: unknown model '{key}'")
        elif cfg.label_map and catalog[key].task != SAFETY_TASK and "CLASSIFY" in cfg.capabilities:
            errors.append(f"{path}: label_map given but '{key}' is a {catalog[key].task} model")
    return errors


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    v = sub.add_parser("validate")
    v.add_argument("files", nargs="+", type=Path)
    f = sub.add_parser("freeze")
    f.add_argument("files", nargs="+", type=Path)
    f.add_argument("--note", default="")
    sub.add_parser("check")
    args = ap.parse_args()

    if args.cmd == "check":
        problems = check(ROOT, LOCK)
        for p in problems:
            print(f"FROZEN FILE {p.problem.upper()}: {p.path}", file=sys.stderr)
        print("lock ok" if not problems else f"{len(problems)} problem(s)")
        return 1 if problems else 0

    errors = [e for p in args.files if p.suffix == ".json" for e in validate(p)]
    for e in errors:
        print(e, file=sys.stderr)
    if errors:
        return 1
    if args.cmd == "validate":
        print(f"{len(args.files)} file(s) valid")
        return 0
    try:
        freeze(ROOT, LOCK, args.files, note=args.note)
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 1
    print(f"froze {len(args.files)} file(s) into {LOCK.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
