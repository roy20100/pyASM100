"""GVAL = APAL EXPRESSION EVALUATOR (ASM100.FTN line 6691).

Evaluates a parenthesis-free operator-precedence expression from LIN (or
FIELD, if FLDFLG==1) and returns its 16-bit two's-complement value in
COMMON IVAL. Converts to postfix using two local stacks (STK1 collects
items while precedence is increasing, STK2 receives them for immediate
evaluation once precedence stops increasing), driven by the operator table
EXPRTB from tables.py.

Ported as a full "block trampoline" (one function per FORTRAN label): this
is the single most GOTO-dense subroutine in ASM100.FTN, with several
distinct loops (100/900, 1000/1120, 150/170, the 2250 error-recovery scan)
sharing labels reached from many different places, so mapping each label
to its own block is far safer than trying to restructure it by hand.

Returns via COMMON: IVAL (the value), GVLFLG (0 ok, -1 failed), IBRF (the
break character), NXC (advanced past the expression). EXTPTR (external
symbol table pointer, or a flag bit pattern -- see the source comment
above SUBROUTINE GVAL) is a true by-reference output parameter, passed as
a Box.

Known fragility inherited from the source, not a translation bug: the
error-recovery scan at label 2250 resumes from the local L1/NXC as they
stood after the failing token was read, not from a fresh read. When a
symbol-lookup error (undefined symbol, external not allowed, ...) is the
very last thing on an otherwise-empty line, GSYM has already consumed the
line's only CR advancing NXC past it, so the recovery scan has nothing
left in LIN to find and would run past the array end. In real use LIN is
a reused COMMON buffer that always has *something* from a prior line
sitting past the current one, so this apparently never bit the original;
an isolated single-line test can hit it (confirmed harmless once a real
delimiter follows the error -- see the module's tests).
"""

from __future__ import annotations

from .arith import icmp16, ineg16, ipfix, isub16, negchk
from .bitops import iadd16, iand16, ilsh16, inot16, ior16
from .box import Box
from .common import G
from .errmes import errmes
from .farray import FArray
from .float2 import float2
from .fusym import fusym
from .gnum import gnum
from .gsym import gsym

# EXPRTB's ID column (1..12) selects the operator, matching the source's
# computed GOTO (1210,1220,1230,1240,1250,1120,1270,1280,1290,1300,1310,1320)
_OP_BLOCK_NAMES = (
    "add", "sub", "mul", "div", "neg", "not_",
    "and_", "or_", "eq", "gt", "lt", "lnot",
)


def gval(okext: int, extptr_box: Box) -> None:
    stk1 = FArray(20, 2)
    stk2 = FArray(10, 2)
    st1max, st2max = 20, 10

    l1 = 0
    lstprs = 0
    pres = 0
    flgdun = 0
    flgdlm = 0
    st1 = 0
    st2 = 0
    extflg = 0
    relflg = 0
    id_ = 0
    val2 = 0
    pres2 = 0
    nxcsv = 0
    ibrfsv = 0
    extptr = 0

    def cur_char(nxc: int) -> int:
        return G.FIELD[nxc] if G.FLDFLG == 1 else G.LIN[nxc]

    G.GVLFLG = 0
    G.IVAL = 0

    def l_init():
        nonlocal ibrfsv, nxcsv
        ibrfsv = G.IBRF
        G.IBRF = -1
        if G.FLDFLG == 0:
            return l150
        nxcsv = G.NXC
        G.NXC = 1
        return l150

    def l100():
        if flgdun == 1:
            return l750
        if G.IBRF == -1:
            G.NXC += 1
        else:
            G.NXC -= 1
        G.IBRF = -1
        return l150

    def l150():
        nonlocal l1
        l1 = cur_char(G.NXC)
        if l1 == G.CHARS[1]:
            return l170
        return l200

    def l170():
        G.NXC += 1
        return l150

    def l200():
        nonlocal extptr
        if l1 != G.CHARS[23]:
            return l225
        extptr = ilsh16(1, 15)
        G.NXC += 1
        return l150

    def l225():
        nonlocal lstprs, pres
        lstprs = pres
        pres = 15
        if G.CHARS[32] <= l1 <= G.CHARS[33]:
            return l300
        return l400

    def l300():
        gnum()
        return l900

    def l400():
        nonlocal relflg
        relflg = 0
        if G.CHARS[34] <= l1 <= G.CHARS[35]:
            return l700
        return l600

    def l600():
        nonlocal relflg
        if l1 == G.CHARS[18]:
            relflg = -1
        if l1 == G.CHARS[24]:
            relflg = -2
        if relflg == 0:
            return l720
        return l700

    def l700():
        if relflg == -1:
            G.NXC += 1
        gsym()
        if G.ALFLG < 0:
            return l2100
        return l701

    def l701():
        fusym()
        if relflg + 1 < 0:
            return l702
        if relflg + 1 == 0:
            return l704
        return l705

    def l702():
        if G.TABPTR <= 0:
            return l703
        return l705

    def l703():
        G.NUSYM += 1
        if G.NUSYM > G.USRMAX:
            return l716
        G.TABPTR = G.NUSYM
        G.USRSYM[G.NUSYM, 1] = G.SYM[1]
        G.USRSYM[G.NUSYM, 2] = G.SYM[2]
        G.USRSYM[G.NUSYM, 3] = G.SYM[3]
        G.USRSYM[G.NUSYM, 4] = 0
        G.EXTNUM += 1
        G.USRSYM[G.NUSYM, 5] = ior16(ilsh16(G.EXTNUM, 8), 1)
        return l705

    def l704():
        nonlocal extptr
        extptr = ilsh16(1, 13)
        return l705

    def l705():
        if G.TABPTR <= 0:
            return l715
        return l706

    def l706():
        nonlocal id_, extptr, extflg
        G.IVAL = G.USRSYM[G.TABPTR, 4]
        id_ = iand16(G.USRSYM[G.TABPTR, 5], 7)
        if id_ == 1 and extflg == 1:
            return l710
        if id_ == 3 or id_ == 4:
            extptr = ior16(ior16(ilsh16(1, 14), extptr), G.TABPTR)
        if id_ in (0, 2, 3, 4):
            return l900
        if okext == 0 or st1 == 1 or st2 == 1:
            return l710
        extptr = ior16(extptr, G.TABPTR)
        if G.IBRF == 14 or G.IBRF == 3:
            return l4000
        if G.IBRF != 4 and G.IBRF != 5:
            return l710
        extflg = 1
        return l900

    def l710():
        errmes(16)
        return l2200

    def l715():
        errmes(17)
        return l2200

    def l716():
        errmes(41)
        return l2200

    def l720():
        if l1 != G.CHARS[8]:
            return l740
        G.IVAL = G.LOCNT
        return l900

    def l740():
        nonlocal flgdlm, pres, flgdun
        if l1 != G.CHARS[3] and l1 != G.CHARS[15] and l1 != G.CHARS[14]:
            return l780
        flgdlm = 1
        if flgdun == 1:
            return l750
        pres = 0
        flgdun = 1
        return l840

    def l750():
        if not (st1 == 1 and stk1[1, 2] == 0 and st2 == 1 and stk2[1, 2] == 15):
            return l2100
        G.IVAL = stk2[1, 1]
        return l3000

    def l780():
        nonlocal pres
        for i in range(1, G.EXPRMX + 1):
            if l1 != G.EXPRTB[i, 1]:
                continue
            pres = G.EXPRTB[i, 2]
            G.IVAL = G.EXPRTB[i, 3]
            if l1 != G.CHARS[5] and l1 != G.CHARS[4]:
                return l840
            if lstprs == 15 or lstprs == 1:
                return l840
            if l1 == G.CHARS[5]:
                G.IVAL = 5
            if l1 == G.CHARS[4]:
                G.IVAL = 6
            pres = 9
            return l840
        return l2100

    def l840():
        if st1 == 0:
            return l900
        return l1000

    def l900():
        nonlocal st1
        if (pres == 15 or pres == 2) and lstprs == 15:
            return l2100
        if pres == 15 and lstprs == 1:
            return l2100
        st1 += 1
        if st1 > st1max:
            return l2000
        stk1[st1, 1] = G.IVAL
        stk1[st1, 2] = pres
        return l100

    def l1000():
        nonlocal val2, pres2, st1
        val2 = stk1[st1, 1]
        pres2 = stk1[st1, 2]
        if pres == 9 and pres2 == 9:
            return l900
        if pres == 15 and pres2 == 15:
            return l2100
        if pres > pres2 or pres == 2:
            return l900
        if pres2 != 2:
            return l1100
        st1 -= 1
        return l100

    def l1100():
        nonlocal st2, st1
        if pres2 != 15:
            return l1150
        st2 += 1
        if st2 > st2max:
            return l2000
        stk2[st2, 1] = stk1[st1, 1]
        stk2[st2, 2] = pres2
        st1 -= 1
        return l1120

    def l1120():
        if st1 == 0:
            return l900
        return l1000

    def l1150():
        nonlocal st2, st1
        if val2 not in (5, 6, 12):
            if st2 < 2 or stk2[st2, 2] != 15 or stk2[st2 - 1, 2] != 15:
                return l2100
            st2 -= 1
        else:
            if st2 < 1 or stk2[st2, 2] != 15:
                return l2100
        st1 -= 1
        return _OP_TABLE[val2 - 1]()

    def l1210():
        stk2[st2, 1] = iadd16(stk2[st2, 1], stk2[st2 + 1, 1])
        return l1120

    def l1220():
        stk2[st2, 1] = isub16(stk2[st2, 1], stk2[st2 + 1, 1])
        return l1120

    def l1230():
        stk2[st2, 1] = ipfix(float2(stk2[st2, 1]) * float2(stk2[st2 + 1, 1]))
        return l1120

    def l1240():
        if icmp16(stk2[st2 + 1, 1], 0) == 0:
            return l1245
        stk2[st2, 1] = ipfix(float2(stk2[st2, 1]) / float2(stk2[st2 + 1, 1]))
        return l1120

    def l1245():
        errmes(57)
        stk2[st2, 1] = ipfix(-1)
        return l1120

    def l1250():
        stk2[st2, 1] = ineg16(stk2[st2, 1])
        return l1120

    def l1120_noop():
        # VAL2 == 6 dispatches straight to l1120 in the source's computed
        # GOTO table (index 6) -- there is no dedicated block for it.
        return l1120

    def l1270():
        stk2[st2, 1] = iand16(stk2[st2, 1], stk2[st2 + 1, 1])
        return l1120

    def l1280():
        stk2[st2, 1] = ior16(stk2[st2, 1], stk2[st2 + 1, 1])
        return l1120

    def l1290():
        stk2[st2, 1] = 0 if icmp16(stk2[st2, 1], stk2[st2 + 1, 1]) == 0 else 1
        return l1120

    def l1300():
        stk2[st2, 1] = 1 if negchk(isub16(stk2[st2 + 1, 1], stk2[st2, 1])) == 1 else 0
        return l1120

    def l1310():
        stk2[st2, 1] = 1 if negchk(isub16(stk2[st2, 1], stk2[st2 + 1, 1])) == 1 else 0
        return l1120

    def l1320():
        stk2[st2, 1] = inot16(stk2[st2, 1])
        return l1120

    _OP_TABLE = (
        l1210, l1220, l1230, l1240, l1250, l1120_noop,
        l1270, l1280, l1290, l1300, l1310, l1320,
    )

    def l2000():
        errmes(46)
        return l2200

    def l2100():
        errmes(9)
        return l2200

    def l2200():
        G.IVAL = 0
        G.GVLFLG = -1
        if flgdlm == 1 and l1 != 0:
            return l3000
        return l2250

    def l2250():
        nonlocal l1
        while True:
            if l1 == G.CHARS[14] or l1 == G.CHARS[15]:
                return l2260
            if l1 == G.CHARS[3]:
                return l3000
            G.NXC += 1
            l1 = cur_char(G.NXC)

    def l2260():
        G.NXC += 1
        return l3000

    def l3000():
        for i in range(1, G.BRKMX + 1):
            if G.CHARS[i] != l1:
                continue
            G.IBRF = i
            if i != 3:
                G.NXC += 1
            return l4000
        G.IBRF = 0
        G.NXC += 1
        return l4000

    def l4000():
        if G.FLDFLG == 1:
            G.NXC = nxcsv
            G.IBRF = ibrfsv
        extptr_box.value = extptr
        return None

    blk = l_init
    while blk is not None:
        blk = blk()
