"""GNUM = GET A NUMBER (ASM100.FTN line 6405).

Called after the caller has already scanned the next character and knows
it's numeric. Digests digits (up to 20) in a radix given by a trailing
suffix -- K=octal (default), B=binary, .=decimal, X=hex -- or NRADIX if no
suffix is present, then converts to a signed 16-bit IVAL.
"""

from __future__ import annotations

from .common import G
from .errmes import errmes
from .farray import FArray
from .gbrk import gbrk


def gnum() -> None:
    idig = FArray(20)
    kt = 0

    while True:
        l1 = G.FIELD[G.NXC] if G.FLDFLG == 1 else G.LIN[G.NXC]
        G.NXC += 1

        j = 0
        found = False
        for i in range(1, 17):
            j = i
            if l1 == G.DIGITS[i]:
                found = True
                break

        if not found:
            break

        if kt > 20:
            errmes(18)
            G.IVAL = 0
            return
        kt += 1
        idig[kt] = j - 1

    if l1 == G.CHARS[26]:
        r = 2.0
    elif l1 == G.CHARS[8]:
        r = 10.0
    elif l1 == G.CHARS[28]:
        r = 16.0
    elif l1 == G.CHARS[25]:
        r = 8.0
    else:
        r = float(G.NRADIX)
        gbrk()
        _gnum_finish(idig, kt, r)
        return

    G.NXC += 1
    gbrk()
    _gnum_finish(idig, kt, r)


def _gnum_finish(idig: FArray, kt: int, r: float) -> None:
    val = 0.0
    for i in range(1, kt + 1):
        if float(idig[i]) >= r:
            errmes(9)
            return
        val = val * r + float(idig[i])

    if val >= 65536.0:
        errmes(18)
        G.IVAL = 0
        return

    if val < 32768.0:
        G.IVAL = int(val)
    elif val == 32768.0:
        G.IVAL = -32767 - 1
    else:
        G.IVAL = int(val - 65536.0)
