"""Build the vendored CLDR emoji annotation subset used by emojilens_core.multilingual.

Input: unpacked npm packages `cldr-annotations-full` and `cldr-annotations-derived-full`
(Unicode CLDR JSON, license Unicode-3.0). Obtain them with:
    npm pack cldr-annotations-full@49.0.0 cldr-annotations-derived-full@49.0.0
and extract each tarball. Usage:
    uv run python scripts/vendor_cldr_annotations.py FULL_DIR DERIVED_DIR
"""

from __future__ import annotations

import json
import pathlib
import shutil
import sys

LOCALES = ("en", "hi", "gu", "hi-Latn")
OUT = (
    pathlib.Path(__file__).resolve().parents[1]
    / "packages/core/src/emojilens_core/multilingual/data"
)


def load(path: pathlib.Path, key: str) -> dict[str, dict[str, list[str]]]:
    data: dict[str, dict[str, dict[str, dict[str, list[str]]]]] = json.loads(
        path.read_text("utf-8")
    )
    return data[key]["annotations"]


def main(full: str, derived: str) -> None:
    full_dir = pathlib.Path(full)
    derived_dir = pathlib.Path(derived)
    version = json.loads((full_dir / "package.json").read_text("utf-8"))["version"]
    result: dict[str, object] = {"cldr_version": version, "license": "Unicode-3.0", "locales": {}}
    locales: dict[str, dict[str, dict[str, object]]] = {}
    for loc in LOCALES:
        merged: dict[str, dict[str, object]] = {}
        for path, key in (
            (full_dir / "annotations" / loc / "annotations.json", "annotations"),
            (derived_dir / "annotationsDerived" / loc / "annotations.json", "annotationsDerived"),
        ):
            for emoji_seq, ann in load(path, key).items():
                tts = ann.get("tts") or []
                merged[emoji_seq] = {
                    "name": tts[0] if tts else "",
                    "keywords": ann.get("default", []),
                }
        locales[loc] = merged
    result["locales"] = locales
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "cldr_annotations.json").write_text(
        json.dumps(result, ensure_ascii=False, separators=(",", ":"), sort_keys=True), "utf-8"
    )
    shutil.copy(full_dir / "LICENSE", OUT / "CLDR_LICENSE.txt")
    print({loc: len(v) for loc, v in locales.items()}, "cldr", version)


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
