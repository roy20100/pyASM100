"""FSYM = FIND OP-CODE SYMBOL (ASM100.FTN line 5253).

Searches OPSYM for a mnemonic matching the packed symbol in SYM(1..3). On
success sets TABPTR to the table index and splits OPSYM(8,TABPTR) into
IARG (processing/handling type) and MSKTYP (mask-table index). On failure
sets TABPTR to 0.
"""

from __future__ import annotations

from .arith import fdiv
from .common import G


def fsym() -> None:
    tabptr = 0
    for k1 in range(1, G.NOPSYM + 1):
        if G.SYM[1] != G.OPSYM[1, k1]:
            continue
        if G.SYM[2] != G.OPSYM[2, k1]:
            continue
        if G.SYM[3] != G.OPSYM[3, k1]:
            continue
        tabptr = k1
        break

    G.TABPTR = tabptr
    if tabptr == 0:
        return

    item = G.OPSYM[8, tabptr]
    iarg = fdiv(item, 256)
    G.IARG = iarg
    G.MSKTYP = item - iarg * 256
