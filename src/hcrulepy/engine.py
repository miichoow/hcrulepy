"""Rule line parser and the RuleEngine."""

from __future__ import annotations

import sys
from collections.abc import Iterable, Iterator
from pathlib import Path

from hcrulepy.errors import InvalidRule, RejectCandidate
from hcrulepy.memory import MemoryState, decode_pos
from hcrulepy.rules import CLASS_REGISTRY, REGISTRY, char_class

Op = tuple  # ("std", cmd, args) or ("cls", ccmd, cls, extra)


def _read_arg(spec_ch: str, line: str, i: int) -> tuple[object, int]:
    """Read one argument char per spec code ('P' or 'C'); return (value, next_index)."""
    if i >= len(line):
        raise InvalidRule(f"missing argument in rule {line!r}")
    ch = line[i]
    if spec_ch == "P":
        if ch == "p":
            raise InvalidRule("p-position register is not supported")
        return decode_pos(ch), i + 1
    # spec_ch == "C": literal char as one byte.
    # hashcat honours a "\xHH" hex escape wherever a single literal char is
    # read (e.g. `$\x64` appends byte 0x64). A lone "\" not followed by a
    # valid "\xHH" is treated as a literal backslash.
    if ch == "\\" and line[i + 1 : i + 2] == "x":
        hexpair = line[i + 2 : i + 4]
        if len(hexpair) == 2 and all(h in "0123456789abcdefABCDEF" for h in hexpair):
            return bytes([int(hexpair, 16)]), i + 4
    return ch.encode("latin-1"), i + 1


def _parse_class_token(line: str, i: int) -> tuple[frozenset, int]:
    if i + 1 >= len(line) or line[i] != "?":
        raise InvalidRule(f"expected ?C class token in {line!r}")
    return char_class(line[i : i + 2]), i + 2


def parse_rule(line: str) -> list[Op]:
    line = line.rstrip("\r\n")
    if not line or line.lstrip().startswith("#"):
        return []
    ops: list[Op] = []
    i = 0
    n = len(line)
    while i < n:
        c = line[i]
        if c == " " or c == "\t":
            i += 1
            continue
        if c == "~":
            i += 1
            if i >= n:
                raise InvalidRule(f"dangling ~ in {line!r}")
            ccmd = line[i]
            if ccmd not in CLASS_REGISTRY:
                raise InvalidRule(f"unknown class command ~{ccmd} in {line!r}")
            i += 1
            _cfunc, cspec = CLASS_REGISTRY[ccmd]
            extra: list = []
            # Positional ("P") args come BEFORE the class token (e.g. ~=N?C,
            # ~%N?C); literal-char ("C") args come AFTER it (e.g. ~sY?C).
            for sp in cspec:
                if sp != "P":
                    continue
                val, i = _read_arg(sp, line, i)
                extra.append(val)
            cls, i = _parse_class_token(line, i)
            for sp in cspec:
                if sp != "C":
                    continue
                val, i = _read_arg(sp, line, i)
                extra.append(val)
            ops.append(("cls", ccmd, cls, tuple(extra)))
            continue
        if c not in REGISTRY:
            raise InvalidRule(f"unknown rule command {c!r} in {line!r}")
        i += 1
        _sfunc, spec = REGISTRY[c]
        args: list = []
        for sp in spec:
            val, i = _read_arg(sp, line, i)
            args.append(val)
        ops.append(("std", c, tuple(args)))
    return ops


def apply_ops(word: bytes, ops: list[Op], mem: MemoryState | None = None) -> bytes | None:
    mem = mem or MemoryState()
    w = word
    try:
        for op in ops:
            if op[0] == "std":
                sfunc, _sspec = REGISTRY[op[1]]
                w = sfunc(w, op[2], mem)
            else:
                cfunc, _cspec = CLASS_REGISTRY[op[1]]
                w = cfunc(w, op[2], op[3], mem)
    except RejectCandidate:
        return None
    return w


def apply_rule(word: str, rule: str) -> str | None:
    ops = parse_rule(rule)
    out = apply_ops(word.encode("latin-1"), ops)
    return None if out is None else out.decode("latin-1")


def _iter_rule_lines(path: str | Path) -> list[str]:
    """Split a rule file into lines byte-exactly, mirroring cli.py's _iter_words.

    Splits only on "\\n" (not on other Unicode line boundaries such as
    \\x0b, \\x0c, \\x1c, \\x85, ...) and strips a single trailing "\\r"
    per line, so rule-file parsing matches hashcat's byte-exact behavior.
    """
    text = Path(path).read_text(encoding="latin-1")
    lines = text.split("\n")
    return [line.removesuffix("\r") for line in lines]


class RuleEngine:
    def __init__(self, rules: Iterable[str], skip_invalid: bool = False) -> None:
        self._ops: list[list[Op]] = []
        for lineno, line in enumerate(rules, start=1):
            try:
                ops = parse_rule(line)
            except InvalidRule as exc:
                if skip_invalid:
                    print(
                        f"hcrulepy: warning: line {lineno}: {exc} (line: {line!r})", file=sys.stderr
                    )
                    continue
                raise InvalidRule(f"line {lineno}: {exc} (line: {line!r})") from exc
            if ops:
                self._ops.append(ops)

    @classmethod
    def from_file(cls, path: str | Path, skip_invalid: bool = False) -> RuleEngine:
        return cls.from_files([path], skip_invalid=skip_invalid)

    @classmethod
    def from_files(cls, paths: Iterable[str | Path], skip_invalid: bool = False) -> RuleEngine:
        # Parsed per-file (rather than delegating to __init__ on a merged line
        # list) so an InvalidRule error can report which rule file it came
        # from, not just a line number into the concatenated stream.
        ops: list[list[Op]] = []
        for p in paths:
            for lineno, line in enumerate(_iter_rule_lines(p), start=1):
                try:
                    parsed = parse_rule(line)
                except InvalidRule as exc:
                    if skip_invalid:
                        print(
                            f"hcrulepy: warning: {p}:{lineno}: {exc} (line: {line!r})",
                            file=sys.stderr,
                        )
                        continue
                    raise InvalidRule(f"{p}:{lineno}: {exc} (line: {line!r})") from exc
                if parsed:
                    ops.append(parsed)
        engine = cls.__new__(cls)
        engine._ops = ops
        return engine

    @staticmethod
    def check_files(paths: Iterable[str | Path]) -> list[tuple[str, int, str, str]]:
        """Validate rule files without building an engine.

        Returns a list of (path, line_number, line_text, error_message) for
        every line that fails to parse; empty if all files are clean.
        """
        errors: list[tuple[str, int, str, str]] = []
        for p in paths:
            for lineno, line in enumerate(_iter_rule_lines(p), start=1):
                try:
                    parse_rule(line)
                except InvalidRule as exc:
                    errors.append((str(p), lineno, line, str(exc)))
        return errors

    def apply(self, word: str | bytes) -> Iterator[str]:
        wb = word.encode("latin-1") if isinstance(word, str) else word
        for ops in self._ops:
            out = apply_ops(wb, ops)
            if out is not None:
                yield out.decode("latin-1")

    def apply_many(self, words: Iterable[str | bytes]) -> Iterator[str]:
        for word in words:
            yield from self.apply(word)
