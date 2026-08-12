"""Regression tests against captured real-hashcat output (golden oracles).

Each oracle is a pair under ``tests/data/``:
  - ``<name>.rule`` (or the specially-named all-rules file) — the ruleset
  - ``<name>.out``  — the exact stdout of ``hashcat --stdout -r <rule> word.txt``
    for the input word ``p@ssW0rd``.

The test replays the ruleset through hcrulepy and asserts byte-for-byte
equality with hashcat's candidate lines.

hashcat emits a warning line (and produces NO candidate) for rules it cannot
process on a given build, e.g.:
  - ``Cannot convert rule for use on OpenCL device ... line 119: lMuX084``
  - ``Skipping invalid or unsupported rule ... line 222: ~s?l0``  (7.0.0+ ~?C
    class rules are still rejected by hashcat's --stdout rule engine)
hcrulepy implements these, so — to compare against a specific hashcat build —
we skip exactly the rule lines hashcat itself skipped. The skip set is parsed
out of each ``.out`` file's warning lines, so it stays honest.

The main ``all.rules`` oracle was captured on hashcat v6.2.6 and confirmed
byte-for-byte identical when re-captured on v7.1.2. Additional oracles (e.g.
``coverage_supplement``) activate automatically once their ``.out`` file is
dropped into ``tests/data/``; until then they skip.
"""

import re
from pathlib import Path

import pytest

from hcrulepy.engine import apply_ops, parse_rule
from hcrulepy.errors import InvalidRule

DATA = Path(__file__).parent / "data"
WORD = b"p@ssW0rd"

_WARN = re.compile(r"(?:Cannot convert rule|Skipping invalid or unsupported rule).*on line (\d+):")

# (rules_filename, out_filename). Oracles whose .out is absent are skipped.
ORACLES = [
    ("hashcat_v6.2.6_all.rules", "hashcat_v6.2.6_pAtssW0rd.out"),
    ("coverage_supplement.rule", "coverage_supplement.out"),
]


def _lines(path: Path) -> list[str]:
    raw = path.read_bytes().decode("latin-1").split("\n")
    if raw and raw[-1] == "":
        raw.pop()
    return [ln.removesuffix("\r") for ln in raw]


def _compare(rules_path: Path, out_path: Path) -> None:
    rules = _lines(rules_path)
    out = _lines(out_path)

    skipped: set[int] = set()
    hc_candidates: list[str] = []
    for ln in out:
        m = _WARN.search(ln)
        if m:
            skipped.add(int(m.group(1)))
        else:
            hc_candidates.append(ln)

    ours: list[str] = []
    for lineno, line in enumerate(rules, start=1):
        if lineno in skipped:
            continue
        try:
            ops = parse_rule(line)
        except InvalidRule as exc:  # pragma: no cover - guards against regressions
            raise AssertionError(f"parse gap at line {lineno} {line!r}: {exc}") from exc
        if not ops:  # comment / blank
            continue
        result = apply_ops(WORD, ops)
        if result is not None:
            ours.append(result.decode("latin-1"))

    for idx, (a, b) in enumerate(zip(ours, hc_candidates)):
        assert a == b, f"line #{idx}: hcrulepy={a!r} hashcat={b!r}"
    assert len(ours) == len(hc_candidates), (
        f"candidate count differs: hcrulepy={len(ours)} hashcat={len(hc_candidates)}"
    )


@pytest.mark.parametrize("rules_name,out_name", ORACLES)
def test_matches_hashcat(rules_name: str, out_name: str) -> None:
    rules_path = DATA / rules_name
    out_path = DATA / out_name
    if not out_path.exists():
        pytest.skip(f"no captured hashcat output at {out_path.name}")
    _compare(rules_path, out_path)
