"""PASS1 = 1ST PASS OF ASSEMBLY (ASM100.FTN line 416).

The largest subroutine in the source (~1300 lines): reads every source
line once, builds the user symbol table (labels get the current LOCNT,
"=" / $EQU define named values, $EXT/$INTEGER/$REAL/$TRIPLE declare
externals), processes every pseudo-op that has first-pass effects
($TITLE, $RADIX, $INSERT, $IF/$ENDIF, $BOX/$ENDBOX, $COMMON, $COMIO,
$PARAM, $CALL's macro expansion, $TASK, $ISR, &LIB/&ENDLIB), and stops at
$END. Regular op-code lines are *not* decoded here -- PASS1 only needs to
know that a line consumes one location (LOCNT increments once per line at
the top of the loop, unless the previous line ended in a continuation
comma/semicolon); actually validating and encoding an op-code's fields
happens in PASS2, which has every symbol's final value available.

Ported as a full block trampoline, the same approach as GVAL/FPGET/RTOE/
GFIELD and for the same reason: ~140 labels including several loops
(100 the whole-line loop, 245 the "no-op pseudo-op, get continuation"
loop, the $COMMON/$PARAM/$CALL parameter-list loops) reached from many
different pseudo-op handlers via shared error/success landing points
(100, 110, 2000, 2010, 3000, 3010, 3030, 3040).

Returns via COMMON: nothing directly meaningful; via RETFLG (a Box,
matching the source's by-reference output param): 1 = real EOF reached
(caller should stop), 0 otherwise (only ever set right before the $END
path's RETURN, or the genuine-EOF path's RETURN -- every other path loops
back into the per-line loop).
"""

from __future__ import annotations

from .arith import fdiv
from .bitops import iand16, ilsh16, ior16, irsh16
from .box import Box
from .common import G
from .errmes import errmes
from .exflds import exflds
from .farray import FArray
from .fpget import fpget
from .gline import gline
from .gnum import gnum
from .gsym import gsym
from .gval import gval
from .fusym import fusym
from .header import header
from .hollerith import holl
from .itas import itas
from .fio import fwrite, infile
from .length import length
from .pnum import pnum
from .sndmes import sndmes
from .wlin import wlin

_BLKCMN = (holl(".B"), holl("LA"), holl("NK"))
_LOCCMN = (holl(".L"), holl("OC"), holl("AL"))
_SI, _SR, _SIP, _SOP = holl("I "), holl("R "), holl("IP"), holl("OP")
_SM, _SS, _ST = holl("M "), holl("S "), holl("T ")

def pass1(retflg: Box) -> None:
    ifflg = 0
    boxflg = 0
    linflg = 0
    comcnt = 0
    id_ext = 0  # the source's general-purpose scratch "ID" local, reused
    # across $EXT/$INTEGER/$REAL/$TRIPLE's type code, $RADIX's save/
    # restore, and later $COMMON/$COMIO/$PARAM/$CALL/$TASK sections --
    # named for its first use here, not $EXT-specific.
    retflg.value = 0
    ibuf = FArray(3)
    indx = 0
    indx1 = 0
    itype = 0
    oldtyp = 0
    elmcnt = 0
    comptr = 0
    ibrfsv = 0
    nxcsv = 0
    slunsv = 0
    linsv = 0
    insfil = FArray(31)
    array1 = FArray(6)
    array2 = FArray(6)
    val1 = 0
    val2 = 0
    i_count = 0
    task_j = task_k = task_l = task_m = task_id = 0

    G.GLNFLG = 0
    G.EXTNUM = 0
    G.LINES = 9999

    def new_extptr() -> Box:
        return Box(0)

    # ---- per-line loop ----
    def l100():
        if G.GLNFLG == 0:
            G.LOCNT += 1
        return l110

    def l110():
        G.LABFLG = 0
        return l111

    def l111():
        gline()
        if boxflg != 0:
            return l1320
        if G.GLNFLG < 0:
            return l115
        return l130

    def l115():
        nonlocal boxflg
        if G.INSFLG == 0:
            return l120
        G.LINES += 1
        if G.LINES > 54:
            header()
        fwrite(G.LLUN, "(1X, 12H END $INSERT)", [])
        fwrite(G.TLUN, "( 1H[)", [])
        slun = G.SLUN - 7
        infile(4, insfil, slun)
        G.SLUN = slunsv
        G.LINNUM = linsv
        G.INSFLG = 0
        return l110

    def l120():
        if linflg == 0:
            return l225
        errmes(23)
        return l1000

    def l225():
        retflg.value = 1
        return l1000

    def l130():
        nonlocal ifflg, linflg
        if ifflg != 0:
            return l1250
        gsym()
        linflg = 1
        if G.IBRF != 16:
            return l200
        if G.ALFLG < 0:
            return l155
        return l160

    def l155():
        errmes(20)
        return l2010

    def l160():
        if G.NUSYM == 0:
            return l175
        fusym()
        if G.TABPTR == 0:
            return l175
        errmes(2)
        return l2000

    def l175():
        G.NUSYM += 1
        if G.NUSYM > G.USRMAX:
            return l3000
        G.USRSYM[G.NUSYM, 1] = G.SYM[1]
        G.USRSYM[G.NUSYM, 2] = G.SYM[2]
        G.USRSYM[G.NUSYM, 3] = G.SYM[3]
        G.USRSYM[G.NUSYM, 4] = G.LOCNT
        G.USRSYM[G.NUSYM, 5] = 0
        G.LABFLG = -1
        gsym()
        if G.IBRF == 3 and G.ALFLG == -1:
            return l111
        return l200

    # ---- pseudo-op recognition ----
    def l200():
        if G.IBRF != 9:
            return l500
        if G.ALFLG >= 0:
            return l520
        gsym()
        if G.ALFLG >= 0:
            return l210
        errmes(20)
        return l2010

    def l210():
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
        return l240

    def l240():
        blk = _pseudo_op_table.get(indx)
        if blk is None:
            return l3010
        return blk

    # ---- "=" / $EQU assignment ----
    def l500():
        if G.IBRF - 10 != 0:
            return l100
        return l520

    def l520():
        ibuf[1] = G.SYM[1]
        ibuf[2] = G.SYM[2]
        ibuf[3] = G.SYM[3]
        if G.IBRF == 10:
            return l540
        if G.IBRF != 9:
            return l100
        gsym()
        if G.ALFLG < 0:
            return l100
        return l530

    def l530():
        if G.SYM[1] != G.PSUSYM[1, 4]:
            return l3030
        if G.SYM[2] != G.PSUSYM[2, 4]:
            return l3030
        if G.SYM[3] != G.PSUSYM[3, 4]:
            return l3030
        if G.IBRF != 0:
            G.NXC -= 1
        return l540

    def l540():
        if ibuf[1] == G.OPSYM[1, 196]:
            return l100
        if G.NUSYM != 0:
            for i in range(1, G.NUSYM + 1):
                if G.USRSYM[i, 1] != ibuf[1]:
                    continue
                if G.USRSYM[i, 2] != ibuf[2]:
                    continue
                if G.USRSYM[i, 3] != ibuf[3]:
                    continue
                errmes(2)
                return l2010
        return l555

    def l555():
        extptr_box = new_extptr()
        gval(1, extptr_box)
        G.NUSYM += 1
        if G.NUSYM > G.USRMAX:
            return l3000
        G.USRSYM[G.NUSYM, 1] = ibuf[1]
        G.USRSYM[G.NUSYM, 2] = ibuf[2]
        G.USRSYM[G.NUSYM, 3] = ibuf[3]
        G.USRSYM[G.NUSYM, 5] = 0
        id_ = G.NUSYM
        if G.GVLFLG < 0:
            G.USRSYM[G.NUSYM, 4] = 0
            errmes(9)
            return l2010
        G.USRSYM[id_, 4] = G.IVAL
        if extptr_box.value != 0:
            G.USRSYM[id_, 5] = G.USRSYM[iand16(extptr_box.value, 4095), 5]
        return l110

    # ---- pseudo-ops that don't need the location counter incremented ----
    def l245():
        if G.GLNFLG != 1:
            return l110
        gline()
        return l245

    # ---- $LOC ----
    def l250():
        extptr_box = new_extptr()
        gval(0, extptr_box)
        if G.GVLFLG < 0:
            return l270
        return l260

    def l260():
        G.LOCNT = G.IVAL
        if G.LABFLG >= 0:
            return l110
        G.USRSYM[G.NUSYM, 4] = G.LOCNT
        return l110

    def l270():
        errmes(9)
        return l2010

    # ---- $EXT / $INTEGER / $REAL / $TRIPLE ----
    def l700():
        nonlocal id_ext
        id_ext = 1
        return l710

    def l702():
        nonlocal id_ext
        id_ext = 2
        return l710

    def l704():
        nonlocal id_ext
        id_ext = 3
        return l710

    def l706():
        nonlocal id_ext
        id_ext = 4
        return l710

    def l710():
        gsym()
        if G.ALFLG < 0:
            return l720
        return l730

    def l720():
        if G.IBRF == 3 and G.GLNFLG == 1:
            return l725
        errmes(28)
        return l2010

    def l725():
        gline()
        return l710

    def l730():
        """Note: a duplicate-symbol match jumps straight into the ID==4
        check at l750 (see source lines 751-752, 'CALL ERRMES(2); GOTO
        750') -- it does NOT go through l741's NUSYM increment, so on a
        conflicting $TRIPLE declaration specifically, USRSYM(NUSYM,5) for
        whatever NUSYM currently is (a stale, unrelated entry) gets
        overwritten. Preserved as-is -- an authentic original quirk."""
        if G.NUSYM == 0:
            return l741
        for i in range(1, G.NUSYM + 1):
            if G.USRSYM[i, 1] != G.SYM[1]:
                continue
            if G.USRSYM[i, 2] != G.SYM[2]:
                continue
            if G.USRSYM[i, 3] != G.SYM[3]:
                continue
            errmes(2)
            return l750
        return l741

    def l741():
        G.NUSYM += 1
        if G.NUSYM > G.USRMAX:
            return l3000
        G.USRSYM[G.NUSYM, 1] = G.SYM[1]
        G.USRSYM[G.NUSYM, 2] = G.SYM[2]
        G.USRSYM[G.NUSYM, 3] = G.SYM[3]
        G.USRSYM[G.NUSYM, 4] = 0
        if id_ext != 1:
            return l742
        G.EXTNUM += 1
        G.USRSYM[G.NUSYM, 5] = ior16(ilsh16(G.EXTNUM, 8), 1)
        return l742

    def l742():
        if id_ext != 2:
            return l744
        G.USRSYM[G.NUSYM, 5] = ior16(ilsh16(1, 3), 6)
        return l744

    def l744():
        if id_ext != 3:
            return l750
        G.USRSYM[G.NUSYM, 5] = ior16(ilsh16(2, 3), 6)
        return l750

    def l750():
        if id_ext != 4:
            return l755
        G.USRSYM[G.NUSYM, 5] = ior16(ilsh16(4, 3), 6)
        return l755

    def l755():
        if G.IBRF - 3 != 0:
            return l760
        return l780

    def l760():
        if G.IBRF - 15 != 0:
            return l770
        return l710

    def l770():
        errmes(27)
        return l710

    def l780():
        if G.ERRCNT > 0:
            return l2010
        return l110

    # ---- $END ----
    def l1000():
        sndmes()
        tlun = G.TLUN - 7
        infile(6, G.TFILE, tlun)
        return None

    # ---- $INSERT ----
    def l1100():
        nonlocal slunsv, linsv
        if G.INSFLG == 1:
            return l1190
        slunsv = G.SLUN
        linsv = G.LINNUM
        return l1110

    def l1110():
        if G.LIN[G.NXC] != G.CHARS[1]:
            return l1115
        G.NXC += 1
        return l1110

    def l1115():
        exflds(G.CHARS[1], G.CHARS[1], 1, 0)
        length(G.FIELD)
        for i in range(1, 32):
            insfil[i] = G.FIELD[i]
        G.SLUN = 5
        infile(1, insfil, G.SLUN)
        G.SLUN += 7
        G.LINNUM = 0
        G.INSFLG = 1
        pnum(linsv, G.IOPTR, 1)
        wlin()
        return l110

    def l1190():
        errmes(41)
        return l2010

    # ---- $IF ----
    def l1200():
        extptr_box = new_extptr()
        gval(0, extptr_box)
        if G.GVLFLG < 0:
            return l1220
        return l1210

    def l1210():
        nonlocal ifflg
        if G.IVAL == 0:
            ifflg = 1
        return l110

    def l1220():
        errmes(9)
        return l2010

    # ---- $IF/$ENDIF skip-scan (reached while IFFLG is set) ----
    def l1250():
        gsym()
        if G.IBRF != 9:
            return l110
        gsym()
        if G.SYM[1] != G.PSUSYM[1, 11]:
            return l110
        if G.SYM[2] != G.PSUSYM[2, 11]:
            return l110
        if G.SYM[3] != G.PSUSYM[3, 11]:
            return l110
        return l1260

    def l1260():
        nonlocal ifflg
        ifflg = 0
        return l110

    # ---- $BOX ----
    def l1300():
        nonlocal boxflg
        boxflg = 1
        return l110

    # ---- $ENDBOX without a matching $BOX ----
    def l1310():
        errmes(41)
        return l110

    # ---- $BOX/$ENDBOX skip-scan (reached while BOXFLG is set) ----
    def l1320():
        gsym()
        if G.IBRF != 9:
            return l110
        gsym()
        if G.SYM[1] != G.PSUSYM[1, 13]:
            return l110
        if G.SYM[2] != G.PSUSYM[2, 13]:
            return l110
        if G.SYM[3] != G.PSUSYM[3, 13]:
            return l110
        nonlocal boxflg
        boxflg = 0
        return l110

    # ---- &LIB ----
    def l1400():
        fwrite(G.OLUN, "( 5X,1H6,6X,6H***LSB)", [])
        return l110

    # ---- &ENDLIB (treated as $END) ----
    def l1450():
        return l1000

    # ---- $TITLE ----
    def l1500():
        gsym()
        if G.ALFLG < 0:
            return l1520
        G.TI[1] = G.SYM[1]
        G.TI[2] = G.SYM[2]
        G.TI[3] = G.SYM[3]
        fwrite(G.OLUN, "( 5X,1H3,6X,8H***TITLE/ 3A2)", [G.SYM[1], G.SYM[2], G.SYM[3]])
        return l110

    def l1520():
        errmes(20)
        return l2010

    # ---- $RADIX ----
    def l1600():
        nonlocal id_ext
        id_ext = G.NRADIX
        G.NRADIX = 10
        extptr_box = new_extptr()
        gval(0, extptr_box)
        if G.GVLFLG < 0:
            return l1610
        G.NRADIX = id_ext
        if G.IVAL != 8 and G.IVAL != 10 and G.IVAL != 16:
            return l1610
        G.NRADIX = G.IVAL
        return l110

    def l1610():
        errmes(9)
        return l2010

    # ---- $COMMON ----
    def l1700():
        nonlocal elmcnt, oldtyp
        elmcnt = 0
        oldtyp = 0
        if G.IBRF == 0:
            return l1710
        if G.IBRF != 7:
            return l1990
        exflds(G.CHARS[7], G.CHARS[7], 1, 1)
        if G.FIELD[1] != G.CHARS[3]:
            return l1720
        return l1710

    def l1710():
        for i in range(1, 4):
            G.SYM[i] = _BLKCMN[i - 1]
        return l1725

    def l1720():
        from .packs import packs

        packs(6, G.FIELD)
        if G.FIELD[1] != G.CHARS[8]:
            return l1725
        for i in range(1, 4):
            if G.SYM[i] != _BLKCMN[i - 1] and G.SYM[i] != _LOCCMN[i - 1]:
                return l1990
        return l1725

    def l1725():
        nonlocal comptr
        fusym()
        if G.TABPTR == 0:
            return l1730
        if G.USRSYM[G.TABPTR, 4] != 1:
            return l1990
        comptr = G.TABPTR
        for i in range(1, 4):
            if G.SYM[i] != _LOCCMN[i - 1]:
                return l1728
        G.USRSYM[G.TABPTR, 4] = irsh16(G.USRSYM[G.TABPTR, 5], 8)
        return l1770

    def l1728():
        nonlocal comcnt
        comcnt += 1
        G.USRSYM[comptr, 4] = comcnt
        return l1770

    def l1730():
        nonlocal comptr, comcnt
        G.NUSYM += 1
        if G.NUSYM > G.USRMAX:
            return l3000
        for i in range(1, 4):
            G.USRSYM[G.NUSYM, i] = G.SYM[i]
        G.USRSYM[G.NUSYM, 5] = 3
        comptr = G.NUSYM
        comcnt += 1
        G.USRSYM[G.NUSYM, 4] = comcnt
        return l1770

    def l1770():
        nonlocal indx
        indx = comptr
        gsym()
        if G.ALFLG < 0:
            return l3030
        return l1775

    def l1775():
        nonlocal indx1
        fusym()
        indx1 = G.TABPTR
        if G.TABPTR != 0:
            return l1800
        G.NUSYM += 1
        if G.NUSYM > G.USRMAX:
            return l3000
        for i in range(1, 4):
            G.USRSYM[G.NUSYM, i] = G.SYM[i]
        indx1 = G.NUSYM
        return l1800

    def l1800():
        G.IVAL = 1
        if G.IBRF != 11:
            return l1830
        G.NXC -= 1
        exflds(G.CHARS[11], G.CHARS[12], 0, 1)
        return l1805_scan()

    def l1805_scan():
        nonlocal id_ext
        id_ext = 0
        j = 1
        for i in range(1, 81):
            j = i
            if G.FIELD[i] == G.CHARS[3]:
                break
            if G.FIELD[i] == G.CHARS[15]:
                id_ext += 1
        k = (j + 2) + (2 * id_ext)
        G.FIELD[k] = G.CHARS[3]
        G.FIELD[k - 1] = G.CHARS[12]
        j -= 1
        k -= 2
        return _l1815(j, k)

    def _l1815(j: int, k: int):
        while True:
            if G.FIELD[j] == G.CHARS[15]:
                return _l1820(j, k)
            G.FIELD[k] = G.FIELD[j]
            j -= 1
            k -= 1
            if j == 0:
                break
        if k != 1:
            return l3030
        G.FIELD[1] = G.CHARS[11]
        return l1825

    def _l1820(j: int, k: int):
        G.FIELD[k] = G.CHARS[11]
        G.FIELD[k - 1] = G.CHARS[6]
        G.FIELD[k - 2] = G.CHARS[12]
        k -= 3
        j -= 1
        return _l1815(j, k)

    def l1825():
        G.FLDFLG = 1
        extptr_box = new_extptr()
        gval(0, extptr_box)
        G.FLDFLG = 0
        return l1830

    def l1830():
        nonlocal itype
        if G.IBRF == 7:
            return l1840
        itype = iand16(irsh16(G.USRSYM[indx1, 5], 3), 7)
        if itype == 1 or itype == 2 or itype == 4:
            return l1860
        itype = 1
        return l1860

    def l1840():
        gsym()
        if G.SYM[1] == _SI:
            return l1850
        if G.SYM[1] == _SR:
            return l1855
        if G.SYM[1] == _ST:
            return l1857
        errmes(45)
        return l1880

    def l1850():
        nonlocal itype
        itype = 1
        return l1860

    def l1855():
        nonlocal itype
        itype = 2
        return l1860

    def l1857():
        nonlocal itype
        itype = 4
        return l1860

    def l1860():
        nonlocal elmcnt, oldtyp
        G.USRSYM[indx, 5] = ior16(iand16(G.USRSYM[indx, 5], 7), ilsh16(indx1, 3))
        if oldtyp != itype:
            elmcnt += 1
            oldtyp = itype
        return l1870

    def l1870():
        nonlocal indx
        G.USRSYM[indx1, 4] = G.IVAL
        G.USRSYM[indx1, 5] = itype
        indx = indx1
        return l1880

    def l1880():
        if G.IBRF != 15:
            return l1910
        return l1890

    def l1890():
        gsym()
        if G.ALFLG < 0:
            return l1895
        return l1775

    def l1895():
        if G.IBRF == 3 and G.GLNFLG == 1:
            return l1900
        errmes(30)
        return l2010

    def l1900():
        gline()
        return l1890

    def l1910():
        nonlocal indx, itype, oldtyp, elmcnt
        id_ = iand16(G.USRSYM[comptr, 5], 7)
        itas(elmcnt, array1, 8)
        fwrite(
            G.OLUN,
            "( 4X,2H10,1X,6A1,1X,3A2,I4,2X,7H***DBDB)",
            [array1[j] for j in range(1, 7)]
            + [G.USRSYM[comptr, i] for i in range(1, 4)]
            + [id_],
        )
        i_ = G.USRSYM[comptr, 4]
        j_ = irsh16(G.USRSYM[comptr, 5], 3)
        G.USRSYM[comptr, 4] = 0
        G.USRSYM[comptr, 5] = ior16(4, ilsh16(i_, 8))
        indx = 0
        itype = 1
        oldtyp = 0
        elmcnt = 0
        return _l1930(i_, j_)

    def _l1930(i_: int, j_: int):
        nonlocal indx, elmcnt, itype, oldtyp
        while True:
            indx1_ = iand16(G.USRSYM[j_, 5], 7)
            k_ = j_
            j_ = irsh16(G.USRSYM[k_, 5], 3)
            if indx1_ == oldtyp:
                elmcnt += G.USRSYM[k_, 4]
            else:
                if itype == 0:
                    itas(elmcnt, array1, 8)
                    fwrite(
                        G.OLUN, "( I6,4X,6A1)",
                        [oldtyp] + [array1[l] for l in range(1, 7)],
                    )
                itype = 0
                elmcnt = G.USRSYM[k_, 4]
                oldtyp = indx1_
            id_ = G.USRSYM[k_, 4]
            G.USRSYM[k_, 4] = indx
            G.USRSYM[k_, 5] = ior16(ior16(ilsh16(i_, 8), ilsh16(indx1_, 3)), 3)
            indx += id_
            if j_ == 0:
                break
        itas(elmcnt, array1, 8)
        fwrite(
            G.OLUN, "( I6,4X,6A1)",
            [oldtyp] + [array1[l] for l in range(1, 7)],
        )
        return l2010

    def l1990():
        errmes(22)
        return l2010

    # ---- shared error landings ----
    def l2000():
        sndmes()
        return l100

    def l2010():
        sndmes()
        return l245

    def l3000():
        errmes(41)
        return l2010

    def l3010():
        errmes(40)
        return l2010

    def l3030():
        errmes(45)
        return l2010

    def l3040():
        errmes(30)
        return l2010

    # ---- $COMIO ----
    def l4000():
        if G.IBRF == 8:
            return l4020
        if G.IBRF != 0:
            return l3040
        return l4010

    def l4010():
        gsym()
        if G.IBRF != 3 and G.ALFLG != -1 and G.GLNFLG != 1:
            return l4020
        gline()
        return l4010

    def l4020():
        if G.IBRF != 8:
            return l4040
        exflds(G.CHARS[1], G.CHARS[1], 1, 1)
        if G.FIELD[6] == G.CHARS[3]:
            return l4030
        return l4060

    def l4030():
        from .packs import packs

        for i in range(1, 6):
            j = 7 - i
            G.FIELD[j] = G.FIELD[j - 1]
        G.FIELD[1] = G.CHARS[8]
        packs(6, G.FIELD)
        return l4040

    def l4040():
        gnum()
        fusym()
        if G.TABPTR != 0:
            return l4060
        G.NUSYM += 1
        if G.NUSYM > G.USRMAX:
            return l3000
        for i in range(1, 4):
            G.USRSYM[G.NUSYM, i] = G.SYM[i]
        G.USRSYM[G.NUSYM, 4] = 1
        G.USRSYM[G.NUSYM, 5] = G.IVAL
        if G.IBRF == 15:
            return l4010
        if G.IBRF != 3:
            return l4060
        return l2010

    def l4060():
        errmes(42)
        return l2010

    # ---- $PARAM ----
    def l5000():
        nonlocal comptr, oldtyp
        exflds(G.CHARS[15], G.CHARS[15], 1, 1)
        G.FLDFLG = 1
        extptr_box = new_extptr()
        gval(0, extptr_box)
        if G.IVAL == 0:
            return l5300
        G.FLDFLG = 0
        comptr = -1
        itas(G.IVAL, array1, 8)
        fwrite(G.OLUN, "( 4X,2H12,1X,6A1,6X,5H***PB)", [array1[i] for i in range(1, 7)])
        for i in range(1, 4):
            G.SYM[i] = _LOCCMN[i - 1]
        fusym()
        oldtyp = 0
        if G.TABPTR != 0:
            return l5020
        oldtyp = 1
        G.NUSYM += 1
        if G.NUSYM > G.USRMAX:
            return l3000
        for i in range(1, 4):
            G.USRSYM[G.NUSYM, i] = _LOCCMN[i - 1]
        nonlocal comcnt
        comcnt += 1
        G.USRSYM[G.NUSYM, 4] = 1
        G.USRSYM[G.NUSYM, 5] = ior16(ilsh16(comcnt, 8), 7)
        G.TABPTR = G.NUSYM
        return l5020

    def l5020():
        nonlocal indx1
        indx1 = irsh16(G.USRSYM[G.TABPTR, 5], 8)
        return l5030

    def l5030():
        gsym()
        if G.ALFLG == 0:
            return l5050
        if G.IBRF != 3 and G.GLNFLG != 1:
            return l3040
        gline()
        return l5030

    def l5050():
        nonlocal comptr
        comptr += 1
        fusym()
        if G.TABPTR == 0:
            return l5070
        if oldtyp == 1:
            return l5060
        if comptr != G.USRSYM[G.TABPTR, 4]:
            return l5300
        if irsh16(G.USRSYM[G.TABPTR, 5], 8) != indx1:
            return l5300
        return _l5090(G.USRSYM[G.TABPTR, 4], ior16(G.USRSYM[G.TABPTR, 5], 7))

    def l5060():
        return _l5090(comptr, ior16(G.USRSYM[G.TABPTR, 5], 7))

    def l5070():
        G.NUSYM += 1
        if G.NUSYM > G.USRMAX:
            return l3000
        G.TABPTR = G.NUSYM
        for i in range(1, 4):
            G.USRSYM[G.NUSYM, i] = G.SYM[i]
        return _l5090(comptr, 7)

    def _l5090(v1: int, v2: int):
        nonlocal val1, val2
        val1, val2 = v1, v2
        G.FIELD[1] = 0
        if G.IBRF != 11:
            return l5100
        G.NXC -= 1
        exflds(G.CHARS[11], G.CHARS[12], 1, 1)
        return l5100

    def l5100():
        nonlocal itype
        G.IVAL = 0
        itype = 0
        if G.IBRF != 7:
            return l5130
        gsym()
        if G.SYM[1] == _SI:
            itype = 1
        if G.SYM[1] == _SR:
            itype = 2
        if G.SYM[1] == _SIP:
            G.IVAL = 1
        if G.SYM[1] == _SOP:
            G.IVAL = 2
        return l5110

    def l5110():
        if G.IBRF != 7:
            return l5130
        gsym()
        if G.IVAL != 0:
            return l5120
        if G.SYM[1] == _SIP:
            G.IVAL = 1
        if G.SYM[1] == _SOP:
            G.IVAL = 2
        if G.IVAL == 1 or G.IVAL == 2:
            return l5110
        errmes(19)
        return l5110

    def l5120():
        if G.SYM[1] == _SIP and G.IVAL == 2:
            G.IVAL = 3
        if G.SYM[1] == _SOP and G.IVAL == 1:
            G.IVAL = 3
        if G.IVAL != 3:
            errmes(19)
        return l5130

    def l5130():
        nonlocal itype, val2
        if G.IVAL == 0:
            G.IVAL = 3
        if iand16(irsh16(val2, 3), 7) != 0:
            return l5140
        if itype == 0:
            itype = 1
        val2 = ior16(iand16(val2, 7), ilsh16(itype, 3))
        G.USRSYM[G.TABPTR, 4] = val1
        G.USRSYM[G.TABPTR, 5] = val2
        return l5150

    def l5140():
        nonlocal itype
        if itype != iand16(irsh16(val2, 3), 7) and itype != 0:
            errmes(19)
        itype = iand16(irsh16(val2, 3), 7)
        return l5150

    def l5150():
        nonlocal i_count
        i_count = 0
        if G.FIELD[1] == 0:
            return l5210
        for j in range(1, 81):
            if G.FIELD[j] == G.CHARS[15]:
                i_count += 1
            if G.FIELD[j] == G.CHARS[3]:
                break
        i_count += 1
        return l5210

    def l5210():
        itas(i_count, array1, 8)
        fwrite(
            G.OLUN, "( 2I6,6A1)",
            [itype, G.IVAL] + [array1[x] for x in range(1, 7)],
        )
        nonlocal ibrfsv, nxcsv
        ibrfsv = G.IBRF
        nxcsv = G.NXC
        if i_count == 0:
            return l5270
        G.FLDFLG = 1
        return _l5220(1)

    def _l5220(k: int):
        while True:
            k += 1
            if G.FIELD[k] != G.CHARS[1]:
                break
        indx_local = 0
        if G.FIELD[k] == G.CHARS[18]:
            indx_local = 1
            G.FIELD[k] = G.CHARS[1]
        return _l5230(k, indx_local)

    def _l5230(k: int, indx_local: int):
        for i in range(k, 81):
            l_ = i
            id_local = 0
            if G.FIELD[i] != G.CHARS[3]:
                if G.FIELD[i] != G.CHARS[15]:
                    continue
                G.FIELD[i] = G.CHARS[3]
            else:
                id_local = 1
            extptr_box = new_extptr()
            gval(0, extptr_box)
            itas(G.IVAL, array1, 8)
            fwrite(
                G.OLUN, "( I6,1X,6A1)",
                [indx_local] + [array1[x] for x in range(1, 7)],
            )
            if id_local == 1:
                return l5270
            for m in range(k, l_ + 1):
                G.FIELD[m] = G.CHARS[1]
            return _l5220(l_)
        return l5270

    def l5270():
        G.NXC = nxcsv
        G.IBRF = ibrfsv
        G.FLDFLG = 0
        if G.IBRF == 15:
            return l5030
        if G.IBRF != 3:
            return l3040
        return l2010

    def l5300():
        errmes(43)
        return l2010

    # ---- $CALL ----
    def l6000():
        gsym()
        fusym()
        if G.TABPTR == 0:
            return l6500
        if iand16(G.USRSYM[G.TABPTR, 5], 7) != 1:
            return l6500
        for i in range(1, 4):
            ibuf[i] = G.SYM[i]
        nonlocal indx1
        indx1 = 0
        if G.IBRF != 11:
            return l6300
        fwrite(
            G.TLUN,
            "(1X, 'LDMA; DB=#',3A2,'-1     \"BEGIN EXPANSION OF $CALL')",
            [G.SYM[1], G.SYM[2], G.SYM[3]],
        )
        G.LOCNT += 1
        return l6100

    def l6100():
        from .packs import packs

        nonlocal indx1
        exflds(G.CHARS[15], G.CHARS[15], 1, 1)
        indx1 += 1
        if G.IBRF == 3:
            return l6200
        packs(20, G.FIELD)
        fwrite(
            G.TLUN,
            "(1X, 14HDPX(3)<DB; DB=,1X,10A2/1X, 16HINCMA; MI<DPX(3))",
            [G.SYM[i] for i in range(1, 11)],
        )
        G.LOCNT += 2
        return l6100

    def l6200():
        from .packs import packs

        j = 1
        for i in range(1, 81):
            j = i
            if G.FIELD[i] == G.CHARS[3]:
                break
        G.FIELD[j] = G.CHARS[1]
        G.FIELD[j - 1] = G.CHARS[1]
        packs(20, G.FIELD)
        fwrite(
            G.TLUN,
            "(1X, 14HDPX(3)<DB; DB=,1X,10A2/1X, 16HINCMA; MI<DPX(3))",
            [G.SYM[i] for i in range(1, 11)],
        )
        G.LOCNT += 2
        fwrite(G.TLUN, "(1X, 14HLDSPI 0; DB= # ,3A2)", [ibuf[1], ibuf[2], ibuf[3]])
        G.LOCNT += 1
        return l6300

    def l6300():
        fwrite(
            G.TLUN,
            "(1X, 12HLDSPI 1; DB=,I6/1X, 4HJSR ,3A2,12X,23H\"END EXPANSION OF $CALL)",
            [indx1, ibuf[1], ibuf[2], ibuf[3]],
        )
        G.LOCNT += 2
        return l2010

    def l6500():
        errmes(44)
        return l2010

    # ---- $TASK ----
    def l7000():
        nonlocal task_j, task_k, task_l, task_m, task_id
        task_j = 0
        task_k = 0
        task_l = 0
        task_m = 100
        if G.IBRF != 0:
            return l7090
        gnum()
        task_id = G.IVAL
        return l7020

    def l7020():
        if G.IBRF == 7:
            return l7040
        if G.IBRF == 3:
            return l7060
        nonlocal task_m
        gnum()
        task_m = G.IVAL
        if G.IVAL < 0 or G.IVAL > 255:
            return l7090
        return l7020

    def l7040():
        nonlocal task_j, task_k, task_l
        gsym()
        if G.SYM[1] != _SM and G.SYM[1] != _SI and G.SYM[1] != _SS:
            return l7090
        if G.SYM[1] == _SM:
            task_j = 1
        if G.SYM[1] == _SI:
            task_k = 1
        if G.SYM[1] == _SS:
            task_l = 1
        return l7020

    def l7060():
        itas(task_id, array1, 8)
        itas(task_m, array2, 8)
        fwrite(
            G.OLUN,
            "( 4X,2H15,6X,7H***TASK/3A1,1X,I1,1X,3A1,2(1X,I1))",
            [array1[i] for i in range(4, 7)]
            + [task_j]
            + [array2[i] for i in range(4, 7)]
            + [task_k, task_l],
        )
        return l2010

    def l7090():
        errmes(34)
        return l2010

    # ---- $ISR ----
    def l8000():
        if G.IBRF != 0:
            return l7090
        gnum()
        if G.IVAL < 1 or G.IVAL > 15:
            return l7090
        itas(G.IVAL, array1, 8)
        fwrite(G.OLUN, "( 4X,2H16,1X,6A1,6X,6H***ISR)", [array1[i] for i in range(1, 7)])
        return l2010

    # ---- pseudo-op index (PSUSYM 1..31) -> handler block ----
    _pseudo_op_table = {
        1: l1500, 2: l245, 3: l100, 4: l540, 5: l250, 6: l100,
        7: l1000, 8: l700, 9: l1100, 10: l1200, 11: l1260,
        12: l1300, 13: l1310, 14: l1400, 15: l1450, 16: l1600,
        17: l245, 18: l245, 19: l245, 20: l702, 21: l704,
        22: l1700, 23: l245, 24: l4000, 25: l245, 26: l5000,
        27: l6000, 28: l245, 29: l706, 30: l7000, 31: l8000,
    }

    blk = l100
    while blk is not None:
        blk = blk()
