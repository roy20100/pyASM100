"""ITAS = INTEGER TO CHARACTER CONVERSION (ASM100.FTN line 7265).

Converts VALUE into a right-justified, blank-padded, up-to-6-character
RADIX string in STR(6) (one character per element, Hollerith-packed with a
trailing blank as the digit table does). Overflow (more than 6 digits)
turns the whole field into '*' -- faithfully reproducing an original
quirk: the overflow branch's inner loop always assigns STR(1), never
STR(K), so only the first character actually becomes '*'.
"""

from __future__ import annotations

from .farray import FArray
from .hollerith import holl

_ZERO = holl("0 ")
_STAR = holl("* ")
_BLANK = holl("  ")


def itas(value: int, str_: FArray, radix: int) -> None:
    for i in range(1, 7):
        str_[i] = _BLANK

    a = float(radix)
    j = a
    n = float(value & 0xFFFF)  # PFLOAT: unsigned 16-bit magnitude

    i = 6
    overflow = False
    for i in range(1, 7):
        if j > n:
            break
        j *= a
    else:
        i = 6
        if n > j:
            overflow = True

    if overflow:
        str_[1] = _STAR
    else:
        j = j / a
        for k in range(1, i + 1):
            m = int(n / j)
            n = n - float(m) * j
            str_[k] = m + _ZERO
            j = j / a

    if i == 6:
        return
    i = 6 - i
    for _m in range(1, i + 1):
        for k in range(1, 6):
            l = 7 - k
            str_[l] = str_[l - 1]
        str_[1] = _BLANK
