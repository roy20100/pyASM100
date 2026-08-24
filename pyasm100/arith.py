"""Arithmetic idioms where FORTRAN and Python integer semantics diverge.

FORTRAN INTEGER division truncates toward zero; Python's ``//`` floors
toward negative infinity. The two only differ when signs differ, but
ASM100.FTN relies on truncating division/remainder throughout (e.g. FSYM's
``IARG=ITEM/256; MSKTYP=ITEM-IARG*256`` bit-field unpacking), so every
ported ``/`` on INTEGER operands goes through ``fdiv`` rather than ``//``.
"""

from __future__ import annotations


def fdiv(a: int, b: int) -> int:
    q = abs(a) // abs(b)
    return -q if (a < 0) != (b < 0) else q


# ---------------------------------------------------------------------------
# Undocumented host-dependent 16-bit primitives (no source was provided --
# ADUTIL.MAC only has IOR16/IAND16/INOT16/IADD16/IRSH16/ILSH16/IP16; these
# extra ones are named in GVAL's/FLOAT2's "ROUTINES USED" comments and their
# behavior inferred from call sites, the same way INFILE/DATTIM were).
# ---------------------------------------------------------------------------


def negchk(x: int) -> int:
    """1 if the low 16 bits of x are negative (sign bit set), else 0."""
    return 1 if (x & 0xFFFF) & 0x8000 else 0


def ineg16(x: int) -> int:
    """16-bit two's-complement negate, wrapped (matches FLOAT2's use to
    turn a negative value positive before magnitude conversion)."""
    v = (-x) & 0xFFFF
    return v - 0x10000 if v & 0x8000 else v


def pflt(x: int) -> float:
    """Convert the low 16 bits of x to a REAL, treating them as an
    unsigned magnitude (mirrors NUMOUT's FNUM=NUM; IF(NUM.LT.0)
    FNUM=FNUM+65536.0 idiom -- used after a value has already been
    made non-negative, e.g. by FLOAT2's NEGCHK/INEG16 dance)."""
    return float(x & 0xFFFF)
