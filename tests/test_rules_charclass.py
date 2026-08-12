import pytest
from hcrulepy.errors import RejectCandidate
from hcrulepy.memory import MemoryState
from hcrulepy.rules import CLASS_REGISTRY, char_class

DIGIT = char_class("?d")
LOWER = char_class("?l")


def run(word, cmd, cls, extra=()):
    func, _ = CLASS_REGISTRY[cmd]
    return func(word, cls, extra, MemoryState())


def test_char_class_sets():
    assert ord("5") in DIGIT and ord("a") not in DIGIT
    assert ord("a") in LOWER and ord("A") not in LOWER


def test_replace_all_in_class():
    assert run(b"p4ss5", "s", DIGIT, (b"_",)) == b"p_ss_"


def test_remove_all_in_class():
    assert run(b"p4ss5", "@", DIGIT) == b"pss"


def test_capitalize_after_class():
    # capitalize first letter and every letter following a digit
    assert run(b"ab1cd", "e", DIGIT) == b"Ab1Cd"


def test_reject_contains_class():
    with pytest.raises(RejectCandidate):
        run(b"ab1", "!", DIGIT)
    assert run(b"abc", "!", DIGIT) == b"abc"


def test_reject_not_contains_class():
    assert run(b"ab1", "/", DIGIT) == b"ab1"
    with pytest.raises(RejectCandidate):
        run(b"abc", "/", DIGIT)


def test_reject_first_class():
    assert run(b"1ab", "(", DIGIT) == b"1ab"
    with pytest.raises(RejectCandidate):
        run(b"a1b", "(", DIGIT)


def test_reject_last_class():
    assert run(b"ab1", ")", DIGIT) == b"ab1"
    with pytest.raises(RejectCandidate):
        run(b"a1b", ")", DIGIT)


def test_reject_at_class():
    assert run(b"a1b", "=", DIGIT, (1,)) == b"a1b"
    with pytest.raises(RejectCandidate):
        run(b"a1b", "=", DIGIT, (0,))


def test_reject_count_class():
    assert run(b"a12", "%", DIGIT, (2,)) == b"a12"
    with pytest.raises(RejectCandidate):
        run(b"a1b", "%", DIGIT, (2,))
