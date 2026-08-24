"""ERRMES = ADD ERR MESS. NUMBER TO LIST (ASM100.FTN line 4629).

Records up to 12 (message number, line number) pairs in ERNUMS for later
output by SNDMES; further errors on the same line beyond 12 are dropped.
"""

from __future__ import annotations

from .common import G


def errmes(mesnum: int) -> None:
    if G.ERRCNT == 12:
        return
    G.ERRCNT += 1
    G.ERNUMS[G.ERRCNT, 1] = mesnum
    G.ERNUMS[G.ERRCNT, 2] = G.LINNUM
