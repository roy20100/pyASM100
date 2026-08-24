"""PASS2 = 2ND PASS OF ASSEMBLY (ASM100.FTN line 1730).

The second and final pass (~1100 lines, ~110 labels): rewinds the scratch
file, re-reads every line, and this time actually builds the machine code
-- op-code mnemonics are looked up via FSYM, their mask/bit fields merged
into CODE/CODMSK (checking MASKTB for conflicting fields already set by
an earlier field on the same line), argument fields are filled in via
GFIELD (now that every symbol has its final value from PASS1), and
completed instruction words are appended to the COD buffer and flushed to
the object file in blocks of up to 32 (blocks split into 5-word records:
CODE(1..4) plus an optional CODE(5) relocation triplet). Also handles the
second-pass side of every pseudo-op: $DATA builds DBIB records (including
the more involved TRIPLE floating-literal path), $ENTRY/$GLOBAL/$SUBR
write loader records, "="/$EQU prints the resolved value to the listing,
and $END flushes the final block, the external-symbol block, and (if
requested) the full user symbol table.

Ported as a full block trampoline for the same reason and at the same
scale as PASS1/GVAL/GFIELD. The COD-buffer-flush sequence (labels
520-550, 5010-5045, 5520-5535) is byte-for-byte the same code repeated
three times in the source; factored into one shared helper here.
"""

from __future__ import annotations

from .arith import fdiv
from .bitops import iand16, ilsh16, ior16, irsh16, ip16
from .box import Box
from .common import G
from .errmes import errmes
from .exflds import exflds
from .farray import FArray
from .fio import fwrite, infile
from .fpget import fpget
from .fsym import fsym
from .fusym import fusym
from .gfield import gfield
from .gline import gline
from .gnum import gnum
from .gsym import gsym
from .gval import gval
from .header import header
from .itas import itas
from .pnum import pnum
from .rtoe import rtoe
from .sndmes import sndmes
from .wlin import wlin


def pass2() -> None:
    iwct = 0
    mloc = 0
    elbflg = 0
    flag = 0
    ifflg = 0
    boxflg = 0
    linsv = 0
    id_ = 0  # general-purpose scratch "ID", reused throughout (see PASS1)
    indx = 0
    itype = 0
    rpcnt = 0
    ibrfsv = 0
    nxcsv = 0
    usptrx = 0
    kchar = 0
    sival = 0
    expnt = 0
    hmant = 0
    oldval = 0
    array1 = FArray(6)
    array2 = FArray(6)
    array3 = FArray(6)
    array4 = FArray(6)
    array5 = FArray(6)

    G.IPASS = 2
    G.IORDF = -1
    G.IPTR = 1
    G.IPTRX = 0
    G.LOCNT = -1
    G.LSTING = G.LSTFLG

    def new_extptr() -> Box:
        return Box(0)

    tlun = G.TLUN - 7
    infile(6, G.TFILE, tlun)

    # ---- shared COD-buffer-flush helper (labels 520-550 / 5010-5045 / 5520-5535) ----
    def flush_block():
        nonlocal iwct
        G.MCPTR -= 1
        itas(iwct, array1, 8)
        itas(mloc, array2, 8)
        fwrite(
            G.OLUN, "( 5X,1H0,1X,6A1,1X,6A1,6X,7H***CODE)",
            [array1[i] for i in range(1, 7)] + [array2[j] for j in range(1, 7)],
        )
        id_local = 1
        while id_local <= G.MCPTR:
            itas(G.COD[id_local], array1, 8)
            itas(G.COD[id_local + 1], array2, 8)
            itas(G.COD[id_local + 2], array3, 8)
            itas(G.COD[id_local + 3], array4, 8)
            if G.COD[id_local + 4] == 0:
                fwrite(
                    G.OLUN, "( 2X,4(6A1,1X))",
                    [array1[i] for i in range(1, 7)]
                    + [array2[i] for i in range(1, 7)]
                    + [array3[i] for i in range(1, 7)]
                    + [array4[i] for i in range(1, 7)],
                )
            else:
                flddes = irsh16(iand16(G.COD[id_local + 4], 248), 3)
                ty = iand16(G.COD[id_local + 4], 7)
                arg = irsh16(iand16(G.COD[id_local + 4], ip16(-256)), 8)
                itas(arg, array5, 8)
                fwrite(
                    G.OLUN, "( 2H* ,4(6A1,1X),I6,1X,I6,1X,6A1)",
                    [array1[i] for i in range(1, 7)]
                    + [array2[i] for i in range(1, 7)]
                    + [array3[i] for i in range(1, 7)]
                    + [array4[i] for i in range(1, 7)]
                    + [flddes, ty]
                    + [array5[i] for i in range(1, 7)],
                )
            id_local += 5
        iwct = 0

    # ---- per-line loop ----
    def l100():
        G.LOCNT += 1
        return l110

    def l110():
        for j in range(1, 6):
            G.CODE[j] = 0
            G.CODMSK[j] = 0
        return l135

    def l130():
        return l135

    def l135():
        gline()
        if boxflg != 0:
            return l1550
        if G.GLNFLG != -1 and G.LIN[G.NXC] != G.CHARS[36]:
            return l180
        return l136

    def l136():
        nonlocal linsv, id_
        if G.INSFG2 != 1:
            return l5500
        G.LINNUM = linsv
        G.INSFG2 = 0
        id_ = G.IOPTR - 1
        if id_ <= 0:
            id_ = 1
        G.LINES += 1
        if G.LINES > 54:
            header()
        pnum(G.LINNUM, id_, 1)
        fwrite(G.LLUN, "(1X, 1X,5A1,16X,12H END $INSERT)", [G.IOLIN[i, id_] for i in range(1, 6)])
        G.IOPTR -= 1
        return l135

    def l180():
        nonlocal ifflg
        if ifflg == 1:
            return l1350
        gsym()
        if G.IBRF - 16 != 0:
            return l220
        return l210

    def l210():
        gsym()
        return l220

    def l220():
        if G.ALFLG >= 0:
            return l230
        if G.IBRF == 9:
            return l400
        return l230

    def l230():
        if G.ALFLG < 0 and G.IBRF == 3:
            return l110
        if G.ALFLG < 0:
            return l240
        if G.IBRF == 10:
            return l1020
        if G.IBRF == 9:
            return l1000
        return l4000

    def l240():
        errmes(20)
        return l5200

    # ---- pseudo-op recognition ----
    def l400():
        gsym()
        return l402()

    def l402():
        nonlocal indx
        indx = 0
        for i in range(1, 32):
            match = True
            for j in range(1, 4):
                if G.SYM[j] != G.PSUSYM[j, i]:
                    match = False
                    break
            if match:
                indx = i
                break
        return l420

    def l420():
        """indx==0 (a $-prefixed word that isn't one of the 31 known
        pseudo-ops) falls straight through to l500 ($LOC) in the source
        -- there is no explicit 'unrecognized pseudo-op' branch here,
        unlike PASS1. Not a bug to fix: PASS1 already rejected any line
        it couldn't classify, so a line reaching PASS2 with indx==0
        should be unreachable in practice. Preserved as-is."""
        return _pseudo_op_table.get(indx, l500)

    # ---- $LOC ----
    def l500():
        extptr_box = new_extptr()
        gval(0, extptr_box)
        if G.GVLFLG < 0:
            return l510
        return l520

    def l510():
        errmes(21)
        return l5400

    def l520():
        G.LOCNT = G.IVAL
        if iwct <= 0:
            return l5400
        # Flush using MLOC as it already stands (set back when this block
        # was opened, at l5020) -- the source does NOT reassign MLOC here,
        # it just flushed the block that's ending before LOCNT moves on.
        flush_block()
        return l5400

    # ---- $TITLE ordering check ----
    def l600():
        if G.IORDF <= 0:
            return l620
        return l610

    def l610():
        errmes(32)
        return l5200

    def l620():
        G.IORDF = 1
        return l5400

    # ---- $TASK / $ISR ordering check ----
    def l650():
        if G.IORDF < 0:
            return l660
        return l610

    def l660():
        G.IORDF = 0
        return l5400

    # ---- $ENTRY / $GLOBAL / $SUBR ----
    def l700():
        nonlocal flag
        flag = 0
        return l705()

    def l701():
        nonlocal flag
        flag = 2
        return l705()

    def l702():
        nonlocal flag
        flag = 1
        return l705()

    def l705():
        if G.IORDF >= 2:
            return l610
        gsym()
        if G.ALFLG < 0:
            return l790
        fusym()
        if G.TABPTR > 0:
            return l710
        errmes(35)
        return l5200

    def l710():
        if G.USRSYM[G.TABPTR, 5] == 0:
            return l720
        errmes(33)
        return l5200

    def l720():
        G.USRSYM[G.TABPTR, 5] = 2
        G.IVAL = 0
        if flag == 2:
            return l760
        if G.IBRF == 3 and flag == 0:
            return l740
        if G.IBRF == 3 and flag == 1:
            return l750
        if G.IBRF != 15:
            return l795
        return _l720_getvalue()

    def _l720_getvalue():
        i_save = G.TABPTR
        extptr_box = new_extptr()
        gval(0, extptr_box)
        G.TABPTR = i_save
        if G.GVLFLG >= 0:
            return l730
        errmes(9)
        return l5200

    def l730():
        if flag == 1:
            return l750
        if G.IVAL > 15 or G.IVAL < 0:
            return l795
        return l740

    def l740():
        itas(G.USRSYM[G.TABPTR, 4], array1, 8)
        itas(G.IVAL, array2, 8)
        fwrite(
            G.OLUN,
            "( 4X,2H13,6X,1H1,6X,9H***AENTRY/ 3A2,1X,6A1,6X,1H2,1X,6A1)",
            [G.SYM[1], G.SYM[2], G.SYM[3]]
            + [array1[i] for i in range(1, 7)]
            + [array2[j] for j in range(1, 7)],
        )
        if G.IBRF != 3:
            return l705
        return l5400

    def l750():
        nonlocal id_
        id_ = 1
        return l770()

    def l760():
        nonlocal id_
        id_ = 0
        return l770()

    def l770():
        itas(G.USRSYM[G.TABPTR, 4], array1, 8)
        itas(G.IVAL, array2, 8)
        fwrite(
            G.OLUN,
            "( 5X,1H4,6X,1H1,6X,8H***ENTRY/3A2,1X,6A1,1X,I6,1X,6A1)",
            [G.SYM[1], G.SYM[2], G.SYM[3]]
            + [array1[i] for i in range(1, 7)]
            + [id_]
            + [array2[j] for j in range(1, 7)],
        )
        if G.IBRF != 3:
            return l705
        return l5400

    def l790():
        errmes(20)
        return l5200

    def l795():
        errmes(20)
        return l5200

    # ---- $VAL ----
    def l800():
        if G.IBRF != 0:
            G.NXC -= 1
        return _l800_loop(1)

    def _l800_loop(ix: int):
        if ix > 3:
            return l860()
        extptr_box = new_extptr()
        gval(0, extptr_box)
        if G.GVLFLG < 0:
            return l870
        G.CODE[ix] = G.IVAL
        return _l800_loop(ix + 1)

    def l860():
        iret = Box(0)
        gfield(5, iret)
        table = {1: l5010, 2: l880, 3: l880}
        return table[iret.value]

    def l870():
        errmes(9)
        return l5200

    def l880():
        errmes(20)
        return l5200

    # ---- $FP ----
    def l900():
        if G.IBRF != 0:
            G.NXC -= 1
        nerr = Box(0)
        fpget(nerr)
        return l5010

    # ---- $EQU or "=" ----
    def l1000():
        fusym()
        gsym()
        if G.SYM[1] != G.PSUSYM[1, 4]:
            return l402()
        if G.SYM[2] != G.PSUSYM[2, 4]:
            return l402()
        if G.SYM[3] != G.PSUSYM[3, 4]:
            return l402()
        return l1030

    def l1020():
        if G.SYM[1] != G.OPSYM[1, 196]:
            return l1025
        if G.SYM[2] != G.OPSYM[2, 196]:
            return l1025
        if G.SYM[3] != G.OPSYM[3, 196]:
            return l1025
        return l4000

    def l1025():
        fusym()
        return l1030

    def l1030():
        nonlocal usptrx
        usptrx = 0
        if G.TABPTR <= 0:
            return l1096
        usptrx = G.TABPTR
        if G.LSTING > 0:
            return l1050
        return l1090

    def l1050():
        if usptrx <= 0:
            return l110
        return l1060

    def l1060():
        pnum(G.USRSYM[usptrx, 4], 1, 15)
        G.LINES += 1
        wlin()
        fwrite(G.LLUN, "(/1X)", [])
        return l1090

    def l1090():
        sndmes()
        return l130

    def l1096():
        errmes(15)
        return l5200

    # ---- $INSERT ----
    def l1100():
        nonlocal linsv
        if G.INSFG2 == 1:
            return l130
        if G.LSTING != 0:
            wlin()
        linsv = G.LINNUM
        G.LINNUM = 0
        G.INSFG2 = 1
        return l5400

    # ---- $RADIX ----
    def l1200():
        nonlocal id_
        id_ = G.NRADIX
        G.NRADIX = 10
        extptr_box = new_extptr()
        gval(0, extptr_box)
        G.NRADIX = id_
        if G.GVLFLG < 0:
            return l5450
        if G.IVAL != 8 and G.IVAL != 10 and G.IVAL != 16:
            return l5450
        G.NRADIX = G.IVAL
        return l5450

    # ---- $IF ----
    def l1300():
        nonlocal ifflg
        if ifflg != 0:
            return l5450
        extptr_box = new_extptr()
        gval(0, extptr_box)
        if G.GVLFLG < 0:
            return l5450
        if G.IVAL == 0:
            ifflg = 1
        return l5450

    # ---- $IF-$ENDIF skip-scan ----
    def l1350():
        gsym()
        if G.IBRF != 9:
            return l5450
        gsym()
        if G.SYM[1] != G.PSUSYM[1, 11]:
            return l5450
        if G.SYM[2] != G.PSUSYM[2, 11]:
            return l5450
        if G.SYM[3] != G.PSUSYM[3, 11]:
            return l5450
        return l1370

    def l1370():
        nonlocal ifflg
        ifflg = 0
        return l5450

    # ---- $PAGE ----
    def l1400():
        if G.LSTING == 0:
            return l110
        G.IOPTR -= 1
        if G.IOPTR >= 1:
            wlin()
        fwrite(G.LLUN, "(1H1)", [])
        return l5470

    # ---- $BOX ----
    def l1500():
        nonlocal boxflg
        boxflg = 1
        if G.LSTING == 0:
            return l5470
        G.IOPTR -= 1
        if G.IOPTR >= 1:
            wlin()
        G.LINES += 1
        if G.LINES > 54:
            header()
        pnum(G.LINNUM, 1, 1)
        fwrite(G.LLUN, "(1X, 1X,5A1,16X,79(1H*))", [G.IOLIN[i, 1] for i in range(1, 6)])
        return l5470

    # ---- $ENDBOX-$BOX skip-scan ----
    def l1550():
        gsym()
        if G.IBRF != 9:
            return l1570
        gsym()
        if G.SYM[1] != G.PSUSYM[1, 13]:
            return l1570
        if G.SYM[2] != G.PSUSYM[2, 13]:
            return l1570
        if G.SYM[3] != G.PSUSYM[3, 13]:
            return l1570
        nonlocal boxflg
        boxflg = 0
        if G.LSTING == 0:
            return l5470
        G.IOPTR -= 1
        if G.IOPTR >= 1:
            wlin()
        pnum(G.LINNUM, 1, 1)
        fwrite(G.LLUN, "(1X, 1X,5A1,16X,79(1H*))", [G.IOLIN[i, 1] for i in range(1, 6)])
        return l5470

    def l1570():
        if G.LSTING == 0:
            return l110
        G.IOLIN[22, G.IOPTR] = G.CHARS[6]
        G.IOLIN[100, G.IOPTR] = G.CHARS[6]
        wlin()
        return l110

    # ---- $LIST ----
    def l1600():
        if G.LSTFLG == 0:
            return l110
        G.LSTING = 1
        return l5460

    # ---- $NOLIST ----
    def l1650():
        G.LSTING = 0
        wlin()
        return l110

    # ---- $ENDLIB ----
    def l1700():
        nonlocal elbflg
        elbflg = 1
        return l5500

    # ---- $DATA ----
    def l1800():
        G.DLIM = 0
        if G.GLNFLG != 1 or G.IBRF != 3:
            return l1820
        gline()
        return l1820

    def l1820():
        gsym()
        if G.ALFLG != 0:
            return l1890
        fwrite(G.OLUN, "( 4X,2H11,6X,1H1,6X,7H***DBIB)", [])
        fusym()
        nonlocal indx
        indx = G.TABPTR
        if G.TABPTR == 0:
            return l1890
        return l1830_setup()

    def l1830_setup():
        nonlocal id_, itype
        id_ = irsh16(G.USRSYM[G.TABPTR, 5], 8)
        itype = iand16(irsh16(G.USRSYM[G.TABPTR, 5], 3), 7)
        G.IVAL = G.USRSYM[G.TABPTR, 4]
        if G.IBRF != 11:
            return l1840
        G.NXC -= 1
        exflds(G.CHARS[11], G.CHARS[12], 0, 1)
        G.FLDFLG = 1
        extptr_box = new_extptr()
        gval(0, extptr_box)
        G.FLDFLG = 0
        G.IVAL = (G.IVAL + G.USRSYM[indx, 4]) - 1
        return l1840

    def l1840():
        nonlocal indx, rpcnt
        indx = G.IVAL
        rpcnt = 1
        if G.IBRF != 7:
            return l1850
        gnum()
        rpcnt = G.IVAL
        return l1850

    def l1850():
        nonlocal ibrfsv, nxcsv
        if G.IBRF != 0:
            G.NXC -= 1
        exflds(G.CHARS[15], G.CHARS[15], 1, 1)
        ibrfsv = G.IBRF
        nxcsv = G.NXC
        itas(id_, array1, 8)
        itas(indx, array2, 8)
        itas(rpcnt, array3, 8)
        itas(itype, array4, 8)
        if itype == 4:
            return l1856
        if itype == 1:
            return l1860
        rtoe()
        fwrite(
            G.OLUN, "( 2(6A1),I6,6A1,5X,16A1)",
            [array1[i] for i in range(1, 7)]
            + [array2[j] for j in range(1, 7)]
            + [itype]
            + [array3[k] for k in range(1, 7)]
            + [G.FIELD[l] for l in range(1, 17)],
        )
        return l1880

    def l1856():
        nonlocal itype
        G.FLDFLG = 1
        extptr_box = new_extptr()
        gval(0, extptr_box)
        G.FLDFLG = 0
        if G.IVAL <= 1023:
            return l1857
        errmes(28)
        G.IVAL = iand16(G.IVAL, 1023)
        return l1857

    def l1857():
        nonlocal sival, expnt
        sival = ilsh16(iand16(G.IVAL, 15), 12)
        expnt = irsh16(G.IVAL, 4)
        exflds(G.CHARS[15], G.CHARS[15], 1, 1)
        G.FLDFLG = 1
        extptr_box = new_extptr()
        gval(0, extptr_box)
        G.FLDFLG = 0
        if G.IVAL <= 4095:
            return l1858
        errmes(28)
        G.IVAL = iand16(G.IVAL, 4095)
        return l1858

    def l1858():
        nonlocal hmant, nxcsv, ibrfsv
        hmant = ior16(sival, G.IVAL)
        exflds(G.CHARS[15], G.CHARS[15], 1, 1)
        nxcsv = G.NXC
        ibrfsv = G.IBRF
        return l1860

    def l1860():
        G.FLDFLG = 1
        G.NXC = 1
        return l1861

    def l1861():
        if G.FIELD[G.NXC] != G.CHARS[1]:
            return l1862
        if G.FIELD[G.NXC] == G.CHARS[3]:
            return l1890
        G.NXC += 1
        return l1861

    def l1862():
        if G.FIELD[G.NXC] == G.CHARS[4] or G.FIELD[G.NXC] == G.CHARS[5]:
            return l1867
        if G.FIELD[G.NXC] - G.CHARS[32] < 0:
            return l1864
        if G.FIELD[G.NXC] - G.CHARS[32] == 0:
            return l1867
        return l1863

    def l1863():
        if G.FIELD[G.NXC] - G.CHARS[33] < 0:
            return l1867
        return l1864

    def l1864():
        if G.FIELD[G.NXC] - G.CHARS[34] < 0:
            return l1890
        if G.FIELD[G.NXC] - G.CHARS[34] == 0:
            return l1866
        return l1865

    def l1865():
        if G.FIELD[G.NXC] - G.CHARS[35] <= 0:
            return l1866
        return l1890

    def l1866():
        gsym()
        fusym()
        if G.TABPTR == 0:
            return l1890
        nonlocal id_
        id_ = iand16(G.USRSYM[G.TABPTR, 5], 7)
        if id_ == 1 or id_ == 3 or id_ == 4:
            return l1868
        return l1867

    def l1867():
        extptr_box = new_extptr()
        gval(0, extptr_box)
        return l1869

    def l1868():
        nonlocal itype
        iret = Box(0)
        gfield(6, iret)
        if iret.value == 2:
            return l1890
        itype += 16
        itas(itype, array4, 8)
        G.IVAL = G.CODE[4]
        return l1869

    def l1869():
        G.NXC = nxcsv
        G.IBRF = ibrfsv
        flddes = irsh16(iand16(G.CODE[5], 248), 3)
        id_local = iand16(G.CODE[5], 7)
        arg = irsh16(iand16(G.CODE[5], ip16(-256)), 8)
        itas(arg, array5, 8)
        G.FLDFLG = 0
        if itype == 4 or itype == 20:
            return _l1875(flddes, id_local)
        if G.CODE[5] != 0:
            return _l1871(flddes, id_local)
        fwrite(
            G.OLUN, "( 4(6A1),4X,I6)",
            [array1[i] for i in range(1, 7)]
            + [array2[j] for j in range(1, 7)]
            + [array4[l] for l in range(1, 7)]
            + [array3[k] for k in range(1, 7)]
            + [G.IVAL],
        )
        return l1880

    def _l1871(flddes: int, id_local: int):
        fwrite(
            G.OLUN, "( 4(6A1),4X,3(I6,1X),6A1)",
            [array1[i] for i in range(1, 7)]
            + [array2[j] for j in range(1, 7)]
            + [array4[l] for l in range(1, 7)]
            + [array3[k] for k in range(1, 7)]
            + [G.IVAL, flddes, id_local]
            + [array5[m] for m in range(1, 7)],
        )
        return l1880

    def _l1875(flddes: int, id_local: int):
        if G.CODE[5] != 0:
            return _l1877(flddes, id_local)
        fwrite(
            G.OLUN, "( 4(6A1),I4,I6,4X,I6)",
            [array1[i] for i in range(1, 7)]
            + [array2[j] for j in range(1, 7)]
            + [array4[l] for l in range(1, 7)]
            + [array3[k] for k in range(1, 7)]
            + [expnt, hmant, G.IVAL],
        )
        return l1880

    def _l1877(flddes: int, id_local: int):
        fwrite(
            G.OLUN, "( 4(6A1),I4,I6,4X,3(I6,1X),6A1)",
            [array1[i] for i in range(1, 7)]
            + [array2[j] for j in range(1, 7)]
            + [array4[l] for l in range(1, 7)]
            + [array3[k] for k in range(1, 7)]
            + [expnt, hmant, G.IVAL, flddes, id_local]
            + [array5[m] for m in range(1, 7)],
        )
        return l1880

    def l1880():
        if G.IBRF == 15:
            return l1800
        if G.DLIM == 1:
            return l1800
        if G.IBRF != 3:
            return l1890
        return l5450

    def l1890():
        G.FLDFLG = 0
        errmes(25)
        return l5300

    # ---- MICRO OPERATION (regular op-code) ----
    def l4000():
        fsym()
        if G.TABPTR <= 0:
            return l4200
        G.IORDF = 2
        if G.MSKTYP != 0:
            return l4010
        return l4040

    def l4010():
        for j1 in range(1, 5):
            jx = iand16(G.MASKTB[G.MSKTYP, j1], G.CODMSK[j1])
            if jx != 0:
                return l4020
        return l4040

    def l4020():
        errmes(3)
        return l5200

    def l4040():
        for j1 in range(1, 5):
            if G.MSKTYP != 0:
                G.CODMSK[j1] = ior16(G.MASKTB[G.MSKTYP, j1], G.CODMSK[j1])
            jk = j1 + 3
            G.CODE[j1] = ior16(G.OPSYM[jk, G.TABPTR], G.CODE[j1])
        # A FMUL that's a "pusher" is turned into FMUL TM,MD instead of
        # FMUL FM,FA, to avoid an overflow/underflow some loops could hit
        # (source comment: M.T.C. 6/6/79).
        if G.TABPTR == 197 and (G.IBRF == 3 or G.IBRF == 14):
            G.CODE[4] = ior16(G.CODE[4], 7936)
        if G.IARG - 7 != 0:
            return l4080
        return l4090

    def l4080():
        if G.IARG - 9 != 0:
            return l4110
        return l4090

    def l4090():
        if G.IBRF - 14 != 0:
            return l4100
        return l5000

    def l4100():
        if G.IBRF - 3 != 0:
            return l4110
        return l5000

    def l4110():
        iret = Box(0)
        gfield(G.IARG, iret)
        table = {1: l5000, 2: l5200, 3: l5010}
        return table[iret.value]

    def l4200():
        errmes(15)
        return l5200

    # ---- end of a field: continue with next field, or finish the line ----
    def l5000():
        if G.IBRF - 3 != 0:
            return l5005
        return l5010

    def l5005():
        gsym()
        if G.IBRF == 3 and G.ALFLG < 0 and G.GLNFLG == 1:
            return l135
        return l4000

    # ---- append the completed instruction word to the COD buffer ----
    def l5010():
        if iwct <= 0:
            return l5020
        return l5030

    def l5020():
        nonlocal mloc
        mloc = G.LOCNT
        G.MCPTR = 1
        return l5030

    def l5030():
        nonlocal iwct
        for i in range(1, 6):
            i2 = G.MCPTR + i - 1
            G.COD[i2] = G.CODE[i]
        G.MCPTR += 5
        iwct += 1
        if G.MCPTR < 161:
            return l5050
        flush_block()
        return l5050

    def l5050():
        if G.LSTING <= 0:
            return l5120
        return l5060

    def l5060():
        pnum(G.LOCNT, 1, 7)
        for i in range(1, 5):
            pnum(G.CODE[i], i, 15)
        if G.IOPTR < 5:
            G.IOPTR = 5
        wlin()
        return l5120

    def l5120():
        G.IOPTR = 0
        sndmes()
        return l100

    # ---- error recovery: skip to ';' or CR ----
    def l5200():
        if G.IBRF - 3 != 0:
            return l5210
        return l5010

    def l5210():
        if G.IBRF - 14 != 0:
            return l5220
        return l210

    def l5220():
        nonlocal kchar
        kchar = G.LIN[G.NXC]
        G.NXC += 1
        if kchar - G.CHARS[3] != 0:
            return l5230
        return l5010

    def l5230():
        if kchar - G.CHARS[14] != 0:
            return l5220
        return l210

    # ---- pseudo-ops needing no PASS2 processing, but may have continued lines ----
    def l5300():
        if G.GLNFLG < 0:
            return l136
        if G.GLNFLG == 0:
            return l5450
        return l5350

    def l5350():
        gline()
        return l5300

    # ---- end of statement ----
    def l5400():
        if G.IBRF - 3 != 0:
            return l5410
        return l5450

    def l5410():
        if G.IBRF - 14 != 0:
            return l5420
        return l5440

    def l5420():
        nonlocal kchar
        kchar = G.LIN[G.NXC]
        G.NXC += 1
        if kchar - G.CHARS[3] != 0:
            return l5430
        return l5450

    def l5430():
        if kchar - G.CHARS[14] != 0:
            return l5420
        return l5440

    def l5440():
        nonlocal kchar
        G.NXC += 1
        kchar = G.LIN[G.NXC]
        if kchar != G.CHARS[3]:
            return l5420
        errmes(30)
        gline()
        return l5420

    def l5450():
        if G.LSTING <= 0:
            return l5470
        return l5460

    def l5460():
        wlin()
        return l5470

    def l5470():
        G.IOPTR = 0
        if G.ERRCNT <= 0:
            return l110
        return l5480

    def l5480():
        sndmes()
        return l110

    # ---- $END ----
    def l5500():
        if G.LSTING <= 0:
            return l5520
        return l5510

    def l5510():
        wlin()
        return l5520

    def l5520():
        # As in l520: the source does not reassign MLOC here either, it
        # just flushes the final block using MLOC as set when that block
        # was opened (l5020).
        if iwct <= 0:
            return l5540
        flush_block()
        return l5540

    def l5540():
        nonlocal oldval
        if G.EXTNUM == 0:
            return l5572
        itas(G.EXTNUM, array1, 8)
        fwrite(G.OLUN, "( 5X,2H5 ,6A1,6X,6H***EXT)", [array1[i] for i in range(1, 7)])
        oldval = -1
        for i in range(1, G.NUSYM + 1):
            if iand16(G.USRSYM[i, 5], 7) != 1:
                continue
            if oldval >= irsh16(G.USRSYM[i, 5], 8):
                continue
            oldval = irsh16(G.USRSYM[i, 5], 8)
            fwrite(G.OLUN, "( 3A2)", [G.USRSYM[i, j] for j in range(1, 4)])
        return l5572

    def l5572():
        if elbflg != 1:
            return l5580
        fwrite(G.OLUN, "( 5X,1H7,6X,6H***LEB)", [])
        return None

    def l5580():
        fwrite(G.OLUN, "( 5X,1H1,6X,6H***END/ 3A2)", [G.TI[1], G.TI[2], G.TI[3]])
        G.LINES += 2
        fwrite(G.LLUN, "(/1X, 1X,I4,14H ERROR(S) FOR ,3A2)", [G.ERRTOT, G.TI[1], G.TI[2], G.TI[3]])
        fwrite(G.ITTO, "(/1X, 1X,I4,14H ERROR(S) FOR ,3A2)", [G.ERRTOT, G.TI[1], G.TI[2], G.TI[3]])
        if G.LSTFLG != 1:
            return None
        G.LINES += 5
        if G.LINES > 54:
            header()
        fwrite(G.LLUN, "(1X, 1X,//,14H SYMBOL  VALUE,//1X)", [])
        if G.NUSYM < G.ISUSYM:
            return None
        G.IOLIN[7, 1] = G.CHARS[1]
        G.IOLIN[8, 1] = G.CHARS[1]
        for i in range(G.ISUSYM, G.NUSYM + 1):
            G.IOPTR = 1
            for ii in range(1, 4):
                G.IOLIN[2 * ii - 1, 1] = G.USRSYM[i, ii]
                G.IOLIN[2 * ii, 1] = irsh16(G.USRSYM[i, ii], 8)
            pnum(G.USRSYM[i, 4], 1, 8)
            if iand16(G.USRSYM[i, 5], 7) != 1:
                if iand16(G.USRSYM[i, 5], 7) != 2:
                    wlin()
                    continue
                G.IOLIN[17, 1] = G.CHARS[30]
            else:
                G.IOLIN[17, 1] = G.CHARS[28]
            G.IOLIN[16, 1] = G.CHARS[27]
            G.IOLIN[18, 1] = G.CHARS[29]
            wlin()
        return None

    # ---- pseudo-op index (PSUSYM 1..31) -> handler block ----
    _pseudo_op_table = {
        1: l600, 2: l700, 3: l800, 4: l130, 5: l500, 6: l900,
        7: l5500, 8: l5300, 9: l1100, 10: l1300, 11: l1370,
        12: l1500, 13: l5460, 14: l5460, 15: l1700, 16: l1200,
        17: l1400, 18: l1600, 19: l1650, 20: l5300, 21: l5300,
        22: l5300, 23: l1800, 24: l5300, 25: l702, 26: l5300,
        27: l5450, 28: l701, 29: l5300, 30: l650, 31: l650,
    }

    blk = l100
    while blk is not None:
        blk = blk()
