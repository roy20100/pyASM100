"""APALI = APAL INITIALIZE (ASM100.FTN line 137).

One-time setup (guarded by FIRST, a by-reference in/out flag) that
defines the three character codes not expressible as a plain 1H Hollerith
literal (CR, EOF-sentinel, tab), opens the temp/source/object/listing
files interactively via INFILE, and asks the listing-on/off and
listing-radix questions. Every call (first or not) does the per-assembly
reset: rewind the scratch file, reset NUSYM/IORDF/LOCNT/error counters,
and reinitialize the handful of OPSYM/IDPXX entries that need a runtime
-32768 constant FORTRAN can't express as a literal (INTEGER overflows at
32767).
"""

from __future__ import annotations

from .bitops import ior16
from .box import Box
from .common import G
from .fio import fwrite, fread, infile
from .hollerith import holl
from .length import length

_YESANS = holl("Y ")
_NOANS = holl("N ")


def apali(first: Box) -> None:
    for i in range(1, 101):
        for j in range(1, 11):
            G.IOLIN[i, j] = G.BLANK

    if first.value != 0:
        _reset_for_pass1()
        return

    G.CHARS[3] = 1
    G.CHARS[36] = 2
    G.CHARS[2] = 8201
    first.value = 1

    G.ITTI = 5
    G.ITTO = 5

    G.SLUN = 1
    G.TLUN = 2
    G.OLUN = 3
    G.LLUN = 4

    fwrite(G.ITTO, "(1X,'ASM100 REL.  1.00 , 09/01/79')", [])

    infile(7, G.TFILE, G.TLUN)

    while True:
        fwrite(G.ITTO, "(1X, 12HSOURCE FILE=)", [])
        vals = fread(G.ITTI, "(30A1)")
        for i in range(1, 31):
            G.SFILE[i] = vals[i - 1]
        length(G.SFILE)
        if infile(1, G.SFILE, G.SLUN) == 0:
            break

    while True:
        fwrite(G.ITTO, "(1X, 12HOBJECT FILE=)", [])
        vals = fread(G.ITTI, "(30A1)")
        for i in range(1, 31):
            G.BFILE[i] = vals[i - 1]
        length(G.BFILE)
        if infile(2, G.BFILE, G.OLUN) == 0:
            break

    while True:
        fwrite(G.ITTO, "(1X, 20HLIST AND ERROR FILE=)", [])
        vals = fread(G.ITTI, "(30A1)")
        for i in range(1, 31):
            G.LFILE[i] = vals[i - 1]
        length(G.LFILE)
        if infile(2, G.LFILE, G.LLUN) == 0:
            break

    G.SLUN += 7
    G.OLUN += 7
    G.LLUN += 7
    G.TLUN += 7

    G.LSTFLG = -1
    while True:
        fwrite(G.ITTO, "(1X, 14HLISTING? (Y/N))", [])
        vals = fread(G.ITTI, "(30A1)")
        for i in range(1, 31):
            G.FIELD[i] = vals[i - 1]
        if G.FIELD[1] == _YESANS:
            G.LSTFLG = 1
        if G.FIELD[1] == _NOANS:
            G.LSTFLG = 0
        if G.LSTFLG == 1:
            break
        if G.LSTFLG == 0:
            _reset_for_pass1()
            return
        fwrite(G.ITTO, "(1X, 3H???)", [])

    while True:
        fwrite(G.ITTO, "(1X, 23HLISTING RADIX (8,10,16))", [])
        vals = fread(G.ITTI, "(I2)")
        G.IRADIX = vals[0]
        if G.IRADIX in (8, 10, 16):
            break
        fwrite(G.ITTO, "(1X, 3H???)", [])

    _reset_for_pass1()


def _reset_for_pass1() -> None:
    """Label 1800 onward -- reached both on the first call (after the
    interactive dialog) and on every subsequent call (FIRST != 0 skips
    straight here), so IPASS=1 belongs here, not in the interactive path."""
    G.IPASS = 1
    tlun = G.TLUN - 7
    infile(6, G.TFILE, tlun)

    G.ISUSYM = 1
    G.NUSYM = 0
    G.NOPSYM = 231
    G.IORDF = 0
    G.LOCNT = -1
    G.LSTING = 0
    G.ERRCNT = 0
    G.ERRTOT = 0
    G.IPTR = 1
    G.IPTRX = 0
    G.FLDFLG = 0

    G.IDPXX[1] = 16384
    G.IDPXX[2] = -32768
    G.IDPXX[3] = -16384
    G.OPSYM[5, 121] = -32768
    G.OPSYM[5, 123] = -32768
    G.OPSYM[5, 125] = -32768
    G.ISBT = -32768
    G.OPSYM[5, 219] = ior16(G.OPSYM[5, 219], G.ISBT)
    G.OPSYM[5, 220] = ior16(G.OPSYM[5, 220], G.ISBT)
