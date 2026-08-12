import subprocess
import sys

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


def test_console_script_runs():
    # smoke test the installed entry point
    out = subprocess.run(
        [sys.executable, "-m", "hcrulepy", "--help"],
        capture_output=True,
        check=False,
    )
    assert out.returncode == 0
