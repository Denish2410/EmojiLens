"""Load the synthetic benign-control fixture into a running local API.

Creates dataset ``benign-controls-synthetic`` (kind ``synthetic_fixture``) if it is missing,
uploads the fixture as a new version and freezes it with a fixed seed. Development only.
    uv run python scripts/seed_fixtures.py [--api http://127.0.0.1:8000]
"""

from __future__ import annotations

import argparse
import json
import pathlib
import urllib.error
import urllib.request
from typing import Any

ROOT = pathlib.Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "datasets/fixtures/benign_controls.synthetic.jsonl"
SLUG = "benign-controls-synthetic"


def call(method: str, url: str, body: bytes | None = None, ctype: str = "application/json") -> Any:
    if not url.startswith(("http://127.0.0.1", "http://localhost")):
        raise SystemExit("Refusing to seed a non-local API.")
    req = urllib.request.Request(url, data=body, method=method, headers={"Content-Type": ctype})  # noqa: S310
    try:
        with urllib.request.urlopen(req) as resp:  # noqa: S310 - local URL enforced above
            return json.loads(resp.read())
    except urllib.error.HTTPError as exc:
        return json.loads(exc.read() or b"{}") | {"status": exc.code}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--api", default="http://127.0.0.1:8000")
    base = parser.parse_args().api.rstrip("/") + "/api/v1/datasets"
    created = call(
        "POST",
        base,
        json.dumps(
            {
                "slug": SLUG,
                "name": "Benign controls (synthetic fixture)",
                "description": "Developer-written synthetic benign controls across five varieties. "
                "Not research data.",
                "kind": "synthetic_fixture",
                "license": "CC0-1.0",
            }
        ).encode(),
    )
    if created.get("status") not in (None, 409):
        raise SystemExit(f"create failed: {created}")
    imported = call("POST", f"{base}/{SLUG}/versions", FIXTURE.read_bytes(), "application/x-ndjson")
    number = imported["version"]["number"]
    frozen = call(
        "POST", f"{base}/{SLUG}/versions/{number}/freeze", json.dumps({"seed": 20261124}).encode()
    )
    count = imported["version"]["record_count"]
    print(f"{SLUG} v{number}: {count} records, leakage={frozen['leakage']}")


if __name__ == "__main__":
    main()
