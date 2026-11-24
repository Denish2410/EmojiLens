"""Find (and optionally escape) invisible, bidi and confusable characters in source files.

Source code must spell such characters as escapes (\\u200b, \\u{1F3FD}) so reviewers can
see them. Usage:
    uv run python scripts/source_hygiene.py          # check; exit 1 on findings
    uv run python scripts/source_hygiene.py --fix    # rewrite as escapes
"""

from __future__ import annotations

import pathlib
import subprocess
import sys
import unicodedata

import regex

ROOT = pathlib.Path(__file__).resolve().parents[1]
SUFFIXES = {".py", ".ts", ".tsx", ".js", ".mjs"}
_CONFUSABLE = regex.compile(r"[\p{Script=Cyrillic}\p{Script=Greek}]")


def dangerous(ch: str) -> bool:
    cp = ord(ch)
    if ch in "\n\t\r":
        return False
    cat = unicodedata.category(ch)
    if cat in ("Cf", "Cc", "Zl", "Zp", "Co", "Cn") or (cat == "Zs" and ch != " "):
        return True
    if 0xFE00 <= cp <= 0xFE0F or 0xE0100 <= cp <= 0xE01EF or 0xE0000 <= cp <= 0xE007F:
        return True
    if 0x1F3FB <= cp <= 0x1F3FF or cp == 0x20E3:
        return True
    nfkc = unicodedata.normalize("NFKC", ch)
    if nfkc != ch and nfkc.isascii() and nfkc.isalnum():
        return True  # fullwidth / mathematical / styled look-alikes of ASCII
    return bool(_CONFUSABLE.match(ch))


def escape(ch: str, ts: bool) -> str:
    cp = ord(ch)
    if ts:
        return f"\\u{{{cp:X}}}" if cp > 0xFFFF else f"\\u{cp:04x}"
    return f"\\U{cp:08x}" if cp > 0xFFFF else f"\\u{cp:04x}"


def source_files() -> list[pathlib.Path]:
    out = subprocess.run(
        ["git", "ls-files", "--cached", "--others", "--exclude-standard"],  # noqa: S607
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=True,
    ).stdout.split()
    return [ROOT / p for p in out if pathlib.Path(p).suffix in SUFFIXES]


def findings(path: pathlib.Path) -> list[tuple[int, str]]:
    found = []
    for lineno, line in enumerate(path.read_text("utf-8").splitlines(), 1):
        for ch in line:
            if dangerous(ch):
                found.append((lineno, f"U+{ord(ch):04X} {unicodedata.name(ch, '?')}"))
    return found


def main(argv: list[str]) -> int:
    fix = "--fix" in argv
    bad = 0
    for path in source_files():
        if fix:
            src = path.read_text("utf-8")
            ts = path.suffix in {".ts", ".tsx", ".js", ".mjs"}
            out = "".join(escape(c, ts) if dangerous(c) else c for c in src)
            if out != src:
                path.write_text(out, "utf-8")
                print(f"escaped: {path.relative_to(ROOT)}")
        else:
            for lineno, what in findings(path):
                bad += 1
                print(f"{path.relative_to(ROOT)}:{lineno}: {what}")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
