#!/usr/bin/env python3
"""Throughput benchmark for hcrulepy.

Usage:
    python benchmarks/bench.py [--rules PATH] [--count N] [--word WORD]
"""

import argparse
import time
from pathlib import Path

from hcrulepy import RuleEngine

_DEFAULT_RULES = Path("tests/data/hashcat_v6.2.6_all.rules")
_FALLBACK_RULES = [":", "l", "u", "c", "t", "r", "d", "$1", "^2", "so0", "sa@", "{", "}"]


def _synthetic_words(count: int):
    base = b"Passw0rd"
    for i in range(count):
        yield base + str(i).encode("ascii")


def main() -> None:
    ap = argparse.ArgumentParser(description="hcrulepy throughput benchmark")
    ap.add_argument(
        "--rules", type=Path, default=None, help="rule file (default: bundled all.rules)"
    )
    ap.add_argument("--count", type=int, default=50_000, help="synthetic word count")
    ap.add_argument("--word", default=None, help="benchmark one repeated word instead")
    args = ap.parse_args()

    if args.rules is not None:
        engine = RuleEngine.from_file(args.rules)
        rules_desc = str(args.rules)
    elif _DEFAULT_RULES.exists():
        engine = RuleEngine.from_file(_DEFAULT_RULES)
        rules_desc = str(_DEFAULT_RULES)
    else:
        engine = RuleEngine(_FALLBACK_RULES)
        rules_desc = f"{len(_FALLBACK_RULES)} built-in rules"

    if args.word is not None:
        words = [args.word] * args.count
    else:
        words = list(_synthetic_words(args.count))

    start = time.perf_counter()
    candidates = 0
    for _ in engine.apply_many(words):
        candidates += 1
    elapsed = time.perf_counter() - start

    print(f"rules       : {rules_desc}")
    print(f"words       : {len(words):,}")
    print(f"candidates  : {candidates:,}")
    print(f"elapsed     : {elapsed:.3f} s")
    if elapsed > 0:
        print(f"words/sec   : {len(words) / elapsed:,.0f}")
        print(f"cands/sec   : {candidates / elapsed:,.0f}")


if __name__ == "__main__":
    main()
