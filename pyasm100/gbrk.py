"""GBRK = GETS NEXT BREAK CHARACTER (ASM100.FTN line 6627).

Locates the break character following a symbol/number/field, skipping
(and re-scanning past) blanks. Sets IBRF to the CHARS index of the break
character (0 if it wasn't a recognized break character at all -- i.e. an
alphanumeric character terminated the token).
"""

from __future__ import annotations

from .common import G


def gbrk() -> None:
    l1 = G.FIELD[G.NXC - 1] if G.FLDFLG == 1 else G.LIN[G.NXC - 1]

    while True:
        found = False
        for j1 in range(1, G.BRKMX + 1):
            if l1 != G.CHARS[j1]:
                continue
            G.IBRF = j1
            found = True
            break

        if not found:
            G.IBRF = 0
            G.NXC -= 1
            return

        if G.IBRF != 1:
            return

        l1 = G.FIELD[G.NXC] if G.FLDFLG == 1 else G.LIN[G.NXC]
        G.NXC += 1
