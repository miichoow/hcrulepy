"""Position decoding, memory register, and ASCII-only byte-case helpers."""

from dataclasses import dataclass, field

from hcrulepy.errors import InvalidRule


def decode_pos(ch: str) -> int:
    """Decode a hashcat position character: 0-9 -> 0-9, A-Z -> 10-35."""
    if len(ch) != 1:
        raise InvalidRule(f"position must be one character, got {ch!r}")
    if "0" <= ch <= "9":
        return ord(ch) - ord("0")
    if "A" <= ch <= "Z":
        return ord(ch) - ord("A") + 10
    raise InvalidRule(f"invalid position character {ch!r}")


def lower_byte(b: int) -> int:
    return b + 32 if ord("A") <= b <= ord("Z") else b


def upper_byte(b: int) -> int:
    return b - 32 if ord("a") <= b <= ord("z") else b


def toggle_byte(b: int) -> int:
    if ord("A") <= b <= ord("Z"):
        return b + 32
    if ord("a") <= b <= ord("z"):
        return b - 32
    return b


# 256-byte translation tables for whole-word case ops via bytes.translate().
# Derived from the scalar helpers above, so the two paths cannot drift.
LOWER_TABLE = bytes(lower_byte(b) for b in range(256))
UPPER_TABLE = bytes(upper_byte(b) for b in range(256))
TOGGLE_TABLE = bytes(toggle_byte(b) for b in range(256))


@dataclass
class MemoryState:
    memory: bytes = field(default=b"")

    def reset(self) -> None:
        self.memory = b""
