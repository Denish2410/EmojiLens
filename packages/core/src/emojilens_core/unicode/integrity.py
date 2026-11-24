"""Original-input integrity: validation and hashing.

Rules (see CLAUDE.md, "Original input integrity"):

* Input is never trimmed, normalized, sanitized or otherwise altered.
* The SHA-256 digest is computed over the strict UTF-8 encoding of the input.
* Input containing surrogate code points (U+D800..U+DFFF) is not well-formed
  Unicode and is rejected with :class:`InvalidUnicodeError`.
"""

from __future__ import annotations

import hashlib

from emojilens_core.unicode.errors import InvalidUnicodeError

_SURROGATE_MIN = 0xD800
_SURROGATE_MAX = 0xDFFF


def validate_unicode(text: str) -> None:
    """Raise :class:`InvalidUnicodeError` if ``text`` contains a surrogate code point."""
    for offset, char in enumerate(text):
        cp = ord(char)
        if _SURROGATE_MIN <= cp <= _SURROGATE_MAX:
            raise InvalidUnicodeError(
                f"Input contains a lone surrogate U+{cp:04X} at code point offset {offset}.",
                codepoint_offset=offset,
                codepoint=cp,
            )


def original_utf8(text: str) -> bytes:
    """Return the strict UTF-8 encoding of ``text`` after validating it."""
    validate_unicode(text)
    return text.encode("utf-8", errors="strict")


def original_sha256(text: str) -> str:
    """Return the lowercase hex SHA-256 digest of the original UTF-8 bytes."""
    return hashlib.sha256(original_utf8(text)).hexdigest()
