"""TYPCHR = DETERMINES TYPE OF CHARACTER (ASM100.FTN line 5179).

Returns -2 if CHR falls in the digit range CHARS(32)..CHARS(33), -1 if it
falls in the letter range CHARS(34)..CHARS(35), else 0. The source expresses
each inclusive range test as a pair of three-way arithmetic IFs; that's
just an inclusive bounds check, written directly here.
"""

from __future__ import annotations

from .common import G


def typchr(chr_: int) -> int:
    if G.CHARS[32] <= chr_ <= G.CHARS[33]:
        return -2
    if G.CHARS[34] <= chr_ <= G.CHARS[35]:
        return -1
    return 0
