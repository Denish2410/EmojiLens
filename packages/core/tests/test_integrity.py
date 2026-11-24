import hashlib

import pytest
from hypothesis import given
from hypothesis import strategies as st

from emojilens_core.unicode import InvalidUnicodeError, original_sha256, validate_unicode

# Well-formed Unicode scalar values only (no surrogates).
scalar_text = st.text(alphabet=st.characters(codec="utf-8"), max_size=200)


def test_known_digest_ascii() -> None:
    assert original_sha256("abc") == (
        "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad"
    )


def test_digest_is_over_original_bytes_not_normalized() -> None:
    composed = "é"  # é
    decomposed = "é"  # e + combining acute
    assert original_sha256(composed) != original_sha256(decomposed)


def test_whitespace_and_invisibles_are_not_trimmed() -> None:
    assert original_sha256(" a​ ") != original_sha256("a")


@pytest.mark.parametrize("cp", [0xD800, 0xDBFF, 0xDC00, 0xDFFF])
def test_lone_surrogate_rejected(cp: int) -> None:
    text = "ok" + chr(cp) + "x"
    with pytest.raises(InvalidUnicodeError) as info:
        validate_unicode(text)
    assert info.value.code == "invalid_unicode"
    assert info.value.codepoint_offset == 2
    assert info.value.to_dict()["codepoint"] == f"U+{cp:04X}"


@given(scalar_text)
def test_digest_matches_strict_utf8(text: str) -> None:
    assert original_sha256(text) == hashlib.sha256(text.encode("utf-8")).hexdigest()
