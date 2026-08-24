"""READLN = READ A NEW LINE (ASM100.FTN line 6048).

Reads one 80-column source line: from SLUN during pass 1 (echoing it to
the TLUN scratch file as it goes), or from TLUN during pass 2 (so a
non-rewindable input device only needs to be read once). Strips trailing
blanks, flags all-blank lines, detects the '[' sentinel that marks EOF of
an $INSERT'd file, and appends a CR marker (CHARS(3)) after the last
significant character.

Returns via ISYM: 1 = blank line, 0 = ok, -1 = EOF.
"""

from __future__ import annotations

from .common import G
from .errmes import errmes
from .fio import fread, fwrite
from .pnum import pnum

_FMT_220 = "(80A1)"
_FMT_221 = "(1X, 80A1)"


def readln(isym) -> None:
    for i in range(1, 81):
        G.INLIN[i] = G.BLANK
    isym.value = 0

    if G.IPASS != 2:
        G.IOPTR = 1
        vals = fread(G.SLUN, _FMT_220)
        if vals is None:
            isym.value = -1
            return
        for i in range(1, 81):
            G.INLIN[i] = vals[i - 1]
        fwrite(G.TLUN, _FMT_221, [G.INLIN[i] for i in range(1, 81)])
    else:
        if G.LSTING == 1:
            G.IOPTR += 1
        if G.IOPTR > 10:
            errmes(1)
            isym.value = 1
            return
        vals = fread(G.TLUN, _FMT_220)
        if vals is None:
            isym.value = -1
            return
        for i in range(1, 81):
            G.INLIN[i] = vals[i - 1]

    if not (G.IPASS == 2 and G.LSTING == 0):
        for i in range(23, 101):
            G.IOLIN[i, G.IOPTR] = G.INLIN[i - 22]

    G.LINNUM += 1
    if G.IPASS == 2 and G.LSTING == 1:
        pnum(G.LINNUM, G.IOPTR, 1)

    found = False
    for i in range(1, 81):
        G.IPTRX = 81 - i
        if G.INLIN[G.IPTRX] != G.BLANK:
            found = True
            break
    if not found:
        isym.value = 1

    if G.INLIN[1] == G.CHARS[37]:
        isym.value = -1
        return

    G.IPTRX += 1
    G.INLIN[G.IPTRX] = G.CHARS[3]
