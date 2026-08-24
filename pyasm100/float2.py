"""FLOAT2 = FLOAT A 2'S COMP INTEGER (ASM100.FTN line 7174).

Converts a 16-bit two's-complement integer to its REAL value: negate first
if negative (tracking the sign separately) since PFLOAT only handles
non-negative magnitudes.
"""

from __future__ import annotations

from .arith import ineg16, negchk, pflt


def float2(i: int) -> float:
    ii = i
    sign1 = 1.0
    if negchk(ii) != 0:
        sign1 = -1.0
        ii = ineg16(ii)
    return sign1 * pflt(ii)
