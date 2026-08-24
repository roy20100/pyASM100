"""GFIELD = GET AN OP-CODE ARGUEMENT FIELD (ASM100.FTN line 5530).

Processes the argument field for whichever op-code group PASS1/PASS2
identified (selected by IFLD, 1..16, matching the source's computed
GOTO): S-PAD groups with 1 or 2 arguments, branch displacement, program-
source address (absolute/relative, with relocation-triplet bookkeeping),
floating adder/multiplier argument pairs, DB=/DPX/DPY/MI register-field
arguments (which share a lot of index-register conflict-checking logic
with GARG's DPY/DPX helper, but operate on different CODE/CODMSK bit
fields so aren't merged with it), and a few IFLD values that are no-ops.

Returns via IRET (a Box, matching the source's by-reference output param):
1 = normal (end of field), 2 = an assembly error occurred (caller should
recover), matching the source comment's "1 2000 END OF FIELD / 2 3000
ERROR RECOVERY / 3 320 END OF LINE" -- IRET is only ever actually set to 1
(initially) or 2 (at label 3000) anywhere in the body; the "3" case in the
comment is aspirational/unused, preserved as-is.

Ported as a full block trampoline, the same approach as GVAL/FPGET/RTOE
and for the same reason: this is the single largest and most state-
dependent subroutine in the source after GVAL, with dozens of arithmetic-
IF branches and several shared error-landing labels (1000, 1140, 1640,
2000, 3000) reached from many different argument groups.
"""

from __future__ import annotations

from .arith import fdiv
from .bitops import iand16, ior16, irsh16, ip16
from .box import Box
from .common import G
from .errmes import errmes
from .exflds import exflds
from .garg import garg
from .gval import gval


def gfield(ifld: int, iret: Box) -> None:
    iret.value = 1

    kchar = 0
    jx = 0
    ik = 0
    l1 = l2 = 0
    ivxl = 0
    ldbcf = 0
    ktem = 0

    def new_extptr() -> Box:
        return Box(0)

    # ---- dispatch (computed GOTO on IFLD) ----
    def l_entry():
        table = {
            1: l2000, 2: l100, 3: l300, 4: l400, 5: l600, 6: l610,
            7: l700, 8: l800, 9: l900, 10: l1100, 11: l2000, 12: l1300,
            13: l1500, 14: l2000, 15: l1700, 16: l2000,
        }
        return table[ifld]

    # ---- SPAD group, 2 arguments ----
    def l100():
        if G.IBRF != 18:
            return l105
        if iand16(G.CODMSK[2], G.MASKTB[6, 2]) != 0:
            return l240
        G.CODMSK[2] = ior16(G.CODMSK[2], G.MASKTB[6, 2])
        G.CODE[2] = ior16(G.CODE[2], 32)
        return l105

    def l105():
        nonlocal kchar
        if G.IBRF != 0 and G.IBRF != 18:
            G.NXC -= 1
        kchar = G.LIN[G.NXC]
        if kchar != G.CHARS[19]:
            return l110
        G.NXC += 1
        G.CODMSK[1] = ior16(G.ISBT, G.CODMSK[1])
        G.CODE[1] = ior16(G.ISBT, G.CODE[1])
        return l110

    def l110():
        if kchar != G.CHARS[1]:
            return l115
        G.NXC += 1
        return l105

    def l115():
        gval(0, new_extptr())
        if G.GVLFLG < 0:
            return l120
        return l130

    def l120():
        errmes(37)
        return l3000

    def l130():
        if G.IVAL < 0:
            return l140
        return l150

    def l140():
        errmes(4)
        return l3000

    def l150():
        if G.IVAL - 15 > 0:
            return l140
        return l160

    def l160():
        G.IVAL = G.IVAL * 64
        G.CODE[1] = ior16(G.IVAL, G.CODE[1])
        if G.IBRF - 15 != 0:
            return l170
        return l190

    def l170():
        if G.IBRF - 1 != 0:
            return l180
        return l190

    def l180():
        errmes(27)
        return l3000

    def l190():
        gval(0, new_extptr())
        if G.GVLFLG < 0:
            return l120
        return l200

    def l200():
        if G.IVAL < 0:
            return l140
        return l210

    def l210():
        if G.IVAL - 15 > 0:
            return l140
        return l220

    def l220():
        G.IVAL = G.IVAL * 4
        G.CODE[1] = ior16(G.IVAL, G.CODE[1])
        return l2000

    def l230():
        errmes(9)
        return l3000

    def l240():
        errmes(3)
        return l3000

    # ---- SPAD group, 1 argument ----
    def l300():
        if G.IBRF != 18:
            return l305
        if iand16(G.CODMSK[2], G.MASKTB[6, 2]) != 0:
            return l240
        G.CODMSK[2] = ior16(G.CODMSK[2], G.MASKTB[6, 2])
        G.CODE[2] = ior16(G.CODE[2], 32)
        return l305

    def l305():
        gval(0, new_extptr())
        if G.GVLFLG < 0:
            return l120
        return l310

    def l310():
        if G.IVAL < 0:
            return l140
        return l320

    def l320():
        if G.IVAL - 15 > 0:
            return l140
        return l330

    def l330():
        G.IVAL = G.IVAL * 4
        G.CODE[1] = ior16(G.IVAL, G.CODE[1])
        return l2000

    # ---- branch displacement ----
    def l400():
        if G.IBRF != 0:
            G.NXC -= 1
        gval(0, new_extptr())
        if G.GVLFLG < 0:
            return l500
        return l410

    def l410():
        G.IVAL = G.IVAL - G.LOCNT
        if G.IVAL + 16 < 0:
            return l420
        return l430

    def l420():
        errmes(5)
        return l3000

    def l430():
        if G.IVAL - 15 <= 0:
            return l440
        return l420

    def l440():
        nonlocal jx
        G.IVAL = G.IVAL + 16
        jx = iand16(G.CODMSK[2], 31)
        if jx != 0:
            return l450
        return l470

    def l450():
        nonlocal jx
        jx = iand16(G.CODE[2], 31)
        if jx - G.IVAL != 0:
            return l460
        return l2000

    def l460():
        errmes(6)
        return l3000

    def l470():
        G.CODMSK[2] = ior16(G.CODMSK[2], 31)
        G.CODE[2] = ior16(G.CODE[2], G.IVAL)
        return l2000

    def l500():
        if G.IBRF - 14 != 0:
            return l510
        return l520

    def l510():
        if G.IBRF - 3 != 0:
            return l230
        return l520

    def l520():
        nonlocal jx
        jx = iand16(G.CODMSK[2], 31)
        if jx != 0:
            return l2000
        return l530

    def l530():
        errmes(7)
        return l3000

    # ---- program-source address (absolute / relative) ----
    def l600():
        nonlocal jx
        jx = 0
        return l620

    def l610():
        nonlocal jx
        jx = 1
        return l620

    def l620():
        extptr_box = new_extptr()

        def after_gval():
            if G.GVLFLG < 0:
                return l670
            return _l630(extptr_box, jx)

        if G.IBRF != 0 and G.IBRF != 15:
            G.NXC -= 1
        gval(1, extptr_box)
        return after_gval()

    def _l630(extptr_box: Box, jx_local: int):
        if G.CODMSK[4] != 0:
            if G.CODMSK[4] != ior16(0, -8192):
                return l1140
            ik_local = iand16(fdiv(G.CODE[4], 8192), 7)
            if (
                iand16(7, G.CODMSK[3]) != 0
                and iand16(7, G.CODE[3]) != ik_local
            ):
                return l1640
            G.CODE[3] = ior16(ik_local, G.CODE[3])
            G.CODMSK[3] = ior16(7, G.CODMSK[3])
        return _l640(extptr_box, jx_local)

    def _l640(extptr_box: Box, jx_local: int):
        ik_local = G.IVAL
        if jx_local == 1 and extptr_box.value == 0:
            ik_local = ik_local - G.LOCNT
        G.CODE[4] = ik_local
        G.CODMSK[4] = ior16(0, -1)
        return _relocate(extptr_box, l2000)

    def _relocate(extptr_box: Box, done):
        """Shared relocation-triplet logic for both the P.S. address path
        (labels 650/660/665) and the DB=VALUE path (1160/1170/1175) --
        structurally identical in the source, parameterized here on the
        success continuation block."""
        extptr = extptr_box.value
        if iand16(irsh16(extptr, 15), 1) == 1:
            extptr = iand16(extptr, 8191)
            G.CODE[5] = 2
            if extptr != 0:
                G.CODE[5] = ior16(iand16(G.USRSYM[extptr, 5], ip16(-256)), 2)
            return done
        if iand16(irsh16(extptr, 13), 1) == 1:
            extptr = iand16(extptr, 8191)
            G.CODE[5] = ior16(iand16(G.USRSYM[extptr, 5], ip16(-256)), 4)
            return done
        if iand16(irsh16(extptr, 14), 1) == 1:
            extptr = iand16(extptr, 8191)
            G.CODE[5] = ior16(iand16(G.USRSYM[extptr, 5], ip16(-256)), 3)
            return done
        if extptr == 0:
            return done
        G.CODE[5] = ior16(iand16(G.USRSYM[extptr, 5], ip16(-256)), 5)
        return done

    def l670():
        errmes(9)
        return l3000

    # ---- FADD2 group, 2 arguments ----
    def l700():
        nonlocal l1v, l2v, ivxl
        l1v, l2v = 1, 6
        ivxl_box = Box(0)
        garg(l1v, l2v, ivxl_box)
        ivxl = ivxl_box.value
        if G.PTR < 0:
            return l3000
        if G.PTR == 0:
            return l1000
        return l710

    def l710():
        nonlocal ivxl
        ivxl = ivxl * 4096
        G.CODE[2] = ior16(G.CODE[2], ivxl)
        if G.IBRF - 15 != 0:
            return l720
        return l730

    def l720():
        if G.IBRF - 1 != 0:
            return l180
        return l730

    def l730():
        nonlocal l1v, l2v, ivxl
        l1v, l2v = 7, 14
        ivxl_box = Box(0)
        garg(l1v, l2v, ivxl_box)
        ivxl = ivxl_box.value
        if G.PTR < 0:
            return l3000
        if G.PTR == 0:
            return l740
        return l750

    def l740():
        errmes(10)
        return l3000

    def l750():
        nonlocal ivxl
        ivxl = ivxl * 512
        G.CODE[2] = ior16(G.CODE[2], ivxl)
        return l2000

    # ---- FADD1 group, 1 argument ----
    def l800():
        return l730

    # ---- FMUL group, 2 arguments ----
    def l900():
        nonlocal l1v, l2v, ivxl
        l1v, l2v = 15, 18
        ivxl_box = Box(0)
        garg(l1v, l2v, ivxl_box)
        ivxl = ivxl_box.value
        if G.PTR < 0:
            return l3000
        if G.PTR == 0:
            return l1000
        return l910

    def l910():
        nonlocal ivxl
        ivxl = ivxl * 1024
        G.CODE[4] = ior16(G.CODE[4], ivxl)
        if G.IBRF - 15 != 0:
            return l920
        return l930

    def l920():
        if G.IBRF - 1 != 0:
            return l180
        return l930

    def l930():
        nonlocal l1v, l2v, ivxl
        l1v, l2v = 19, 22
        ivxl_box = Box(0)
        garg(l1v, l2v, ivxl_box)
        ivxl = ivxl_box.value
        if G.PTR != 0:
            return l950
        return l940

    def l940():
        errmes(11)
        return l3000

    def l950():
        nonlocal ivxl
        ivxl = ivxl * 256
        G.CODE[4] = ior16(G.CODE[4], ivxl)
        return l2000

    # ---- "argument not recognized" shared landing (from 700/900) ----
    def l1000():
        if G.IBRF - 14 != 0:
            return l1010
        return l2000

    def l1010():
        if G.IBRF - 3 != 0:
            return l1020
        return l2000

    def l1020():
        errmes(12)
        return l3000

    # ---- DB= (also entered from DPX/DPY/MI's "not a register arg") ----
    def l1100():
        nonlocal ldbcf
        ldbcf = 0
        return l1110

    def l1110():
        nonlocal l1v, l2v, ktem, ivxl
        l1v, l2v = 23, 29
        ktem = G.NXC
        ivxl_box = Box(0)
        garg(l1v, l2v, ivxl_box)
        ivxl = ivxl_box.value
        if G.PTR == -1:
            return l3000
        if G.PTR == 0:
            ivxl = 2
        ivxl = ivxl * 512
        if (
            iand16(3584, G.CODMSK[3]) != 0
            and iand16(3584, G.CODE[3]) != ivxl
        ):
            return l1200
        G.CODE[3] = ior16(G.CODE[3], ivxl)
        G.CODMSK[3] = ior16(G.CODMSK[3], 3584)
        if G.PTR == 0:
            return l1120
        return _l1180

    def l1120():
        G.NXC = ktem
        extptr_box = new_extptr()
        gval(1, extptr_box)
        if G.GVLFLG < 0:
            return l230
        return _l1130(extptr_box)

    def _l1130(extptr_box: Box):
        if G.CODMSK[4] == 0:
            return _l1150(extptr_box)
        if (
            G.CODMSK[4] == ior16(0, -1)
            and iand16(G.CODE[3], 3584) == 1024
            and G.CODE[4] == G.IVAL
        ):
            return _l1150(extptr_box)
        if G.CODMSK[4] != ior16(0, -8192):
            return l1140
        ik_local = iand16(fdiv(G.CODE[4], 8192), 7)
        if iand16(7, G.CODMSK[3]) != 0 and iand16(7, G.CODE[3]) != ik_local:
            return l1640
        G.CODE[3] = ior16(ik_local, G.CODE[3])
        G.CODMSK[3] = ior16(7, G.CODMSK[3])
        return _l1150(extptr_box)

    def l1140():
        errmes(13)
        return l3000

    def _l1150(extptr_box: Box):
        G.CODE[4] = G.IVAL
        G.CODMSK[4] = ior16(0, -1)
        return _relocate(extptr_box, _l1180)

    def _l1180():
        if ldbcf != 0:
            return {1: l1420, 2: l1630, 3: l1730}[ldbcf]
        return l2000

    def l1200():
        errmes(36)
        return l3000

    # ---- DPX ----
    def l1300():
        if G.IBRF - 11 != 0:
            return l1390
        return l1310

    def l1310():
        G.NXC -= 1
        exflds(G.CHARS[11], G.CHARS[12], 0, 1)
        G.FLDFLG = 1
        extptr_box = new_extptr()
        gval(0, extptr_box)
        G.FLDFLG = 0
        if G.GVLFLG < 0:
            return l1330
        return l1340

    def l1330():
        errmes(14)
        return l3000

    def l1340():
        if G.IBRF - 13 != 0:
            return l1430
        return l1350

    def l1350():
        if G.IVAL + 4 < 0:
            return l1330
        return l1360

    def l1360():
        if G.IVAL - 3 > 0:
            return l1330
        return l1370

    def l1370():
        G.IVAL = G.IVAL + 4
        if iand16(7, G.CODMSK[3]) != 0 and iand16(7, G.CODE[3]) != G.IVAL:
            return l1640
        G.CODE[3] = ior16(G.CODE[3], G.IVAL)
        G.CODMSK[3] = ior16(G.CODMSK[3], 7)
        return _l_dpx_rest()

    def _l_dpx_rest():
        nonlocal l1v, l2v, ktem, ivxl
        l1v, l2v = 30, 32
        ktem = G.NXC
        ivxl_box = Box(0)
        garg(l1v, l2v, ivxl_box)
        ivxl = ivxl_box.value
        if G.PTR <= 0:
            return l1410
        return l1380

    def l1380():
        G.CODE[3] = ior16(G.CODE[3], G.IDPXX[ivxl])
        return l2000

    def l1390():
        if G.IBRF - 13 != 0:
            return l1430
        return l1400

    def l1400():
        G.IVAL = 0
        return l1370

    def l1410():
        nonlocal ldbcf
        ldbcf = 1
        G.NXC = ktem
        return l1110

    def l1420():
        nonlocal ivxl
        ivxl = 1
        return l1380

    def l1430():
        errmes(15)
        return l3000

    # ---- DPY ----
    def l1500():
        if G.IBRF - 11 != 0:
            return l1600
        return l1510

    def l1510():
        G.NXC -= 1
        exflds(G.CHARS[11], G.CHARS[12], 0, 1)
        G.FLDFLG = 1
        extptr_box = new_extptr()
        gval(0, extptr_box)
        G.FLDFLG = 0
        if G.GVLFLG < 0:
            return l1330
        return l1530

    def l1530():
        if G.IBRF - 13 != 0:
            return l1430
        return l1540

    def l1540():
        if G.IVAL + 4 < 0:
            return l1330
        return l1550

    def l1550():
        if G.IVAL - 3 > 0:
            return l1330
        return l1560

    def l1560():
        nonlocal ik
        G.IVAL = G.IVAL + 4
        ik = iand16(G.IVAL, 3)
        ik = ik * 8192
        if G.IVAL >= 4:
            ik = ik + G.ISBT
        if iand16(-8192, G.CODMSK[4]) == 0:
            return l1570
        if iand16(7, G.CODMSK[3]) != 0 and iand16(7, G.CODE[3]) != G.IVAL:
            return l1640
        G.CODE[3] = ior16(G.IVAL, G.CODE[3])
        G.CODMSK[3] = ior16(7, G.CODMSK[3])
        return l1580

    def l1570():
        G.CODE[4] = ior16(G.CODE[4], ik)
        G.CODMSK[4] = ior16(G.CODMSK[4], -8192)
        return l1580

    def l1580():
        nonlocal l1v, l2v, ktem, ivxl
        l1v, l2v = 30, 32
        ktem = G.NXC
        ivxl_box = Box(0)
        garg(l1v, l2v, ivxl_box)
        ivxl = ivxl_box.value
        if G.PTR <= 0:
            return l1620
        return l1590

    def l1590():
        nonlocal ivxl
        ivxl = ivxl * 4096
        G.CODE[3] = ior16(G.CODE[3], ivxl)
        return l2000

    def l1600():
        if G.IBRF - 13 != 0:
            return l1430
        return l1610

    def l1610():
        G.IVAL = 0
        return l1560

    def l1620():
        nonlocal ldbcf
        ldbcf = 2
        G.NXC = ktem
        return l1110

    def l1630():
        nonlocal ivxl
        ivxl = 1
        return l1590

    def l1640():
        errmes(39)
        return l3000

    # ---- MI ----
    def l1700():
        nonlocal l1v, l2v, ktem, ivxl
        l1v, l2v = 33, 35
        ktem = G.NXC
        ivxl_box = Box(0)
        garg(l1v, l2v, ivxl_box)
        ivxl = ivxl_box.value
        if G.PTR <= 0:
            return l1720
        return l1710

    def l1710():
        nonlocal ivxl
        ivxl = ivxl * 64
        G.CODE[4] = ior16(G.CODE[4], ivxl)
        return l2000

    def l1720():
        nonlocal ldbcf
        ldbcf = 3
        G.NXC = ktem
        return l1110

    def l1730():
        nonlocal ivxl
        ivxl = 3
        return l1710

    def l2000():
        return None

    def l3000():
        iret.value = 2
        return None

    l1v = l2v = 0
    blk = l_entry()
    while blk is not None:
        blk = blk()
