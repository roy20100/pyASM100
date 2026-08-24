"""LENGTH = LENGTH OF FILE NAME (ASM100.FTN line 7862).

Reformats a blank-padded A1 filename buffer in place for use by INFILE:
finds the last non-blank position (scanning from position 30 down), shifts
those characters right by one slot, and stores the count in slot 1 --
i.e. BUF becomes [count, char1, char2, ..., charN, ...]. INFILE is always
called immediately after LENGTH on the same buffer, so fio._arr_to_filename
reads exactly this counted-string layout.
"""

from __future__ import annotations

from .farray import FArray

_BLANK = ord(" ")


def length(buf: FArray) -> None:
    id_ = 1
    for i in range(1, 31):
        id_ = 31 - i
        if buf[id_] != _BLANK:
            break
    for i in range(1, id_ + 1):
        j = (id_ + 1) - i
        buf[j + 1] = buf[j]
    buf[1] = id_
