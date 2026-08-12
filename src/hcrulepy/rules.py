"""Rule operation implementations and the command registry.

Each op has signature: func(w: bytes, args: tuple, mem: MemoryState) -> bytes
Ops either return the transformed word or raise RejectCandidate.
Positions in `args` are ints; char args are one-byte `bytes`.
"""

from __future__ import annotations

from collections.abc import Callable

from hcrulepy.errors import RejectCandidate
from hcrulepy.memory import (
    LOWER_TABLE,
    TOGGLE_TABLE,
    UPPER_TABLE,
    MemoryState,
    lower_byte,
    toggle_byte,
    upper_byte,
)

Op = Callable[[bytes, tuple, MemoryState], bytes]
REGISTRY: dict[str, tuple[Op, str]] = {}


def _reg(cmd: str, spec: str) -> Callable[[Op], Op]:
    def deco(func: Op) -> Op:
        REGISTRY[cmd] = (func, spec)
        return func

    return deco


@_reg(":", "")
def op_noop(w: bytes, args: tuple, mem: MemoryState) -> bytes:
    return w


@_reg("l", "")
def op_lower(w: bytes, args: tuple, mem: MemoryState) -> bytes:
    return w.translate(LOWER_TABLE)


@_reg("u", "")
def op_upper(w: bytes, args: tuple, mem: MemoryState) -> bytes:
    return w.translate(UPPER_TABLE)


@_reg("c", "")
def op_capitalize(w: bytes, args: tuple, mem: MemoryState) -> bytes:
    return w[:1].translate(UPPER_TABLE) + w[1:].translate(LOWER_TABLE)


@_reg("C", "")
def op_invert_capitalize(w: bytes, args: tuple, mem: MemoryState) -> bytes:
    return w[:1].translate(LOWER_TABLE) + w[1:].translate(UPPER_TABLE)


@_reg("t", "")
def op_toggle_all(w: bytes, args: tuple, mem: MemoryState) -> bytes:
    return w.translate(TOGGLE_TABLE)


@_reg("T", "P")
def op_toggle_at(w: bytes, args: tuple, mem: MemoryState) -> bytes:
    n = args[0]
    if n >= len(w):
        return w
    out = bytearray(w)
    out[n] = toggle_byte(out[n])
    return bytes(out)


@_reg("r", "")
def op_reverse(w: bytes, args: tuple, mem: MemoryState) -> bytes:
    return w[::-1]


@_reg("d", "")
def op_duplicate(w: bytes, args: tuple, mem: MemoryState) -> bytes:
    return w + w


@_reg("p", "P")
def op_duplicate_n(w: bytes, args: tuple, mem: MemoryState) -> bytes:
    return w * (args[0] + 1)


@_reg("f", "")
def op_reflect(w: bytes, args: tuple, mem: MemoryState) -> bytes:
    return w + w[::-1]


@_reg("{", "")
def op_rotate_left(w: bytes, args: tuple, mem: MemoryState) -> bytes:
    return w[1:] + w[:1] if w else w


@_reg("}", "")
def op_rotate_right(w: bytes, args: tuple, mem: MemoryState) -> bytes:
    return w[-1:] + w[:-1] if w else w


@_reg("[", "")
def op_truncate_left(w: bytes, args: tuple, mem: MemoryState) -> bytes:
    return w[1:]


@_reg("]", "")
def op_truncate_right(w: bytes, args: tuple, mem: MemoryState) -> bytes:
    return w[:-1]


@_reg("$", "C")
def op_append(w: bytes, args: tuple, mem: MemoryState) -> bytes:
    return w + args[0]


@_reg("^", "C")
def op_prepend(w: bytes, args: tuple, mem: MemoryState) -> bytes:
    return args[0] + w


@_reg("D", "P")
def op_delete_at(w: bytes, args: tuple, mem: MemoryState) -> bytes:
    n = args[0]
    return w[:n] + w[n + 1 :] if n < len(w) else w


@_reg("x", "PP")
def op_extract_range(w: bytes, args: tuple, mem: MemoryState) -> bytes:
    n, m = args
    return w[n : n + m]


@_reg("O", "PP")
def op_omit_range(w: bytes, args: tuple, mem: MemoryState) -> bytes:
    n, m = args
    return w[:n] + w[n + m :]


@_reg("i", "PC")
def op_insert_at(w: bytes, args: tuple, mem: MemoryState) -> bytes:
    n, x = args
    if n > len(w):
        return w
    return w[:n] + x + w[n:]


@_reg("o", "PC")
def op_overwrite_at(w: bytes, args: tuple, mem: MemoryState) -> bytes:
    n, x = args
    if n >= len(w):
        return w
    return w[:n] + x + w[n + 1 :]


@_reg("'", "P")
def op_truncate_at(w: bytes, args: tuple, mem: MemoryState) -> bytes:
    return w[: args[0]]


@_reg("s", "CC")
def op_replace(w: bytes, args: tuple, mem: MemoryState) -> bytes:
    x, y = args
    return w.replace(x, y)


@_reg("@", "C")
def op_purge(w: bytes, args: tuple, mem: MemoryState) -> bytes:
    return w.replace(args[0], b"")


@_reg("z", "P")
def op_dup_first_n(w: bytes, args: tuple, mem: MemoryState) -> bytes:
    return w[:1] * args[0] + w if w else w


@_reg("Z", "P")
def op_dup_last_n(w: bytes, args: tuple, mem: MemoryState) -> bytes:
    return w + w[-1:] * args[0] if w else w


@_reg("q", "")
def op_dup_all(w: bytes, args: tuple, mem: MemoryState) -> bytes:
    return bytes(b for ch in w for b in (ch, ch))


@_reg("y", "P")
def op_dup_block_front(w: bytes, args: tuple, mem: MemoryState) -> bytes:
    n = args[0]
    return w[:n] + w if n <= len(w) else w


@_reg("Y", "P")
def op_dup_block_back(w: bytes, args: tuple, mem: MemoryState) -> bytes:
    n = args[0]
    return w + w[-n:] if 0 < n <= len(w) else w


@_reg("k", "")
def op_swap_front(w: bytes, args: tuple, mem: MemoryState) -> bytes:
    if len(w) < 2:
        return w
    return w[1:2] + w[0:1] + w[2:]


@_reg("K", "")
def op_swap_back(w: bytes, args: tuple, mem: MemoryState) -> bytes:
    if len(w) < 2:
        return w
    return w[:-2] + w[-1:] + w[-2:-1]


@_reg("*", "PP")
def op_swap_at(w: bytes, args: tuple, mem: MemoryState) -> bytes:
    n, m = args
    if n >= len(w) or m >= len(w):
        return w
    out = bytearray(w)
    out[n], out[m] = out[m], out[n]
    return bytes(out)


@_reg("L", "P")
def op_shift_left(w: bytes, args: tuple, mem: MemoryState) -> bytes:
    n = args[0]
    if n >= len(w):
        return w
    out = bytearray(w)
    out[n] = (out[n] << 1) & 0xFF
    return bytes(out)


@_reg("R", "P")
def op_shift_right(w: bytes, args: tuple, mem: MemoryState) -> bytes:
    n = args[0]
    if n >= len(w):
        return w
    out = bytearray(w)
    out[n] = out[n] >> 1
    return bytes(out)


@_reg("+", "P")
def op_ascii_inc(w: bytes, args: tuple, mem: MemoryState) -> bytes:
    n = args[0]
    if n >= len(w):
        return w
    out = bytearray(w)
    out[n] = (out[n] + 1) & 0xFF
    return bytes(out)


@_reg("-", "P")
def op_ascii_dec(w: bytes, args: tuple, mem: MemoryState) -> bytes:
    n = args[0]
    if n >= len(w):
        return w
    out = bytearray(w)
    out[n] = (out[n] - 1) & 0xFF
    return bytes(out)


@_reg(".", "P")
def op_replace_next(w: bytes, args: tuple, mem: MemoryState) -> bytes:
    n = args[0]
    if n + 1 >= len(w):
        return w
    out = bytearray(w)
    out[n] = out[n + 1]
    return bytes(out)


@_reg(",", "P")
def op_replace_prev(w: bytes, args: tuple, mem: MemoryState) -> bytes:
    n = args[0]
    if n == 0 or n >= len(w):
        return w
    out = bytearray(w)
    out[n] = out[n - 1]
    return bytes(out)


def _titlecase(w: bytes, seps: bytes) -> bytes:
    out = bytearray(lower_byte(b) for b in w)
    start = True
    for i, b in enumerate(out):
        if start:
            out[i] = upper_byte(b)
        start = b in seps
    return bytes(out)


@_reg("E", "")
def op_title(w: bytes, args: tuple, mem: MemoryState) -> bytes:
    return _titlecase(w, b" ")


@_reg("e", "C")
def op_title_sep(w: bytes, args: tuple, mem: MemoryState) -> bytes:
    return _titlecase(w, args[0])


@_reg("3", "PC")
def op_toggle_nth_sep(w: bytes, args: tuple, mem: MemoryState) -> bytes:
    n, sep = args
    sep_byte = sep[0]
    count = 0
    for i, b in enumerate(w):
        if b == sep_byte:
            if count == n and i + 1 < len(w):
                out = bytearray(w)
                out[i + 1] = toggle_byte(out[i + 1])
                return bytes(out)
            count += 1
    return w


@_reg("M", "")
def op_memorize(w: bytes, args: tuple, mem: MemoryState) -> bytes:
    mem.memory = w
    return w


@_reg("X", "PPP")
def op_extract_memory(w: bytes, args: tuple, mem: MemoryState) -> bytes:
    n, m, i = args
    chunk = mem.memory[n : n + m]
    if i > len(w):
        return w
    return w[:i] + chunk + w[i:]


@_reg("4", "")
def op_append_memory(w: bytes, args: tuple, mem: MemoryState) -> bytes:
    return w + mem.memory


@_reg("6", "")
def op_prepend_memory(w: bytes, args: tuple, mem: MemoryState) -> bytes:
    return mem.memory + w


@_reg("Q", "")
def op_reject_memory_equal(w: bytes, args: tuple, mem: MemoryState) -> bytes:
    if w == mem.memory:
        raise RejectCandidate
    return w


@_reg("<", "P")
def op_reject_len_gt(w: bytes, args: tuple, mem: MemoryState) -> bytes:
    if len(w) > args[0]:
        raise RejectCandidate
    return w


@_reg(">", "P")
def op_reject_len_lt(w: bytes, args: tuple, mem: MemoryState) -> bytes:
    if len(w) < args[0]:
        raise RejectCandidate
    return w


@_reg("_", "P")
def op_reject_len_ne(w: bytes, args: tuple, mem: MemoryState) -> bytes:
    if len(w) != args[0]:
        raise RejectCandidate
    return w


@_reg("!", "C")
def op_reject_contains(w: bytes, args: tuple, mem: MemoryState) -> bytes:
    if args[0] in w:
        raise RejectCandidate
    return w


@_reg("/", "C")
def op_reject_not_contains(w: bytes, args: tuple, mem: MemoryState) -> bytes:
    if args[0] not in w:
        raise RejectCandidate
    return w


@_reg("(", "C")
def op_reject_not_start(w: bytes, args: tuple, mem: MemoryState) -> bytes:
    if not w.startswith(args[0]):
        raise RejectCandidate
    return w


@_reg(")", "C")
def op_reject_not_end(w: bytes, args: tuple, mem: MemoryState) -> bytes:
    if not w.endswith(args[0]):
        raise RejectCandidate
    return w


@_reg("=", "PC")
def op_reject_not_at(w: bytes, args: tuple, mem: MemoryState) -> bytes:
    n, x = args
    if n >= len(w) or w[n : n + 1] != x:
        raise RejectCandidate
    return w


@_reg("%", "PC")
def op_reject_count_lt(w: bytes, args: tuple, mem: MemoryState) -> bytes:
    n, x = args
    if w.count(x) < n:
        raise RejectCandidate
    return w


_PRINTABLE_SPECIAL = frozenset(b" !\"#$%&'()*+,-./:;<=>?@[\\]^_`{|}~")


def char_class(token: str) -> frozenset[int]:
    """Resolve a hashcat ?C class token to a set of byte values."""
    if len(token) != 2 or token[0] != "?":
        from hcrulepy.errors import InvalidRule

        raise InvalidRule(f"invalid class token {token!r}")
    c = token[1]
    if c == "l":
        return frozenset(range(ord("a"), ord("z") + 1))
    if c == "u":
        return frozenset(range(ord("A"), ord("Z") + 1))
    if c == "d":
        return frozenset(range(ord("0"), ord("9") + 1))
    if c == "h":
        return frozenset(range(ord("0"), ord("9") + 1)) | frozenset(range(ord("a"), ord("f") + 1))
    if c == "H":
        return frozenset(range(ord("0"), ord("9") + 1)) | frozenset(range(ord("A"), ord("F") + 1))
    if c == "s":
        return _PRINTABLE_SPECIAL
    if c == "a":
        return frozenset(range(0x20, 0x7F))
    if c == "b":
        return frozenset(range(0x100))
    from hcrulepy.errors import InvalidRule

    raise InvalidRule(f"unknown class {token!r}")


ClassOp = Callable[[bytes, frozenset[int], tuple, MemoryState], bytes]
CLASS_REGISTRY: dict[str, tuple[ClassOp, str]] = {}


def _creg(cmd: str, spec: str) -> Callable[[ClassOp], ClassOp]:
    def deco(func: ClassOp) -> ClassOp:
        CLASS_REGISTRY[cmd] = (func, spec)
        return func

    return deco


@_creg("s", "C")
def cop_replace(w: bytes, cls: frozenset[int], extra: tuple, mem: MemoryState) -> bytes:
    y = extra[0]
    return bytes(y[0] if b in cls else b for b in w)


@_creg("@", "")
def cop_remove(w: bytes, cls: frozenset[int], extra: tuple, mem: MemoryState) -> bytes:
    return bytes(b for b in w if b not in cls)


@_creg("e", "")
def cop_capitalize(w: bytes, cls: frozenset[int], extra: tuple, mem: MemoryState) -> bytes:
    out = bytearray(w)
    start = True
    for i, b in enumerate(out):
        if start:
            out[i] = upper_byte(b)
        start = b in cls
    return bytes(out)


@_creg("!", "")
def cop_reject_contains(w: bytes, cls: frozenset[int], extra: tuple, mem: MemoryState) -> bytes:
    if any(b in cls for b in w):
        raise RejectCandidate
    return w


@_creg("/", "")
def cop_reject_not_contains(w: bytes, cls: frozenset[int], extra: tuple, mem: MemoryState) -> bytes:
    if not any(b in cls for b in w):
        raise RejectCandidate
    return w


@_creg("(", "")
def cop_reject_first(w: bytes, cls: frozenset[int], extra: tuple, mem: MemoryState) -> bytes:
    if not w or w[0] not in cls:
        raise RejectCandidate
    return w


@_creg(")", "")
def cop_reject_last(w: bytes, cls: frozenset[int], extra: tuple, mem: MemoryState) -> bytes:
    if not w or w[-1] not in cls:
        raise RejectCandidate
    return w


@_creg("=", "P")
def cop_reject_at(w: bytes, cls: frozenset[int], extra: tuple, mem: MemoryState) -> bytes:
    n = extra[0]
    if n >= len(w) or w[n] not in cls:
        raise RejectCandidate
    return w


@_creg("%", "P")
def cop_reject_count(w: bytes, cls: frozenset[int], extra: tuple, mem: MemoryState) -> bytes:
    n = extra[0]
    if sum(1 for b in w if b in cls) < n:
        raise RejectCandidate
    return w
