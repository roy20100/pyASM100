"""Shared global state -- the direct analogue of ASM100.FTN's COMMON blocks.

FORTRAN COMMON blocks are just named chunks of shared storage that every
subroutine which declares them sees and mutates directly. The most faithful
Python analogue is a single global object with one attribute per COMMON
variable, named exactly as in the source, that every ported module imports
and reads/writes the same way the FORTRAN reads/writes COMMON.

    COMMON /GEN/  SYM(40),CODE(5),CODMSK(5),IRADIX, ...
    COMMON /SYM/  OPSYM(8,231),MASKTB(14,4), ...
    COMMON /EXPRST/ EXPRMX,EXPRTB(12,3)

become the ``GEN``, ``SYM``, and ``EXPRST`` sections of the ``G`` singleton
below. Array-valued members are ``FArray`` (1-based, see farray.py);
scalar members are plain attributes initialized to 0, matching FORTRAN's
undefined-but-usually-zero COMMON storage before DATA/assignment runs.
"""

from __future__ import annotations

from .farray import FArray


class _Common:
    def __init__(self):
        # ---- COMMON /GEN/ ----
        self.SYM = FArray(40)
        self.CODE = FArray(5)
        self.CODMSK = FArray(5)
        self.IRADIX = 0
        self.IPGNO = 0
        self.IPGLN = 0
        self.ITITLE = FArray(6)
        self.LIN = FArray(100)
        self.NXC = 0
        self.ALFLG = 0
        self.GVLFLG = 0
        self.NUSYM = 0
        self.LOCNT = 0
        self.ERNUMS = FArray(12, 2)
        self.ERRCNT = 0
        self.IARG = 0
        self.MSKTYP = 0
        self.TABPTR = 0
        self.IVAL = 0
        self.IBRF = 0
        self.IPTR = 0
        self.IPTRX = 0
        self.INLIN = FArray(81)
        self.MCPTR = 0
        self.LSTING = 0
        self.GLNFLG = 0
        self.ERRTOT = 0
        self.IPASS = 0
        self.IT = FArray(3)
        self.IDPXX = FArray(3)
        self.COD = FArray(160)
        self.IORDF = 0
        self.LABFLG = 0
        self.ITTI = 0
        self.ITTO = 0
        self.ISUSYM = 0
        self.NOPSYM = 0
        self.LSTFLG = 0
        self.SLUN = 0
        self.OLUN = 0
        self.LLUN = 0
        self.TLUN = 0
        self.LINNUM = 0
        self.EXTNUM = 0
        self.FIELD = FArray(80)
        self.LINES = 0
        self.INSFLG = 0
        self.NRADIX = 0
        self.IOLIN = FArray(100, 10)
        self.IOPTR = 0
        self.PAGES = 0
        self.INSFG2 = 0
        self.TI = FArray(3)
        self.BLANK = 0
        self.CHARMX = 0
        self.PTR = 0
        self.FLDFLG = 0
        self.SFILE = FArray(31)
        self.TIMES = FArray(10)
        self.DLIM = 0
        self.BRKMX = 0
        self.BFILE = FArray(31)
        self.LFILE = FArray(31)
        self.TFILE = FArray(31)

        # ---- COMMON /SYM/ ----
        self.OPSYM = FArray(8, 231)
        self.MASKTB = FArray(14, 4)
        self.IBKS = 0
        self.CHARS = FArray(37)
        self.ISBT = 0
        self.ARGSYM = FArray(4, 35)
        self.DIGITS = FArray(16)
        self.USRSYM = FArray(200, 5)
        self.PSUSYM = FArray(3, 31)
        self.USRMAX = 0

        # ---- COMMON /EXPRST/ ----
        self.EXPRMX = 0
        self.EXPRTB = FArray(12, 3)


G = _Common()
