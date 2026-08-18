import pytest

from hcrulepy.errors import RejectCandidate
from hcrulepy.memory import MemoryState
from hcrulepy.rules import REGISTRY


def apply(word, cmd, args=(), mem=None):
    func, _ = REGISTRY[cmd]
    return func(word, args, mem or MemoryState())


def test_memorize_sets_memory():
    mem = MemoryState()
    apply(b"p@ssw0rd", "M", (), mem)
    assert mem.memory == b"p@ssw0rd"


def test_append_memory():
    mem = MemoryState()
    mem.memory = b"P@SSW0RD"
    assert apply(b"p@ssw0rd", "4", (), mem) == b"p@ssw0rdP@SSW0RD"


def test_prepend_memory():
    mem = MemoryState()
    mem.memory = b"dr0Wss@p"
    assert apply(b"p@ssW0rd", "6", (), mem) == b"dr0Wss@pp@ssW0rd"


def test_extract_memory():
    # from wiki: lMX428 on p@ssW0rd -> p@ssw0rdw0
    mem = MemoryState()
    mem.memory = b"p@ssw0rd"  # state after l, M
    assert apply(b"p@ssw0rd", "X", (4, 2, 8), mem) == b"p@ssw0rdw0"


def test_extract_memory_insert_past_end_noop():
    mem = MemoryState()
    mem.memory = b"XYZ"
    assert apply(b"ab", "X", (0, 2, 5), mem) == b"ab"  # i=5 > len(w)=2


def test_reject_memory_equal():
    mem = MemoryState()
    mem.memory = b"p@ssW0rd"
    with pytest.raises(RejectCandidate):
        apply(b"p@ssW0rd", "Q", (), mem)


def test_reject_memory_not_equal():
    mem = MemoryState()
    mem.memory = b"other"
    assert apply(b"p@ssW0rd", "Q", (), mem) == b"p@ssW0rd"
