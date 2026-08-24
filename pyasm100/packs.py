"""PACKS = PACKS CHARACTERS 2 PER WORD (ASM100.FTN line 6188).

Takes up to 40 pairs of A1 characters from BUF and packs them 2-per-word
into SYM (COMMON /GEN/), the way GSYM builds a symbol for table lookup
against the Hollerith-packed OPSYM/PSUSYM/ARGSYM tables. A bare carriage
-return char (CHARS(3)) is treated as a blank (CHARS(1)) so trailing
line-terminator padding doesn't leak into the packed symbol.
"""

from __future__ import annotations

from .common import G
from .bitops import iand16, ilsh16, ior16
from .farray import FArray


def packs(maxnum: int, buf: FArray) -> None:
    for i in range(1, 41):
        G.SYM[i] = G.BLANK

    for i in range(1, maxnum + 1):
        j = i + (i - 1)
        if buf[j] == G.CHARS[3]:
            buf[j] = G.CHARS[1]
        if buf[j + 1] == G.CHARS[3]:
            buf[j + 1] = G.CHARS[1]
        G.SYM[i] = ior16(ilsh16(buf[j + 1], 8), iand16(buf[j], 255))
