import pytest
from hcrulepy.errors import RejectCandidate
from hcrulepy.memory import MemoryState
from hcrulepy.rules import REGISTRY


def run(word, cmd, args=()):
    func, _ = REGISTRY[cmd]
    return func(word, args, MemoryState())


def rejects(word, cmd, args=()):
    with pytest.raises(RejectCandidate):
        run(word, cmd, args)


def passes(word, cmd, args=()):
    assert run(word, cmd, args) == word


def test_reject_length_greater():  # <N reject if len > N
    passes(b"abc", "<", (4,))  # len 3 <= 4 -> keep
    rejects(b"abcde", "<", (4,))  # len 5 > 4 -> reject


def test_reject_length_less():  # >N reject if len < N
    passes(b"abcde", ">", (4,))  # len 5 >= 4 -> keep
    rejects(b"abc", ">", (4,))  # len 3 < 4 -> reject


def test_reject_length_not_equal():
    passes(b"abcd", "_", (4,))
    rejects(b"abc", "_", (4,))


def test_reject_contains():
    rejects(b"abc", "!", (b"a",))
    passes(b"abc", "!", (b"z",))


def test_reject_not_contains():
    passes(b"abc", "/", (b"a",))
    rejects(b"abc", "/", (b"z",))


def test_reject_not_start():
    passes(b"abc", "(", (b"a",))
    rejects(b"abc", "(", (b"b",))


def test_reject_not_end():
    passes(b"abc", ")", (b"c",))
    rejects(b"abc", ")", (b"a",))


def test_reject_equal_at():
    passes(b"abc", "=", (1, b"b"))
    rejects(b"abc", "=", (1, b"x"))
    rejects(b"abc", "=", (9, b"x"))  # out of range


def test_reject_count():
    passes(b"aabc", "%", (2, b"a"))  # 2 a's, >= 2 -> keep
    rejects(b"aabc", "%", (3, b"a"))  # 2 a's, < 3 -> reject
