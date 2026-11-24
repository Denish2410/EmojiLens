"""Offset mapping between code point, UTF-8 byte and UTF-16 code unit positions.

JavaScript strings (the web frontend) index by UTF-16 code units, Python by code
points, and storage/hashing by UTF-8 bytes. Every span EmojiLens reports carries
all three so evidence can be located unambiguously in any layer.
"""

from __future__ import annotations

from dataclasses import dataclass


def utf8_width(char: str) -> int:
    cp = ord(char)
    if cp < 0x80:
        return 1
    if cp < 0x800:
        return 2
    if cp < 0x10000:
        return 3
    return 4


def utf16_width(char: str) -> int:
    return 2 if ord(char) > 0xFFFF else 1


@dataclass(frozen=True, slots=True)
class Span:
    """A half-open span ``[start, end)`` expressed in all three index spaces."""

    cp_start: int
    cp_end: int
    utf8_start: int
    utf8_end: int
    utf16_start: int
    utf16_end: int


@dataclass(frozen=True, slots=True)
class OffsetTable:
    """Prefix offsets: ``utf8[i]`` / ``utf16[i]`` is the position before code point ``i``.

    Both lists have ``len(text) + 1`` entries so any half-open code point span
    can be converted in O(1).
    """

    utf8: tuple[int, ...]
    utf16: tuple[int, ...]

    @classmethod
    def build(cls, text: str) -> OffsetTable:
        utf8 = [0]
        utf16 = [0]
        for char in text:
            utf8.append(utf8[-1] + utf8_width(char))
            utf16.append(utf16[-1] + utf16_width(char))
        return cls(utf8=tuple(utf8), utf16=tuple(utf16))

    def span(self, cp_start: int, cp_end: int) -> Span:
        if not 0 <= cp_start <= cp_end < len(self.utf8):
            raise IndexError(f"invalid code point span [{cp_start}, {cp_end})")
        return Span(
            cp_start=cp_start,
            cp_end=cp_end,
            utf8_start=self.utf8[cp_start],
            utf8_end=self.utf8[cp_end],
            utf16_start=self.utf16[cp_start],
            utf16_end=self.utf16[cp_end],
        )

    def cp_from_utf16(self, utf16_offset: int) -> int:
        """Map a UTF-16 boundary offset back to a code point offset.

        Raises ``ValueError`` if the offset falls inside a surrogate pair.
        """
        lo, hi = 0, len(self.utf16) - 1
        while lo <= hi:
            mid = (lo + hi) // 2
            value = self.utf16[mid]
            if value == utf16_offset:
                return mid
            if value < utf16_offset:
                lo = mid + 1
            else:
                hi = mid - 1
        raise ValueError(f"UTF-16 offset {utf16_offset} is not a code point boundary")
