"""HEADER = OUTPUTS HEADER LINE TO LISTING (ASM100.FTN line 7631).

Form-feeds to a new listing page and writes the "ASM100 REL. ..." banner
with filename, title, date, time, and page number. On the first page only,
fetches the date/time via DATTIM and reformats TIMES(1..5) (month, day,
year, hour, minute as plain integers) into the 10 individual tens/ones
digits FORMAT 200 prints.
"""

from __future__ import annotations

from .common import G
from .fio import dattim, fwrite

_FMT_100 = "(1H1)"
_FMT_200 = (
    "(1X, 'ASM100 REL.  1.00 , 09/01/79 ',30A1,2X,3A2,2X,2(2I1"
    ",'/'),2I1,3X,2I1,1H:,2I1,3X,5HPAGE ,I4,//1X)"
)


def header() -> None:
    if G.PAGES == 0:
        dattim(G.TIMES)
        if G.TIMES[1] != 0:
            G.TIMES[3] = G.TIMES[3] - int(float(G.TIMES[3]) / 100.0) * 100
            ii = [G.TIMES[i] for i in range(1, 6)]
            for i in range(1, 6):
                G.TIMES[2 * i - 1] = ii[i - 1] // 10
                G.TIMES[2 * i] = ii[i - 1] % 10

    fwrite(G.LLUN, _FMT_100, [])

    G.PAGES += 1
    values = (
        [G.SFILE[i] for i in range(2, 32)]
        + [G.TI[j] for j in range(1, 4)]
        + [G.TIMES[k] for k in range(1, 11)]
        + [G.PAGES]
    )
    fwrite(G.LLUN, _FMT_200, values)

    G.LINES = 3
