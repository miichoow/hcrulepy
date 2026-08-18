import pytest

from hcrulepy.errors import InvalidRule
from hcrulepy.memory import MemoryState, decode_pos, lower_byte, toggle_byte, upper_byte


def test_package_imports():
    import hcrulepy
    from hcrulepy.errors import InvalidRule, RejectCandidate

    assert hcrulepy.__name__ == "hcrulepy"
    assert issubclass(InvalidRule, Exception)
    assert issubclass(RejectCandidate, Exception)


def test_decode_pos_digits():
    assert decode_pos("0") == 0
    assert decode_pos("9") == 9


def test_decode_pos_letters():
    assert decode_pos("A") == 10
    assert decode_pos("Z") == 35


def test_decode_pos_invalid():
    with pytest.raises(InvalidRule):
        decode_pos("p")
    with pytest.raises(InvalidRule):
        decode_pos("!")


def test_decode_pos_wrong_length():
    with pytest.raises(InvalidRule):
        decode_pos("")
    with pytest.raises(InvalidRule):
        decode_pos("AB")


def test_memory_state_default_and_reset():
    m = MemoryState()
    assert m.memory == b""
    m.memory = b"abc"
    m.reset()
    assert m.memory == b""


def test_byte_case_helpers_ascii_only():
    assert upper_byte(ord("a")) == ord("A")
    assert lower_byte(ord("A")) == ord("a")
    assert toggle_byte(ord("a")) == ord("A")
    assert toggle_byte(ord("A")) == ord("a")
    # non-letters untouched
    assert upper_byte(ord("1")) == ord("1")
    assert lower_byte(0xE6) == 0xE6  # æ, high byte untouched
