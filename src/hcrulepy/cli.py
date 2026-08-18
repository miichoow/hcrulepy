"""Command-line interface mirroring `hashcat --stdout -r ... wordlist`."""

from __future__ import annotations

import argparse
import sys
from collections.abc import Iterable, Iterator

from hcrulepy.engine import RuleEngine
from hcrulepy.errors import InvalidRule


def _strip_eol(line: bytes) -> bytes:
    if line.endswith(b"\n"):
        line = line[:-1]
    if line.endswith(b"\r"):
        line = line[:-1]
    return line


def _iter_words(wordlist: str | None) -> Iterator[bytes]:
    # Stream line-by-line from the binary stream (constant memory). Iterating a
    # binary file object yields lines including the trailing "\n"; stripping a
    # single "\n" then "\r" reproduces the exact sequence of the previous
    # split(b"\n")+drop-trailing-empty logic for every input shape.
    if wordlist is None or wordlist == "-":
        for line in sys.stdin.buffer:
            yield _strip_eol(line)
    else:
        with open(wordlist, "rb") as fh:
            for line in fh:
                yield _strip_eol(line)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="hcrulepy",
        description="Apply hashcat rules to words (hashcat --stdout compatible).",
    )
    parser.add_argument(
        "-r", "--rules", action="append", default=[], metavar="PATH", help="rule file (repeatable)"
    )
    parser.add_argument("--word", metavar="WORD", help="apply rules to a single word")
    parser.add_argument(
        "--check",
        action="store_true",
        help="validate the rule files and exit, without applying them to a wordlist",
    )
    parser.add_argument(
        "-k",
        "--skip-invalid",
        action="store_true",
        help="warn and skip invalid rule lines instead of stopping",
    )
    parser.add_argument("wordlist", nargs="?", help="wordlist file, or - for stdin")
    args = parser.parse_args(argv)

    if not args.rules:
        parser.error("at least one -r/--rules file is required")

    if args.check:
        try:
            errors = RuleEngine.check_files(args.rules)
        except OSError as exc:
            print(f"hcrulepy: {exc}", file=sys.stderr)
            return 2
        for path, lineno, line, message in errors:
            print(f"{path}:{lineno}: {message} (line: {line!r})", file=sys.stderr)
        if errors:
            print(f"hcrulepy: {len(errors)} invalid rule line(s)", file=sys.stderr)
            return 1
        print("hcrulepy: OK")
        return 0

    try:
        engine = RuleEngine.from_files(args.rules, skip_invalid=args.skip_invalid)
    except (OSError, InvalidRule) as exc:
        print(f"hcrulepy: {exc}", file=sys.stderr)
        return 2

    if args.word is not None:
        words: Iterable[bytes] = [args.word.encode("latin-1")]
    else:
        # streamed lazily; a missing/unreadable wordlist raises OSError during
        # iteration below, which is caught and reported there.
        words = _iter_words(args.wordlist)

    out = sys.stdout.buffer
    buf = bytearray()
    flush_at = 64 * 1024
    try:
        for candidate in engine.apply_many(words):
            buf += candidate.encode("latin-1")
            buf += b"\n"
            if len(buf) >= flush_at:
                out.write(buf)
                buf.clear()
        if buf:
            out.write(buf)
    except OSError as exc:
        print(f"hcrulepy: {exc}", file=sys.stderr)
        return 2
    except InvalidRule as exc:  # pragma: no cover
        # Defensive: parsing (the only source of InvalidRule) already
        # completed successfully above, before candidates are generated.
        print(f"hcrulepy: {exc}", file=sys.stderr)
        return 2
    out.flush()
    return 0
