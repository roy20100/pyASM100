"""GSYM = GET A SYMBOL (ASM100.FTN line 6530).

Gets the next symbol (user or system) from LIN, or from FIELD when
FLDFLG==1, skipping leading blanks. If the first non-blank character is
itself a break character, that's a failure (ALFLG=-1) -- except the
caller is expected to special-case '=' itself; GSYM doesn't. Otherwise
collects up to 6 characters (packed via PACKS into SYM(1..3)), stopping
at the next break character.

Note: this reuses COMMON INLIN(1..6) as scratch space to build the symbol
before packing -- exactly as the original does -- so it must only be
called when the current line's INLIN content (filled by READLN) is no
longer needed.
"""

from __future__ import annotations

from .common import G
from .gbrk import gbrk
from .packs import packs


def gsym() -> None:
    for i in range(1, 7):
        G.INLIN[i] = G.CHARS[1]
    G.ALFLG = 0
    l2 = 1

    while True:
        l1 = G.FIELD[G.NXC] if G.FLDFLG == 1 else G.LIN[G.NXC]
        G.NXC += 1
        if l1 != G.CHARS[1]:
            break

    for j1 in range(2, G.BRKMX + 1):
        if l1 == G.CHARS[j1]:
            G.ALFLG = -1
            G.IBRF = j1
            G.INLIN[l2] = l1
            return

    while True:
        if l2 <= 6:
            G.INLIN[l2] = l1
        l2 += 1
        l1 = G.FIELD[G.NXC] if G.FLDFLG == 1 else G.LIN[G.NXC]
        G.NXC += 1

        is_break = False
        for j1 in range(1, G.BRKMX + 1):
            if l1 == G.CHARS[j1]:
                is_break = True
                break
        if is_break:
            break

    gbrk()
    packs(3, G.INLIN)
