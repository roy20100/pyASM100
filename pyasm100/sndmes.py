"""SNDMES = SEND ERROR MESSAGE (ASM100.FTN line 7321).

Flushes the up-to-12 (message number, line number) pairs ERRMES queued in
ERNUMS for the current line to the listing file, one line per error, each
prefixed with "**" and a severity/category letter baked into the message
text (W=warning, C=conflict, M=missing, O=out-of-range, B=bad statement).

The 45 message texts are a mechanical transcription of the FORTRAN
Hollerith literals in the source's per-message FORMAT statements (1001..
1045) -- same fixed "** <text> (nn) ON LINE nnnn" template throughout, so
this is a data table plus one format rather than 45 near-identical
WRITE/FORMAT blocks.
"""

from __future__ import annotations

from .common import G
from .fio import fwrite
from .header import header
from .hollerith import holl

_STAR = holl("**")

# Index 0 unused; message numbers are 1-based, matching ERNUMS/ERRMES.
_MESSAGES = [
    None,
    "W  LINE BUFFER OVERFLOW (",
    "C  MULTIPLY DEFINED SYMBOL (",
    "C  CONFLICTING OP-CODES (",
    "C  S-PAD ADDRESS OUT OF RANGE (",
    "O  BRANCH ADDRESS OUT OF RANGE (",
    "C  CONFLICTING BRANCH ADDRESS (",
    "M  MISSING BRANCH ADDRESS (",
    "C  CONFLICTING DATA PAD INDEXES (",
    "M  BAD OR MISSING EXPRESSION (",
    "M  BAD FADD ARGUEMENT (",
    "M  BAD FMUL ARGUEMENT (",
    "M  MISSING FADD OR FMUL ARGUEMENT (",
    "C  VALUE FIELD CONFLICT (",
    "M  MISSING DATA PAD INDEX (",
    "M  UNDEFINED OP-CODE (",
    "M  $EXT SYMBOL IN EXPRESSION (",
    "M  UNDEFINED USER SYMBOL (",
    "O  INTEGER OVERFLOW (",
    "W  BAD OPTION - DEFAULT VALUE USED (",
    "B  UNRECOGNIZED STATEMENT (",
    "M  IMPROPER $LOC VALUE (",
    "B  BAD COMMON STATEMENT (",
    "W  MISSING $END (",
    "O  DATA PAD INDEX OUT OF RANGE (",
    "B  BAD DATA STATEMENT (",
    "M  BAD DATA PAD INDEX EXPR (",
    "B  COMMA MISSING (",
    "M  NUMBER TO LARGE,TRUNCATED (",
    "B  MISSING SEP AFTER D.P. INDEX (",
    "W  EXTRANEOUS BROUHAHA (",
    "M  BAD FLOATING POINT CONSTANT (",
    "W  ILLEGAL PSEUDO-OP POSITION (",
    "W  ENTRY SYMBOL NOT LOCAL (",
    "M  BAD PARAMETER (",
    "W  UNDEFINED ENTRY SYMBOL (",
    "C  DATA PAD BUS CONFLICT (",
    "M  MISSING S-PAD ADDRESS (",
    "M  MISSING PROGRAM SOURCE ADDRESS (",
    "C  XW/YW CONFLICT (",
    "B   UNRECOGNIZED PSEUDO OP (",
    "B   SYMBOL TABLE OVERFLOW (",
    "B  COMIO STATEMENT OUT OF ORDER OR ILLFORMATED (",
    "BAD PARAM STATEMENT (",
    "B  SUBROUTINE NAME MUST BE DECLARED EXTERNAL (",
    "B  BAD OR MISSING SYMBOL STRING (",
]


def sndmes() -> None:
    if G.ERRCNT == 0:
        return

    for i in range(1, G.ERRCNT + 1):
        G.LINES += 2
        if G.LINES > 54:
            header()

        j = G.ERNUMS[i, 1]
        text = _MESSAGES[j]
        fmt = f"(1X, 2A2,'{text}',I2,10H) ON LINE ,I4,/1X)"
        fwrite(G.LLUN, fmt, [_STAR, _STAR, j, G.ERNUMS[i, 2]])

    G.ERRTOT += G.ERRCNT
    G.ERRCNT = 0
