"""Generate the research report from stored outputs of eligible runs only.

    uv run python scripts/generate_report.py                # uses EMOJILENS_DATABASE_URL
    uv run python scripts/generate_report.py --out var/reports

Writes <out>/<UTC stamp>/{report.md, report.json}. Ineligible runs appear only in the screening
table with their blocking reasons. With no eligible run, the report states that it has no results.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import UTC, datetime
from pathlib import Path

from emojilens_api.config import get_settings
from emojilens_api.db import make_engine, make_sessionmaker
from emojilens_api.db.migrate import current_revision, head_revision
from emojilens_api.services.reporting import build_report, render_markdown
from emojilens_core.models.catalog import default_registry

ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    ap.add_argument("--out", type=Path, default=ROOT / "var" / "reports")
    args = ap.parse_args()
    settings = get_settings()
    registry = default_registry(pins_path=Path(settings.model_pins_path))
    engine = make_engine(settings.database_url)
    current, head = current_revision(engine), head_revision(settings.database_url)
    if current != head:
        print(
            f"database schema is at {current}, not {head}: run "
            "`uv run alembic -c apps/api/alembic.ini upgrade head` first",
            file=sys.stderr,
        )
        return 2
    with make_sessionmaker(engine)() as session:
        report = build_report(session, registry)
    out = args.out / datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    out.mkdir(parents=True, exist_ok=True)
    (out / "report.json").write_text(
        json.dumps(report, indent=2, ensure_ascii=False, sort_keys=True) + "\n", "utf-8"
    )
    (out / "report.md").write_text(render_markdown(report), "utf-8")
    eligible = sum(s["eligible"] for s in report["screened"])
    print(
        f"{len(report['screened'])} run(s) screened, {eligible} eligible; wrote {out / 'report.md'}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
