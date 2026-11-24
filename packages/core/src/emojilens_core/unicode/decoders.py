"""Decoders for recognized, documented concealment encodings only.

1. Tag characters (U+E0020..U+E007E) mirror printable ASCII (Unicode Standard, Tags block).
   Outside a valid emoji tag sequence they carry no legitimate meaning in running text.
2. Variation-selector byte encoding: each of the 256 variation selectors stands for one
   byte value (VS1..VS16 = U+FE00..U+FE0F -> 0..15, VS17..VS256 = U+E0100..U+E01EF -> 16..255),
   appended after a visible base character. Decoded only if the bytes are valid UTF-8.

Decoded content is evidence, not proof of intent. Nothing decoded is ever executed.
"""

from __future__ import annotations

TAG_FIRST, TAG_LAST = 0xE0000, 0xE007F
TAG_CANCEL = 0xE007F


def is_tag(cp: int) -> bool:
    return TAG_FIRST <= cp <= TAG_LAST


def decode_tag_run(run: str) -> str | None:
    """Return the ASCII mirror of a run of tag characters, or None if any is non-printable."""
    out = []
    for char in run:
        cp = ord(char)
        if 0xE0020 <= cp <= 0xE007E:
            out.append(chr(cp - 0xE0000))
        elif cp == TAG_CANCEL:
            continue
        else:
            return None
    return "".join(out) if out else None


def vs_byte(cp: int) -> int | None:
    if 0xFE00 <= cp <= 0xFE0F:
        return cp - 0xFE00
    if 0xE0100 <= cp <= 0xE01EF:
        return cp - 0xE0100 + 16
    return None


def is_variation_selector(cp: int) -> bool:
    return vs_byte(cp) is not None


def decode_vs_run(run: str) -> tuple[bytes, str | None]:
    """Map a variation-selector run to bytes; also return the UTF-8 text if it decodes."""
    data = bytes(b for b in (vs_byte(ord(c)) for c in run) if b is not None)
    try:
        return data, data.decode("utf-8", errors="strict")
    except UnicodeDecodeError:
        return data, None
