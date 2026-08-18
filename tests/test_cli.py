import runpy
import subprocess
import sys

import pytest

from hcrulepy.cli import main


def write(tmp_path, name, text):
    p = tmp_path / name
    p.write_text(text, encoding="latin-1")
    return p


def test_cli_word(tmp_path, capsysbinary):
    rules = write(tmp_path, "r.rule", ":\nu\n$!\n")
    rc = main(["-r", str(rules), "--word", "ab"])
    assert rc == 0
    out = capsysbinary.readouterr().out
    assert out == b"ab\nAB\nab!\n"


def test_cli_wordlist_word_major(tmp_path, capsysbinary):
    rules = write(tmp_path, "r.rule", ":\nu\n")
    wl = write(tmp_path, "wl.txt", "ab\ncd\n")
    rc = main(["-r", str(rules), str(wl)])
    assert rc == 0
    assert capsysbinary.readouterr().out == b"ab\nAB\ncd\nCD\n"


def test_cli_reject_dropped(tmp_path, capsysbinary):
    rules = write(tmp_path, "r.rule", "u\n)z\n")
    rc = main(["-r", str(rules), "--word", "ab"])
    assert rc == 0
    assert capsysbinary.readouterr().out == b"AB\n"


def test_cli_missing_rule_file(tmp_path, capsys):
    rc = main(["-r", str(tmp_path / "nope.rule"), "--word", "ab"])
    assert rc != 0


def test_cli_no_rules_errors(capsys):
    with pytest.raises(SystemExit) as exc:
        main(["--word", "ab"])
    assert exc.value.code == 2
    assert "at least one" in capsys.readouterr().err


def test_cli_check_ok(tmp_path, capsys):
    rules = write(tmp_path, "r.rule", "u\n:\n")
    rc = main(["-r", str(rules), "--check"])
    assert rc == 0
    assert "OK" in capsys.readouterr().out


def test_cli_check_invalid_lines(tmp_path, capsys):
    rules = write(tmp_path, "r.rule", "u\n\x07\n")
    rc = main(["-r", str(rules), "--check"])
    assert rc == 1
    err = capsys.readouterr().err
    assert f"{rules}:2:" in err
    assert "1 invalid rule line(s)" in err


def test_cli_check_missing_file(tmp_path, capsys):
    rc = main(["-r", str(tmp_path / "nope.rule"), "--check"])
    assert rc == 2
    assert "hcrulepy:" in capsys.readouterr().err


def test_cli_skip_invalid_flag(tmp_path, capsysbinary):
    rules = write(tmp_path, "r.rule", "u\n\x07\n:\n")
    rc = main(["-r", str(rules), "--word", "ab", "-k"])
    assert rc == 0
    captured = capsysbinary.readouterr()
    assert captured.out == b"AB\nab\n"
    assert b":2:" in captured.err


def test_cli_wordlist_missing_raises_during_iteration(tmp_path, capsys):
    rules = write(tmp_path, "r.rule", ":\n")
    rc = main(["-r", str(rules), str(tmp_path / "nope.txt")])
    assert rc == 2
    assert "hcrulepy:" in capsys.readouterr().err


def test_cli_flushes_large_output(tmp_path, capsysbinary):
    # Force the internal 64KiB buffer to flush mid-stream (line 96-97).
    rules = write(tmp_path, "r.rule", ":\n")
    words = "\n".join(f"word{i:05d}" for i in range(10_000)) + "\n"
    wl = write(tmp_path, "wl.txt", words)
    rc = main(["-r", str(rules), str(wl)])
    assert rc == 0
    out = capsysbinary.readouterr().out
    assert out.count(b"\n") == 10_000


def test_main_module_entry_point(tmp_path, monkeypatch, capsysbinary):
    # Run the __main__.py module in-process (so coverage sees it) instead of
    # via subprocess, and confirm it exits with the CLI's return code.
    rules = write(tmp_path, "r.rule", ":\n")
    monkeypatch.setattr(sys, "argv", ["hcrulepy", "-r", str(rules), "--word", "ab"])
    with pytest.raises(SystemExit) as exc:
        runpy.run_module("hcrulepy.__main__", run_name="__main__")
    assert exc.value.code == 0
    assert capsysbinary.readouterr().out == b"ab\n"


def test_console_script_runs():
    # smoke test the installed entry point
    out = subprocess.run(
        [sys.executable, "-m", "hcrulepy", "--help"],
        capture_output=True,
        check=False,
    )
    assert out.returncode == 0
