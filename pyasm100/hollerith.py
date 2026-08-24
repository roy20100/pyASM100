"""Hollerith packing, matching PDP-11 FORTRAN's ``nH`` constants.

``2Hxx`` packs two ASCII characters into one 16-bit word, first character in
the high byte, second in the low byte (standard DEC left-to-right packing).
This is used throughout ASM100 for opcode mnemonics and the break-character
table (``OPSYM``, ``CHARS``, ``DIGITS``, ...). Plain ``A1`` character arrays
(``LIN``, ``INLIN``, ``FIELD``, ``SFILE``, ...) are *not* packed -- one ASCII
code per array element -- and don't go through this module.
"""

from __future__ import annotations


def holl(s: str) -> int:
    """Pack up to 2 characters into a word the way ``2Hxx`` would."""
    if len(s) > 2:
        raise ValueError(f"holl() packs at most 2 chars, got {s!r}")
    s = s.ljust(2)
    hi = ord(s[0])
    lo = ord(s[1])
    return (hi << 8) | lo


def unholl(word: int, n: int = 2) -> str:
    """Unpack a Hollerith word back into an ``n``-character string (n=1 or 2)."""
    word &= 0xFFFF
    hi = (word >> 8) & 0xFF
    lo = word & 0xFF
    if n == 1:
        return chr(hi)
    return chr(hi) + chr(lo)
