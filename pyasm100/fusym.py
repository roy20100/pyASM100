"""FUSYM = FIND USER SYMBOL (ASM100.FTN line 5314).

Searches the first NUSYM rows of USRSYM(200,5) for a row whose first 3
columns match the packed symbol in SYM(1..3). TABPTR is set to the matching
row index, or 0 on failure.
"""

from __future__ import annotations

from .common import G


def fusym() -> None:
    if G.NUSYM >= 1:
        for j in range(1, G.NUSYM + 1):
            if G.SYM[1] != G.USRSYM[j, 1]:
                continue
            if G.SYM[2] != G.USRSYM[j, 2]:
                continue
            if G.SYM[3] != G.USRSYM[j, 3]:
                continue
            G.TABPTR = j
            return
    G.TABPTR = 0
