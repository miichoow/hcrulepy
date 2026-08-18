from hcrulepy.memory import MemoryState
from hcrulepy.rules import REGISTRY

W = b"p@ssW0rd"


def apply(cmd, args=()):
    func, _ = REGISTRY[cmd]
    return func(W, args, MemoryState())


def test_replace():
    assert apply("s", (b"s", b"$")) == b"p@$$W0rd"


def test_purge():
    assert apply("@", (b"s",)) == b"p@W0rd"


def test_dup_first_n():
    assert apply("z", (2,)) == b"ppp@ssW0rd"


def test_dup_last_n():
    assert apply("Z", (2,)) == b"p@ssW0rddd"


def test_dup_all():
    assert apply("q") == b"pp@@ssssWW00rrdd"


def test_dup_block_front():
    assert apply("y", (2,)) == b"p@p@ssW0rd"


def test_dup_block_back():
    assert apply("Y", (2,)) == b"p@ssW0rdrd"


def test_swap_front():
    assert apply("k") == b"@pssW0rd"


def test_swap_back():
    assert apply("K") == b"p@ssW0dr"


def test_swap_front_short_word_noop():
    func, _ = REGISTRY["k"]
    assert func(b"a", (), MemoryState()) == b"a"
    assert func(b"", (), MemoryState()) == b""


def test_swap_back_short_word_noop():
    func, _ = REGISTRY["K"]
    assert func(b"a", (), MemoryState()) == b"a"
    assert func(b"", (), MemoryState()) == b""


def test_swap_at():
    assert apply("*", (3, 4)) == b"p@sWs0rd"
