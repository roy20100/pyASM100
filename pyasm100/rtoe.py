"""RTOE = CONVERTS REAL NUMBER FORMAT (ASM100.FTN line 4915).

Reformats a free-form decimal literal read into FIELD (sign, digits,
optional '.', optional E-exponent, in any mix of upper/lower... actually
whatever TYPCHR accepts) into a normalized "d.dddddddddEsnn" form
overwriting FIELD: exactly one digit's worth of implied leading digit
position (IPOSIT starts at the buffer's 2nd slot, integer digits fill
forward, a leading-zero-after-decimal-point shifts the exponent down by
one instead of taking a buffer slot), then a computed decimal exponent
appended via ITAS.

Ported as a block trampoline for the same reason as GVAL/FPGET: many
short blank-skipping loops (labels 20, 30, 42, 70, 105, 110, 220) and
digit-scanning loops (140, 220/240/250) reached from multiple points.
"""

from __future__ import annotations

from .common import G
from .errmes import errmes
from .farray import FArray
from .itas import itas
from .typchr import typchr


def rtoe() -> None:
    buf = FArray(16)
    temp = FArray(6)

    zflag = 0
    sgn = 1
    iexp = 0
    res = 0
    posit = 0
    iposit = 0
    chr_ = 0

    for i in range(1, 17):
        buf[i] = G.CHARS[1]
    buf[1] = G.CHARS[4]

    def l20():
        nonlocal posit, chr_
        posit += 1
        chr_ = G.FIELD[posit]
        if chr_ == G.CHARS[1]:
            return l20
        id_ = typchr(chr_)
        if id_ == -1 or id_ == -2:
            return l30
        if chr_ != G.CHARS[4] and chr_ != G.CHARS[5]:
            return l30
        buf[1] = chr_
        posit += 1
        return l30

    def l30():
        nonlocal iposit, posit, chr_
        buf[2] = G.CHARS[32]
        iposit = 2
        chr_ = G.FIELD[posit]
        posit += 1
        if chr_ == G.CHARS[1]:
            return l30
        return l40

    def l40():
        if chr_ != G.CHARS[32]:
            return l50
        return l42

    def l42():
        nonlocal posit, chr_
        chr_ = G.FIELD[posit]
        if chr_ == G.CHARS[3]:
            return l205
        posit += 1
        if chr_ == G.CHARS[1]:
            return l42
        if typchr(chr_) != -2:
            return l100
        return l40

    def l50():
        nonlocal zflag, iposit, iexp
        if typchr(chr_) != -2:
            return l100
        zflag = 1
        buf[iposit] = chr_
        iposit += 1
        if iposit <= 11:
            return l70
        errmes(28)
        iexp = 1
        return l70

    def l70():
        nonlocal posit, chr_
        chr_ = G.FIELD[posit]
        if chr_ == G.CHARS[3]:
            return l205
        posit += 1
        if chr_ == G.CHARS[1]:
            return l70
        return l50

    def l100():
        nonlocal iexp
        if typchr(chr_) != -1:
            return l200
        if chr_ != G.CHARS[27]:
            return l300
        iexp = iposit - 11
        return l105

    def l105():
        nonlocal posit, chr_, sgn
        chr_ = G.FIELD[posit]
        posit += 1
        if chr_ == G.CHARS[1]:
            return l105
        sgn = 1
        if chr_ == G.CHARS[4]:
            return l110
        if chr_ == G.CHARS[5]:
            sgn = -1
        if chr_ != G.CHARS[5]:
            return l120
        return l110

    def l110():
        nonlocal posit, chr_
        chr_ = G.FIELD[posit]
        posit += 1
        if chr_ == G.CHARS[1]:
            return l110
        return l120

    def l120():
        for i in range(iposit, 12):
            buf[i] = G.CHARS[32]
        return l140

    def l140():
        nonlocal res, posit, chr_
        if chr_ == G.CHARS[3]:
            return l150
        if typchr(chr_) != -2:
            return l150
        num = 0
        for i in range(1, 11):
            if G.DIGITS[i] == chr_:
                num = i - 1
                break
        res = res * 10 + num
        chr_ = G.FIELD[posit]
        posit += 1
        return l140

    def l150():
        nonlocal iexp
        iexp = iexp + sgn * res
        if zflag == 0:
            iexp = 0
        if -1000 > iexp or iexp > 1000:
            return l300

        buf[11] = G.CHARS[27]
        buf[12] = G.CHARS[4]
        if iexp < 0:
            buf[12] = G.CHARS[5]
        iexp_abs = abs(iexp)

        ip = 13
        itas(iexp_abs, temp, 10)
        for i in range(1, 7):
            if temp[i] == G.CHARS[1]:
                continue
            buf[ip] = temp[i]
            ip += 1

        for i in range(1, 17):
            G.FIELD[i] = buf[i]
        return None

    def l200():
        if chr_ != G.CHARS[8]:
            return l230
        return l205

    def l205():
        nonlocal iexp
        iexp = iposit - 11
        for i in range(iposit, 11):
            buf[i] = G.CHARS[32]
        return l220

    def l220():
        nonlocal posit, chr_
        chr_ = G.FIELD[posit]
        if chr_ == G.CHARS[3]:
            return l150
        posit += 1
        if chr_ == G.CHARS[1]:
            return l220
        return l230

    def l230():
        if typchr(chr_) == -2:
            return l240
        if typchr(chr_) != -1:
            return l150
        if chr_ != G.CHARS[27]:
            return l300
        return l105

    def l240():
        nonlocal zflag, iposit
        if chr_ == G.CHARS[32] and iposit == 2:
            return l250
        zflag = 1
        buf[iposit] = chr_
        iposit += 1
        if iposit > 11 and chr_ != G.CHARS[32]:
            errmes(28)
        return l220

    def l250():
        nonlocal iexp
        iexp -= 1
        return l220

    def l300():
        errmes(31)
        return None

    blk = l20
    while blk is not None:
        blk = blk()
