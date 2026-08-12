import os
import re
import shutil
import subprocess
from pathlib import Path

import pytest

from hcrulepy.engine import RuleEngine

DATA = Path(__file__).parent / "data"
WORDLIST = DATA / "wordlist.txt"


def find_hashcat():
    return os.environ.get("HASHCAT_BIN") or shutil.which("hashcat")


def hashcat_version(binpath):
    out = subprocess.run([binpath, "--version"], capture_output=True, text=True)
    m = re.search(r"v?(\d+)\.(\d+)", out.stdout.strip())
    return tuple(int(x) for x in m.groups()) if m else (0, 0)


def run_hashcat(binpath, rule_file):
    # --stdout applies rules to the wordlist and prints candidates
    proc = subprocess.run(
        [binpath, "--stdout", "-r", str(rule_file), str(WORDLIST)],
        capture_output=True,
    )
    assert proc.returncode == 0, proc.stderr.decode("latin-1", "replace")
    return proc.stdout


def run_hcrulepy(rule_file):
    words = WORDLIST.read_bytes().split(b"\n")
    if words and words[-1] == b"":
        words = words[:-1]  # drop final empty from trailing newline
    engine = RuleEngine.from_file(rule_file)
    lines = list(engine.apply_many(words))
    return ("\n".join(lines) + ("\n" if lines else "")).encode("latin-1")


@pytest.mark.parametrize(
    "rule_name,min_ver",
    [
        ("core_rules.rule", (0, 0)),
        ("charclass_rules.rule", (7, 0)),
    ],
)
def test_matches_hashcat(rule_name, min_ver):
    binpath = find_hashcat()
    if not binpath:
        pytest.skip("hashcat binary not available (set HASHCAT_BIN or add to PATH)")
    if hashcat_version(binpath) < min_ver:
        pytest.skip(f"{rule_name} needs hashcat >= {min_ver}")
    rule_file = DATA / rule_name
    expected = run_hashcat(binpath, rule_file)
    actual = run_hcrulepy(rule_file)
    if expected != actual:
        # produce a helpful first-diff message
        exp_lines = expected.split(b"\n")
        act_lines = actual.split(b"\n")
        for idx, (e, a) in enumerate(zip(exp_lines, act_lines)):
            if e != a:
                pytest.fail(
                    f"line {idx}: hashcat={e!r} hcrulepy={a!r} "
                    f"(total exp={len(exp_lines)} act={len(act_lines)})"
                )
        pytest.fail(f"length differs: exp={len(exp_lines)} act={len(act_lines)}")
