"""PNUM = PRINT NUMBER (ASM100.FTN line 7200).

Converts NUM into ID digits (6 normally, or 5 decimal digits when NXW==1,
the special case for line-number columns) and stores each digit character
into IOLIN(K,LINDX), right-to-left. Handles NUM's sign the same way NUMOUT
does: treat the low 16 bits as unsigned magnitude when NUM is negative.
"""

from __future__ import annotations

import math

from .common import G


def pnum(num: int, lindx: int, nxw: int) -> None:
    id_ = 6
    radix = G.IRADIX
    if nxw == 1:
        radix = 10
        id_ = 5

    inum = num
    nxwr = nxw + id_
    for i in range(1, id_ + 1):
        k = nxwr - i
        if inum >= 0:
            ndig = inum % radix
            inum = inum // radix
        else:
            f = float(inum) + 65536.0
            fr = float(radix)
            ndig = int(math.fmod(f, fr))
            inum = int(f / fr)
        G.IOLIN[k, lindx] = G.DIGITS[ndig + 1]
