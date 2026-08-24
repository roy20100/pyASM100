"""MAIN = ASM100 MAINLINE (ASM100.FTN line 1).

The top-level driver: initialize (APALI), run PASS1, and if PASS1 didn't
hit real EOF (RETFLG/IFLG != 0) run PASS2, then loop back to APALI again.
In practice this only ever assembles one file per run -- the second trip
through APALI skips the interactive dialog (FIRST != 0) and immediately
tries to read from SLUN, which is already at EOF, so PASS1 sets RETFLG=1
and the loop exits after exactly one assembly. See apali.py and pass1.py
for the detailed reasoning.

Since Python has no equivalent of FORTRAN's load-time DATA initialization
for COMMON block members, tables.init() and optab.init() (TABLES and
OPTAB are never CALLed in the source -- see those modules) must run here,
first, before anything else touches COMMON /SYM/ or /EXPRST/.
"""

from __future__ import annotations

from .apali import apali
from .box import Box
from .common import G
from .fio import fwrite, infile
import pyasm100.optab as optab
import pyasm100.tables as tables
from .pass1 import pass1
from .pass2 import pass2


def main() -> None:
    tables.init()
    optab.init()

    first = Box(0)
    G.INSFLG = 0
    G.LINNUM = 0
    G.PAGES = 0
    G.INSFG2 = 2

    while True:
        apali(first)
        linsav = G.LINNUM
        G.NRADIX = 8
        iflg = Box(0)
        pass1(iflg)
        if iflg.value != 0:
            break
        G.LINNUM = linsav
        G.NRADIX = 8
        G.IOPTR = 0
        pass2()

    fwrite(G.ITTO, "(1X,'ASSEMBLY COMPLETED')", [])

    G.SLUN -= 7
    G.OLUN -= 7
    G.LLUN -= 7
    G.TLUN -= 7
    infile(4, G.SFILE, G.SLUN)
    infile(4, G.BFILE, G.OLUN)
    infile(4, G.LFILE, G.LLUN)
    infile(5, G.TFILE, G.TLUN)


if __name__ == "__main__":
    main()
