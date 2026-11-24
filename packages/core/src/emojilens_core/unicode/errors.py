"""Structured errors raised by the Unicode forensics engine."""

from __future__ import annotations


class InvalidUnicodeError(ValueError):
    """Raised when input cannot be represented as well-formed Unicode.

    The stable machine-readable code is ``invalid_unicode``. ``codepoint_offset``
    is the index (in Python code points) of the first offending code point.
    """

    code = "invalid_unicode"

    def __init__(self, message: str, *, codepoint_offset: int, codepoint: int) -> None:
        super().__init__(message)
        self.codepoint_offset = codepoint_offset
        self.codepoint = codepoint

    def to_dict(self) -> dict[str, object]:
        return {
            "code": self.code,
            "message": str(self),
            "codepoint_offset": self.codepoint_offset,
            "codepoint": f"U+{self.codepoint:04X}",
        }
