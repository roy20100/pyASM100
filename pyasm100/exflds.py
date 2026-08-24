"""EXFLDS = EXTRACTS A FIELD FROM A STRING (ASM100.FTN line 7714).

Extracts a delimited substring from LIN into FIELD. If LBRK==TBRK,
extracts from the current position to the next TBRK. If they differ,
tracks nesting level so "N leading breaks need N+1 trailing breaks"
(e.g. balanced parens). OPT!=0 strips the delimiters themselves from the
extracted FIELD. CR==1 appends a CR marker to FIELD's end.
"""

from __future__ import annotations

from .common import G
from .errmes import errmes
from .gbrk import gbrk


def exflds(lbrk: int, tbrk: int, opt: int, cr: int) -> None:
    for i in range(1, 81):
        G.FIELD[i] = G.CHARS[1]

    G.DLIM = 1
    i = 1
    ilevel = 1

    def l20():
        nonlocal i
        if G.LIN[G.NXC] == lbrk:
            return l40
        if G.LIN[G.NXC] == G.CHARS[3]:
            return l400
        G.NXC += 1
        return l20

    def l40():
        nonlocal i
        if opt != 0:
            return l45
        G.FIELD[1] = G.LIN[G.NXC]
        i = 2
        return l45

    def l45():
        G.NXC += 1
        return l50

    def l50():
        nonlocal ilevel
        if G.LIN[G.NXC] != tbrk:
            return l70
        ilevel -= 1
        if ilevel == 0:
            return l100
        return l70

    def l70():
        nonlocal i, ilevel
        G.FIELD[i] = G.LIN[G.NXC]
        i += 1
        if i > 79:
            return l400
        if G.LIN[G.NXC] == lbrk:
            ilevel += 1
        G.NXC += 1
        if G.LIN[G.NXC] == G.CHARS[3]:
            return l300
        return l50

    def l100():
        nonlocal i
        G.FIELD[i] = G.LIN[G.NXC]
        G.NXC += 1
        if opt != 0:
            G.FIELD[i] = G.CHARS[1]
        if opt == 0:
            i += 1
        if cr == 1:
            G.FIELD[i] = G.CHARS[3]
        G.NXC += 1
        gbrk()
        return None

    def l300():
        G.DLIM = 0
        G.IBRF = 3
        if cr == 1:
            G.FIELD[i] = G.CHARS[3]
        return None

    def l400():
        errmes(1)
        G.IBRF = -1
        G.DLIM = 0
        return None

    if lbrk == tbrk:
        blk = l50
    else:
        blk = l20
    while blk is not None:
        blk = blk()
