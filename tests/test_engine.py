import pytest

from hcrulepy.engine import RuleEngine, apply_rule, parse_rule
from hcrulepy.errors import InvalidRule
from hcrulepy.rules import char_class


def test_parse_multi_function_line():
    ops = parse_rule("so0 c $1")
    assert ops == [
        ("std", "s", (b"o", b"0")),
        ("std", "c", ()),
        ("std", "$", (b"1",)),
    ]


def test_parse_comment_and_blank():
    assert parse_rule("# comment") == []
    assert parse_rule("   ") == []


def test_parse_unknown_command():
    with pytest.raises(InvalidRule):
        parse_rule("\x07")


def test_parse_missing_arg():
    with pytest.raises(InvalidRule):
        parse_rule("$")  # $ needs a char


def test_parse_p_register_rejected():
    with pytest.raises(InvalidRule):
        parse_rule("Tp")  # deferred feature


def test_parse_class_rule():
    ops = parse_rule("~s?d_")
    assert ops[0][0] == "cls" and ops[0][1] == "s"


def test_parse_class_positional_arg_before_token():
    # ~=N?C: positional arg comes BEFORE the class token.
    ops = parse_rule("~=1?d")
    assert ops == [("cls", "=", char_class("?d"), (1,))]


def test_parse_class_literal_arg_after_token():
    # ~sY?C: literal-char arg comes AFTER the class token.
    ops = parse_rule("~s?d_")
    assert ops == [("cls", "s", char_class("?d"), (b"_",))]


def test_parse_dangling_tilde():
    with pytest.raises(InvalidRule):
        parse_rule("~")


def test_parse_unknown_class_command():
    with pytest.raises(InvalidRule):
        parse_rule("~Z?d")


def test_parse_missing_class_token():
    with pytest.raises(InvalidRule):
        parse_rule("~s")  # no ?C class token follows


def test_apply_rule_transform():
    assert apply_rule("password", "so0") == "passw0rd"


def test_apply_rule_reject():
    assert apply_rule("abcde", "<3") is None  # len 5 > 3 -> reject


def test_apply_rule_class_op():
    # ~s?d_ : replace every digit with '_' via the class-op path in apply_ops.
    assert apply_rule("p4ss5", "~s?d_") == "p_ss_"


def test_apply_rule_class_op_reject():
    # ~!?d rejects words containing a digit, exercising the "cls" branch's
    # RejectCandidate handling in apply_ops.
    assert apply_rule("ab1", "~!?d") is None
    assert apply_rule("abc", "~!?d") == "abc"


def test_apply_rule_memory_roundtrip():
    # uMl4 from wiki -> p@ssw0rdP@SSW0RD
    assert apply_rule("p@ssW0rd", "uMl4") == "p@ssw0rdP@SSW0RD"


def test_engine_apply_word_major():
    eng = RuleEngine([":", "u", "$!"])
    assert list(eng.apply("ab")) == ["ab", "AB", "ab!"]


def test_engine_apply_many_word_major():
    eng = RuleEngine([":", "u"])
    assert list(eng.apply_many(["ab", "cd"])) == ["ab", "AB", "cd", "CD"]


def test_engine_rejects_dropped():
    eng = RuleEngine(["u", ")z"])  # )z rejects words not ending in z
    assert list(eng.apply("ab")) == ["AB"]  # second rule rejected


def test_init_skip_invalid_warns_and_skips(capsys):
    eng = RuleEngine(["u", "\x07", ":"], skip_invalid=True)
    err = capsys.readouterr().err
    assert "line 2" in err
    assert list(eng.apply("ab")) == ["AB", "ab"]


def test_init_without_skip_invalid_raises():
    with pytest.raises(InvalidRule):
        RuleEngine(["u", "\x07"])


def test_from_files_skip_invalid_warns_and_skips(tmp_path, capsys):
    rules = tmp_path / "r.rule"
    rules.write_text("u\n\x07\n:\n", encoding="latin-1")
    eng = RuleEngine.from_files([rules], skip_invalid=True)
    err = capsys.readouterr().err
    assert str(rules) in err and ":2:" in err
    assert list(eng.apply("ab")) == ["AB", "ab"]


def test_from_files_without_skip_invalid_raises(tmp_path):
    rules = tmp_path / "r.rule"
    rules.write_text("u\n\x07\n", encoding="latin-1")
    with pytest.raises(InvalidRule):
        RuleEngine.from_files([rules])


def test_check_files_reports_errors(tmp_path):
    good = tmp_path / "good.rule"
    good.write_text("u\n:\n", encoding="latin-1")
    bad = tmp_path / "bad.rule"
    bad.write_text("u\n\x07\n$\n", encoding="latin-1")

    assert RuleEngine.check_files([good]) == []

    errors = RuleEngine.check_files([bad])
    assert [e[1] for e in errors] == [2, 3]  # line numbers
    assert errors[0][0] == str(bad)
    assert errors[0][2] == "\x07"


def test_from_file_byte_exact_line_splitting(tmp_path):
    # CRLF line ending must be stripped like LF-only form; a byte such as
    # \x0c inside a rule argument (append rule "$\x0c") must be treated as
    # part of the rule, not as a Unicode line separator (str.splitlines()
    # would incorrectly split on \x0c).
    lf_path = tmp_path / "lf.rule"
    lf_path.write_bytes(b"so0\n$\x0c\n")

    crlf_path = tmp_path / "crlf.rule"
    crlf_path.write_bytes(b"so0\r\n$\x0c\r\n")

    eng_lf = RuleEngine.from_file(lf_path)
    eng_crlf = RuleEngine.from_file(crlf_path)

    assert list(eng_lf.apply("password")) == ["passw0rd", "password\x0c"]
    assert list(eng_crlf.apply("password")) == ["passw0rd", "password\x0c"]

    # Same file supplied via from_files should behave identically.
    eng_files = RuleEngine.from_files([lf_path, crlf_path])
    assert list(eng_files.apply("password")) == [
        "passw0rd",
        "password\x0c",
        "passw0rd",
        "password\x0c",
    ]


def test_hex_escape_append():
    # hashcat: `$\x64` appends byte 0x64 ('d'); rule text is a literal backslash.
    assert apply_rule("p@ssW0rd", r"$\x64") == "p@ssW0rdd"


def test_hex_escape_prepend_and_high_byte():
    assert apply_rule("abc", r"^\x41") == "Aabc"  # 0x41 = 'A'
    assert apply_rule("abc", r"$\xe6") == "abc\xe6"  # high byte survives


def test_hex_escape_parsed_as_single_arg_not_extract():
    # The 'x' after the backslash must NOT be read as the extract-range op.
    assert parse_rule(r"$\x64") == [("std", "$", (b"d",))]


def test_hex_escape_in_replace_both_chars():
    # sXY with hex-escaped operands: replace 's' (\x73) with '#' (\x23).
    assert apply_rule("p@ssW0rd", r"s\x73\x23") == "p@##W0rd"


def test_lone_backslash_is_literal():
    # A backslash not forming a valid \xHH stays literal.
    assert apply_rule("abc", "$\\") == "abc\\"  # trailing backslash
    assert apply_rule("abc", "sZ\\") == "abc"  # replace 'Z'->'\', no 'Z'
    assert apply_rule("ab", "^\\") == "\\ab"


def test_backslash_x_without_two_hex_is_literal():
    # `\xZZ` is not a valid escape -> '$' appends a literal backslash.
    assert parse_rule(r"$\xZZ")[0] == ("std", "$", (b"\\",))
