"""FPGET = GET A FLOATING POINT NUMBER (ASM100.FTN line 4686).

Parses a floating-point literal (sign, integer part, optional fractional
part, optional E-exponent) from LIN starting at NXC, then converts it to
the FPS-100's packed floating-point representation (a normalized 0.5..1.0
mantissa scaled by a power-of-2 exponent, split into 11+1+15 mantissa bits
plus a convergent-rounded 14-bit remainder) and merges the result into
CODE(2..4).

Ported as a block trampoline: the parse phase especially has several
short branches whose fallthrough paths overlap (e.g. the optional single
blank after a sign at label 200), which is easy to get subtly wrong by
hand-merging -- one function per label avoids that risk.
"""

from __future__ import annotations

from .arith import fdiv
from .bitops import ior16
from .box import Box
from .common import G
from .errmes import errmes


def fpget(nerr: Box) -> None:
    accum = 0.0
    iexp = 0
    ktw = 0
    ktx = 0
    nerr.value = 0

    l1 = 0
    ipar1 = ipar2 = ipar3 = ipar4 = 0

    def l_start():
        nonlocal l1
        l1 = G.LIN[G.NXC]
        G.NXC += 1
        if l1 == G.CHARS[4]:
            return l200
        if l1 != G.CHARS[5]:
            return l400
        return l100

    def l100():
        nonlocal ktw
        ktw = 1
        return l200

    def l200():
        nonlocal l1
        l1 = G.LIN[G.NXC]
        G.NXC += 1
        if l1 != G.CHARS[1]:
            return l400
        return l300

    def l300():
        nonlocal l1
        l1 = G.LIN[G.NXC]
        G.NXC += 1
        return l400

    def l400():
        if G.CHARS[32] <= l1 <= G.CHARS[33]:
            return l600
        return l700

    def l600():
        nonlocal accum, l1
        dig = l1 - G.CHARS[32]
        accum = accum * 10.0 + dig
        l1 = G.LIN[G.NXC]
        G.NXC += 1
        return l400

    def l700():
        if l1 != G.CHARS[8]:
            return l800
        return l1100

    def l800():
        if l1 != G.CHARS[27]:
            return l900
        return l1500

    def l900():
        if l1 != G.CHARS[3]:
            return l1000
        return l2500

    def l1000():
        errmes(31)
        nerr.value = 1
        return l2500

    def l1100():
        nonlocal pten
        pten = 1.0
        return l1200

    def l1200():
        nonlocal l1
        l1 = G.LIN[G.NXC]
        G.NXC += 1
        if G.CHARS[32] <= l1 <= G.CHARS[33]:
            return l1400
        return l800

    def l1400():
        nonlocal pten, accum
        pten = pten / 10.0
        dig = l1 - G.CHARS[32]
        accum = accum + pten * dig
        return l1200

    def l1500():
        nonlocal l1
        l1 = G.LIN[G.NXC]
        G.NXC += 1
        if l1 != G.CHARS[1]:
            return l1600
        return l1500

    def l1600():
        if l1 == G.CHARS[4]:
            return l1800
        if l1 != G.CHARS[5]:
            return l1900
        return l1700

    def l1700():
        nonlocal ktx
        ktx = 1
        return l1800

    def l1800():
        nonlocal l1
        l1 = G.LIN[G.NXC]
        G.NXC += 1
        return l1900

    def l1900():
        if G.CHARS[32] <= l1 <= G.CHARS[33]:
            return l2100
        return l2200

    def l2100():
        nonlocal iexp
        dig = l1 - G.CHARS[32]
        iexp = iexp * 10 + dig
        return l1800

    def l2200():
        if l1 != G.CHARS[3]:
            return l2300
        return l2400

    def l2300():
        errmes(31)
        nerr.value = 1
        return l2400

    def l2400():
        nonlocal iexp, accum
        if ktx == 1:
            iexp = -iexp
        accum = accum * (10.0**iexp)
        return l2500

    def l2500():
        if accum != 0:
            return l5000
        return l6500

    def l5000():
        # 5000-5300: normalize ACCUM into [0.5, 1.0) by powers of 2,
        # tracking the exponent. The source's 5100/5300 shrink-loop and
        # 5200 grow-loop are each self-contained (the grow-loop only ever
        # starts once the shrink-loop has ACCUM < 1.0), so this sequential
        # rewrite is behaviorally identical to the interleaved GOTOs.
        nonlocal iexp, accum
        iexp = 512
        while accum >= 1.0:
            accum = accum / 2.0
            iexp += 1
        while accum < 0.5:
            accum = accum * 2.0
            iexp -= 1
        return l5400

    def l5400():
        nonlocal accum, ipar1, ipar2, ipar3, ipar4
        accum = accum * 2048.0
        ipar1 = int(accum)
        dig = float(ipar1)
        accum = (accum - dig) * 2.0
        ipar2 = int(accum)
        dig = float(ipar2)
        accum = (accum - dig) * 32768.0
        ipar3 = int(accum)
        dig = float(ipar3)
        ipar4 = int((accum - dig) * 16384.0)
        return l_round()

    def l_round():
        nonlocal ipar1, ipar2, ipar3, iexp
        i2 = (ipar4 + 8191) // 16384
        if i2 == 1 and ipar3 == 32767:
            ipar3 = 0
            i2 = (ipar2 + 1) // 2
            ipar2 = (ipar2 + 1) % 2
            ipar1 = ipar1 + i2
            if ipar1 != 2048:
                return l5600
            ipar2 = 0
            ipar1 = 1024
            iexp += 1
            return l5600
        ipar3 = ipar3 + i2
        return l5600

    def l5600():
        # IEXP could in principle be negative (an extremely small literal),
        # so use FORTRAN-truncating div/mod rather than Python's floored //%.
        i2 = fdiv(iexp, 16)
        G.CODE[2] = i2
        i2 = iexp - fdiv(iexp, 16) * 16
        if i2 < 8:
            return l5700(i2)
        G.CODE[3] = G.ISBT
        i2 = iexp - fdiv(iexp, 8) * 8
        return l5700(i2)

    def l5700(i2: int):
        i2 = i2 * 4096
        G.CODE[3] = ior16(G.CODE[3], i2)
        if ktw > 0:
            return l6100
        return l5800

    def l5800():
        G.CODE[3] = ior16(G.CODE[3], ipar1)
        if ipar2 > 0:
            return l5900
        return l6000

    def l5900():
        G.CODE[4] = ior16(G.CODE[4], G.ISBT)
        return l6000

    def l6000():
        G.CODE[4] = ior16(G.CODE[4], ipar3)
        return l6500

    def l6100():
        if ipar3 != 0:
            return l6400
        if ipar2 == 0:
            return l6300
        G.CODE[4] = G.ISBT
        return l6200

    def l6200():
        nonlocal ipar1
        ipar1 = ipar1 + 1
        return l6300

    def l6300():
        G.CODE[3] = ior16(G.CODE[3], 4096 - ipar1)
        return l6500

    def l6400():
        G.CODE[4] = 32767 - ipar3 + 1
        if ipar2 == 0:
            G.CODE[4] = ior16(G.CODE[4], G.ISBT)
        return l6200

    def l6500():
        return None

    pten = 1.0
    blk = l_start
    while blk is not None:
        blk = blk()
