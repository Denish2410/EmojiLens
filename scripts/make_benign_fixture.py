"""Generate datasets/fixtures/benign_controls.synthetic.jsonl.

These are SYNTHETIC development fixtures written by the EmojiLens developers. They exercise
benign-control handling (clean text, heavy emoji, Indic joiners, code-mixing, decoration)
across the five varieties. They are never research data: import them only into a dataset of
kind "synthetic_fixture", which reports exclude. Invisible characters are written as JSON
escapes so the file stays reviewable.
"""

from __future__ import annotations

import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from source_hygiene import dangerous  # noqa: E402

ZWJ, ZWNJ, VS16 = "\u200d", "\u200c", "\ufe0f"
FAMILY = f"\U0001f468{ZWJ}\U0001f469{ZWJ}\U0001f467{ZWJ}\U0001f466"

ROWS: list[tuple[str, str, str]] = [
    # (control, language, text)
    ("clean", "en", "See you at the library at five."),
    ("clean", "hi", "कल सुबह बैठक है।"),
    ("clean", "gu", "આવતીકાલે સવારે મીટિંગ છે."),
    ("clean", "hi-Latn", "kal subah meeting hai, time pe aana"),
    ("clean", "gu-Latn", "kale savare meeting che, samay par aavjo"),
    ("heavy_emoji", "en", "Happy birthday!!! \U0001f389\U0001f382\U0001f388\U0001f973\U0001f381"),
    ("heavy_emoji", "en", f"Family dinner tonight {FAMILY}\U0001f372"),
    ("heavy_emoji", "en", "Great job \U0001f44d\U0001f3fd\U0001f44f\U0001f3fe"),
    ("heavy_emoji", "en", f"Call me at 9{VS16}\u20e3 tomorrow"),
    ("heavy_emoji", "en", "Go India \U0001f1ee\U0001f1f3!"),
    ("heavy_emoji", "hi", "जन्मदिन मुबारक हो \U0001f389\U0001f382\U0001f973"),
    ("heavy_emoji", "gu-Latn", f"happy birthday ben \U0001f382\U0001f389❤{VS16}"),
    (
        "heavy_emoji",
        "hi-Latn",
        "weekend pe beach chalte hain \U0001f31e\U0001f3d6\ufe0f\U0001f379\U0001f60e",
    ),
    ("indic_joiner", "hi", f"क्{ZWJ}षमा करें"),
    ("indic_joiner", "hi", f"क्{ZWNJ}ष अक्षर"),
    ("indic_joiner", "gu", f"ક્{ZWNJ}ષ અક્ષર"),
    ("indic_joiner", "gu", f"ક્{ZWJ}ષમા કરો"),
    ("indic_joiner", "hi", "विद्यालय में आज छुट्टी है"),
    ("code_mixed", "hi-Latn", "aaj मौसम बहुत अच्छा hai \U0001f60a"),
    ("code_mixed", "gu-Latn", "kal ઓફિસ jaish? \U0001f642"),
    ("code_mixed", "en", "meeting is at 5, पहुंच जाना"),
    ("code_mixed", "gu-Latn", "tame free cho to call karjo \U0001f4de"),
    ("code_mixed", "hi-Latn", "yaar this movie was too good, ekdum mast \U0001f525"),
    ("decoration", "en", "✨ Good morning ✨"),
    ("decoration", "en", "Hello \U0001f338\U0001f338\U0001f338"),
    ("decoration", "hi-Latn", "~*~ Shubh Prabhat ~*~ \U0001f305"),
    ("decoration", "en", "\U0001f496 Thank you \U0001f496"),
    ("decoration", "gu", "\U0001fa94 શુભ દીપાવલી \U0001fa94"),
]


def jsonl_line(obj: dict[str, object]) -> str:
    raw = json.dumps(obj, ensure_ascii=False, sort_keys=True)
    out = []
    for ch in raw:
        if dangerous(ch):
            cp = ord(ch)
            if cp > 0xFFFF:
                cp -= 0x10000
                out.append(f"\\u{0xD800 + (cp >> 10):04x}\\u{0xDC00 + (cp & 0x3FF):04x}")
            else:
                out.append(f"\\u{cp:04x}")
        else:
            out.append(ch)
    return "".join(out)


def main() -> None:
    path = ROOT / "datasets/fixtures/benign_controls.synthetic.jsonl"
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        jsonl_line(
            {
                "id": f"benign-{i:03d}",
                "text": text,
                "language": lang,
                "safety_label": "safe",
                "control": control,
                "origin": "synthetic:emojilens-dev-fixture",
                "license": "CC0-1.0",
                "meta": {"synthetic": True},
            }
        )
        for i, (control, lang, text) in enumerate(ROWS, 1)
    ]
    path.write_text("\n".join(lines) + "\n", "utf-8")
    print(f"wrote {len(lines)} records to {path.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
