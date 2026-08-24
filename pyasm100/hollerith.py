"""Hollerith packing, matching PDP-11 FORTRAN's ``nH`` constants.

``2Hxx`` packs two ASCII characters into one 16-bit word: first character in
the LOW byte, second in the HIGH byte. This byte order isn't documented
anywhere in the source -- it's pinned down by PACKS (ASM100.FTN line 6188),
which packs a run-time character buffer into words comparable against the
``2H``-packed OPSYM/PSUSYM/ARGSYM tables so the assembler can recognize
opcodes at all:

    SYM(I) = IOR16(ILSH16(BUF(J+1),8), IAND16(BUF(J),255))

i.e. BUF(J) (the first character of the pair) goes in the low byte and
BUF(J+1) (the second) in the high byte. Both directions must agree or
opcode/symbol lookups silently never match.

Plain ``A1`` character arrays (``LIN``, ``INLIN``, ``FIELD``, ``SFILE``,
...) are *not* packed -- one ASCII code per array element -- and don't go
through this module.
"""

from __future__ import annotations


def holl(s: str) -> int:
    """Pack up to 2 characters into a word the way ``2Hxx`` would."""
    if len(s) > 2:
        raise ValueError(f"holl() packs at most 2 chars, got {s!r}")
    s = s.ljust(2)
    lo = ord(s[0])
    hi = ord(s[1])
    return (hi << 8) | lo


def unholl(word: int, n: int = 2) -> str:
    """Unpack a Hollerith word back into an ``n``-character string (n=1 or 2)."""
    word &= 0xFFFF
    hi = (word >> 8) & 0xFF
    lo = word & 0xFF
    if n == 1:
        return chr(lo)
    return chr(lo) + chr(hi)
