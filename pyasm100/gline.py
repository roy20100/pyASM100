"""GLINE = GET A LINE (ASM100.FTN line 6246).

Gets the next line of text, one character per word in LIN(100): deletes
leading blanks, converts tabs to blanks, strips comments (introduced by
CHARS(17), '"'), and packs semicolon/comma-terminated statements. Loops
(via the original's GOTO 1) until it has a non-blank, non-comment-only
line to hand back, calling WLIN to flush the listing buffer for any line
skipped along the way in pass 2.

Ported as a "block trampoline": one small function per FORTRAN label,
each returning the next block (or None for RETURN), driven by the loop at
the bottom. GLINE has two real GOTO-formed loops (the whole-subroutine
retry at label 1, and the character-copy loop re-entering at label 30),
which is exactly the case structured Python control flow doesn't map onto
cleanly -- this preserves the original's label-level structure so it's
easy to diff against the source.

Returns via COMMON: GLNFLG = -1 EOF, 0 no ';'/',' last seen, 1 ';'/',' was
the last character seen.
"""

from __future__ import annotations

from .box import Box
from .common import G
from .readln import readln
from .wlin import wlin


def gline() -> None:
    symbol = 0
    j = 0

    def l1():
        G.NXC = 1
        flag = Box(0)
        readln(flag)
        f = flag.value
        if f < 0:
            return l80
        if f == 0:
            return l5
        return l90

    def l5():
        nonlocal symbol, j
        for i in range(1, 81):
            j = i
            symbol = G.INLIN[j]
            if symbol == G.CHARS[1]:
                continue
            if symbol != G.CHARS[2]:
                break
        return l20

    def l20():
        if symbol == G.CHARS[17]:
            return l90
        return l30

    def l30():
        nonlocal symbol, j
        G.LIN[G.NXC] = symbol
        G.NXC += 1
        j += 1
        symbol = G.INLIN[j]
        if symbol == G.CHARS[14] or symbol == G.CHARS[15]:
            G.GLNFLG = 1
            return l30
        return l50

    def l50():
        if symbol != G.CHARS[17]:
            return l60
        return l55

    def l55():
        G.LIN[G.NXC] = G.CHARS[3]
        jj = G.NXC
        for _i in range(1, G.NXC + 1):
            jj -= 1
            if jj == 0:
                break
            if G.LIN[jj] != G.CHARS[1]:
                break
            G.LIN[jj] = G.CHARS[3]
            G.LIN[jj + 1] = G.CHARS[1]
        G.NXC = 1
        return None

    def l60():
        if symbol != G.CHARS[3]:
            return l70
        return l55

    def l70():
        nonlocal symbol
        if symbol == G.CHARS[2]:
            symbol = G.CHARS[1]
        if symbol == G.CHARS[1]:
            return l30
        G.GLNFLG = 0
        return l30

    def l80():
        G.GLNFLG = -1
        G.NXC = 1
        return None

    def l90():
        if not (G.IPASS != 2 or G.LSTING != 1 or G.GLNFLG == 1):
            wlin()
            G.IOPTR = 0
        return l1

    blk = l1
    while blk is not None:
        blk = blk()
