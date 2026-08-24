"""GARG = GET ARGUEMENT (ASM100.FTN line 5383).

Reads a symbol via GSYM and matches it against ARGSYM(1..2, L1..L2), the
allowable-arguments table for a group of related op-codes. On a match,
KVAL is set to the argument's ID (ARGSYM(3,*)) and, if ARGSYM(4,*) is
nonzero, special processing runs for a DPY (1) or DPX (2) argument: an
index-register value that must either match one already recorded in
CODMSK/CODE, or (if the break char was '(') be read as a parenthesized
expression via GVAL and range/shift-encoded.

PTR conventions: 0 = no match, -1 = matched but a later error occurred
(already reported), otherwise the ARGSYM index.

The DPY (mask 56, shift x8) and DPX (mask 448, shift x64) special-
processing blocks are structurally identical in the source (a copy-pasted
pair differing only in those two constants) -- unlike other trampoline
ports here there's no real GOTO-formed loop, just the same shared block
reached from two computed-GOTO targets, so this is one ordinary Python
helper called with different constants rather than duplicated blocks.
"""

from __future__ import annotations

from .bitops import iand16, ior16
from .box import Box
from .common import G
from .errmes import errmes
from .exflds import exflds
from .gsym import gsym
from .gval import gval


def garg(l1: int, l2: int, kval: Box) -> None:
    gsym()
    if G.ALFLG < 0:
        G.PTR = 0
        return

    ptr = 0
    for j1 in range(l1, l2 + 1):
        if G.SYM[1] != G.ARGSYM[1, j1]:
            continue
        if G.SYM[2] != G.ARGSYM[2, j1]:
            continue
        if G.SYM[3] != G.BLANK:
            continue
        ptr = j1
        break

    if ptr == 0:
        G.PTR = 0
        return

    G.PTR = ptr
    kval.value = G.ARGSYM[3, ptr]
    special = G.ARGSYM[4, ptr]
    if special <= 0:
        return

    if special == 1:
        _reg_arg(mask=56, shift=8, implied_zero=32)
    elif special == 2:
        _reg_arg(mask=448, shift=64, implied_zero=256)


def _reg_arg(mask: int, shift: int, implied_zero: int) -> None:
    """DPY (mask=56,shift=8,iz=32) / DPX (mask=448,shift=64,iz=256)."""
    if G.IBRF != 11:
        _merge_or_check(implied_zero, mask)
        return
    _from_expr(mask, shift)


def _merge_or_check(iv: int, mask: int) -> None:
    jx = iand16(G.CODMSK[3], mask)
    if jx != 0:
        jx2 = iand16(G.CODE[3], mask)
        if jx2 != iv:
            errmes(8)
            G.PTR = -1
        return
    G.CODMSK[3] = ior16(G.CODMSK[3], mask)
    G.CODE[3] = ior16(G.CODE[3], iv)


def _from_expr(mask: int, shift: int) -> None:
    G.NXC -= 1
    exflds(G.CHARS[11], G.CHARS[12], 0, 1)
    G.FLDFLG = 1
    extptr = Box(0)
    gval(0, extptr)
    G.FLDFLG = 0
    if G.GVLFLG < 0:
        errmes(26)
        G.PTR = -1
        return

    if (
        G.IBRF != 0
        and G.IBRF != 14
        and G.IBRF != 3
        and G.IBRF != 11
        and G.IBRF != 15
    ):
        errmes(29)

    if G.IVAL + 4 < 0 or G.IVAL - 3 > 0:
        errmes(24)
        G.PTR = -1
        return

    iv = (G.IVAL + 4) * shift
    _merge_or_check(iv, mask)
