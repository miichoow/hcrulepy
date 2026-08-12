from hcrulepy.memory import MemoryState
from hcrulepy.rules import REGISTRY

W = b"p@ssW0rd"


def apply(cmd, args=()):
    func, _ = REGISTRY[cmd]
    return func(W, args, MemoryState())


def test_rotate_left():
    assert apply("{") == b"@ssW0rdp"


def test_rotate_right():
    assert apply("}") == b"dp@ssW0r"


def test_truncate_left():
    assert apply("[") == b"@ssW0rd"


def test_truncate_right():
    assert apply("]") == b"p@ssW0r"


def test_append_char():
    assert apply("$", (b"1",)) == b"p@ssW0rd1"


def test_prepend_char():
    assert apply("^", (b"2",)) == b"2p@ssW0rd"


def test_delete_at():
    assert apply("D", (3,)) == b"p@sW0rd"


def test_extract_range():
    assert apply("x", (0, 4)) == b"p@ss"


def test_omit_range():
    assert apply("O", (1, 2)) == b"psW0rd"


def test_insert_at():
    assert apply("i", (4, b"!")) == b"p@ss!W0rd"


def test_overwrite_at():
    assert apply("o", (3, b"$")) == b"p@s$W0rd"


def test_truncate_at():
    assert apply("'", (6,)) == b"p@ssW0"
