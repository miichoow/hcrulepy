from hcrulepy.memory import MemoryState
from hcrulepy.rules import REGISTRY


def apply(word, cmd, args=()):
    func, _ = REGISTRY[cmd]
    return func(word, args, MemoryState())


def test_shift_left():
    # 's' (0x73) << 1 = 0xE6
    assert apply(b"p@ssW0rd", "L", (2,)) == b"p@\xe6sW0rd"


def test_shift_right():
    # 's' (0x73) >> 1 = 0x39 = '9'
    assert apply(b"p@ssW0rd", "R", (2,)) == b"p@9sW0rd"


def test_ascii_increment():
    assert apply(b"p@ssW0rd", "+", (2,)) == b"p@tsW0rd"


def test_ascii_decrement():
    assert apply(b"p@ssW0rd", "-", (1,)) == b"p?ssW0rd"


def test_replace_n_plus_1():
    assert apply(b"p@ssW0rd", ".", (1,)) == b"psssW0rd"


def test_replace_n_minus_1():
    assert apply(b"p@ssW0rd", ",", (1,)) == b"ppssW0rd"


def test_title():
    assert apply(b"p@ssW0rd w0rld", "E") == b"P@ssw0rd W0rld"


def test_title_sep():
    assert apply(b"p@ssW0rd-w0rld", "e", (b"-",)) == b"P@ssw0rd-W0rld"


def test_toggle_nth_sep():
    assert apply(b"pass-word", "3", (0, b"-")) == b"pass-Word"
