"""16-bit integer intrinsics from ADUTIL.MAC.

ASM100.FTN runs on a 16-bit host (the PDP-11) where FORTRAN INTEGERs are
16-bit two's-complement words and native ``.AND.``/``.OR.``/``+`` etc. only
operate on 16 bits, wrapping on overflow. Python ints are arbitrary
precision, so every one of these routines masks/wraps its result back to a
signed 16-bit value the same way the PDP-11 assembly in ADUTIL.MAC does.
"""

from __future__ import annotations

_MASK = 0xFFFF
_SIGN = 0x8000


def to_signed16(x: int) -> int:
    x &= _MASK
    return x - 0x10000 if x & _SIGN else x


def ior16(ia: int, ib: int) -> int:
    return to_signed16((ia & _MASK) | (ib & _MASK))


def iand16(ia: int, ib: int) -> int:
    return to_signed16((ia & _MASK) & (ib & _MASK))


def inot16(ia: int) -> int:
    return to_signed16(~ia)


def iadd16(ia: int, ib: int) -> int:
    return to_signed16(ia + ib)


def irsh16(ia: int, n: int) -> int:
    """Logical (zero-fill) right shift of the low 16 bits by n places."""
    if n <= 0:
        return to_signed16(ia)
    return to_signed16((ia & _MASK) >> n)


def ilsh16(ia: int, n: int) -> int:
    """Logical (zero-fill) left shift of the low 16 bits by n places."""
    if n <= 0:
        return to_signed16(ia)
    return to_signed16((ia & _MASK) << n)


def ip16(ia: int) -> int:
    """Convert a signed 16-bit value to its 0..65535 unsigned equivalent."""
    return ia + 0x10000 if ia < 0 else ia
