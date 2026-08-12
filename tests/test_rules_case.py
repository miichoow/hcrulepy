from hcrulepy.memory import MemoryState
from hcrulepy.rules import REGISTRY

W = b"p@ssW0rd"


def apply(cmd, args=()):
    func, _spec = REGISTRY[cmd]
    return func(W, args, MemoryState())


def test_nothing():
    assert apply(":") == b"p@ssW0rd"


def test_lower():
    assert apply("l") == b"p@ssw0rd"


def test_upper():
    assert apply("u") == b"P@SSW0RD"


def test_capitalize():
    assert apply("c") == b"P@ssw0rd"


def test_invert_capitalize():
    assert apply("C") == b"p@SSW0RD"


def test_toggle_all():
    assert apply("t") == b"P@SSw0RD"


def test_toggle_at():
    assert apply("T", (3,)) == b"p@sSW0rd"


def test_reverse():
    assert apply("r") == b"dr0Wss@p"


def test_duplicate():
    assert apply("d") == b"p@ssW0rdp@ssW0rd"


def test_duplicate_n():
    assert apply("p", (2,)) == b"p@ssW0rdp@ssW0rdp@ssW0rd"


def test_reflect():
    assert apply("f") == b"p@ssW0rddr0Wss@p"
