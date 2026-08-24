"""WLIN = WRITE A LINE (ASM100.FTN line 7565).

Flushes the IOPTR queued listing lines from IOLIN(100,10) to LLUN, one
character per word, calling HEADER first if the page is full. FORMAT 500
declares a 132A1 field but the WRITE only ever supplies 100 values -- the
extra descriptors are simply never reached (see fwrite_lines).
"""

from __future__ import annotations

from .common import G
from .fio import fwrite
from .header import header

_FMT_500 = "(1X, 1H ,132A1)"


def wlin() -> None:
    G.LINES += G.IOPTR
    if G.LINES > 54 and G.GLNFLG == 0:
        header()

    lldx = 1
    while True:
        fwrite(G.LLUN, _FMT_500, [G.IOLIN[j, lldx] for j in range(1, 101)])
        lldx += 1
        if lldx > G.IOPTR:
            break
    G.IOPTR = 0

    for i in range(1, 101):
        for j in range(1, 11):
            G.IOLIN[i, j] = G.BLANK
