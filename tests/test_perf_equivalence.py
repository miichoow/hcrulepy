import io

from hcrulepy import apply_rule, cli
from hcrulepy.memory import (
    LOWER_TABLE,
    TOGGLE_TABLE,
    UPPER_TABLE,
    lower_byte,
    toggle_byte,
    upper_byte,
)


def test_tables_are_256_bytes():
    assert len(LOWER_TABLE) == 256
    assert len(UPPER_TABLE) == 256
    assert len(TOGGLE_TABLE) == 256


def test_tables_match_scalar_helpers_for_every_byte():
    for b in range(256):
        assert LOWER_TABLE[b] == lower_byte(b), f"lower {b}"
        assert UPPER_TABLE[b] == upper_byte(b), f"upper {b}"
        assert TOGGLE_TABLE[b] == toggle_byte(b), f"toggle {b}"


def test_case_ops_unchanged_on_edge_words():
    for word in ["", "a", "A", "p@ssW0rd", "Ab\xe6Z9"]:
        raw = word.encode("latin-1")
        assert apply_rule(word, "l") == raw.translate(LOWER_TABLE).decode("latin-1")
        assert apply_rule(word, "u") == raw.translate(UPPER_TABLE).decode("latin-1")
        assert apply_rule(word, "t") == raw.translate(TOGGLE_TABLE).decode("latin-1")


def test_capitalize_ops_unchanged():
    assert apply_rule("p@ssW0rd", "c") == "P@ssw0rd"
    assert apply_rule("p@ssW0rd", "C") == "p@SSW0RD"
    assert apply_rule("", "c") == ""
    assert apply_rule("", "C") == ""


def _reference_words(data: bytes):
    # the pre-streaming behavior, inlined as the oracle
    lines = data.split(b"\n")
    if lines and lines[-1] == b"":
        lines.pop()
    out = []
    for line in lines:
        if line.endswith(b"\r"):
            line = line[:-1]
        out.append(line)
    return out


CASES = [
    b"ab\ncd\n",  # trailing newline
    b"ab\ncd",  # no trailing newline
    b"ab\n\ncd\n",  # interior blank line
    b"",  # empty input
    b"\n",  # lone newline -> one empty word
    b"ab\r\ncd\r\n",  # CRLF
    b"a\xe6b\n\xffz\n",  # high bytes
]


def test_iter_words_file_matches_reference(tmp_path):
    for data in CASES:
        p = tmp_path / "wl.txt"
        p.write_bytes(data)
        assert list(cli._iter_words(str(p))) == _reference_words(data), repr(data)


def test_iter_words_stdin_matches_reference(monkeypatch):
    for data in CASES:
        monkeypatch.setattr(cli.sys, "stdin", io.TextIOWrapper(io.BytesIO(data)))
        assert list(cli._iter_words(None)) == _reference_words(data), repr(data)
        monkeypatch.undo()
