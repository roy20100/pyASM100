"""Cross-module symbol table for pyld100.

New code, not a port -- but the addressing rule below (how a module's
$ENTRY/$SUBR values become absolute PS addresses) is transcribed directly
from LED100.FTN's real APLOAD entry-record reader (~lines 3649-3657):

    C   GET VALUE AND TYPE AND SAVE THEM TOO. ACTUAL ENTRY PT. IS THE REL.
    C   ADDRESS + PSBRK UNLESS ITS ABSOLUTE.
    IVAL(1)=STOI(SYM,RADIX)
    IV=STOI(SYM,RADIX)
    IVAL(2)=IVAL(2)+IV
    IF (IV .NE. 0) IVAL(1)=IADD16(IVAL(1),PSBRK)

IV there is exactly our Entry.kind (0 for $GLOBAL, 1 for $ENTRY/$SUBR --
pyasm100/pass2.py writes that same 0/1 into the ***ENTRY line's kind
field). PSBRK is APLOAD's running PS-space watermark, i.e. this module's
load address (our `ldaddr`). So: a $GLOBAL entry's value is already
absolute (e.g. SYMLIB.APO's "!DIV $EQU 10000" -- a fixed hardware
address, unaffected by link order); a $ENTRY/$SUBR entry's value is an
offset within its own module and only becomes absolute once the module's
ldaddr is added. IV also becomes RELTYP, reused unchanged by relocate.py.
"""

from __future__ import annotations

from dataclasses import dataclass

from .objfile import Module


class LinkError(Exception):
    pass


@dataclass
class ResolvedEntry:
    name: str
    value: int  # absolute PS address
    kind: int  # 0 = absolute ($GLOBAL), 1 = relocatable ($ENTRY/$SUBR) -- also RELTYP
    module: Module


def assign_ldaddr(modules: list[Module], origin: int = 0) -> dict[int, int]:
    """Assign each module a base PS address by concatenating their code
    words in link (input) order, starting at `origin`.

    Grounded in LINKUP's sequential LOCCUR walk (LED100.FTN ~2671-2791):
    LOCCUR advances by exactly 1 per code word/line copied, regardless of
    each block's own MLOC header -- APLOAD does not seek by MLOC, it just
    copies records in file order. So module N's base is origin plus the
    total word count of modules 0..N-1, and a word's own absolute address
    is its module's base plus its sequential position within that module
    (also ignoring MLOC, for the same reason).

    Keyed by id(module) since Module isn't hashable/frozen.
    """
    ldaddr: dict[int, int] = {}
    addr = origin
    for m in modules:
        ldaddr[id(m)] = addr
        addr += sum(len(cb.words) for cb in m.code_blocks)
    return ldaddr


def build_symtab(modules: list[Module], ldaddr: dict[int, int]) -> dict[str, ResolvedEntry]:
    """Merge every module's $ENTRY/$GLOBAL/$SUBR entries into one
    cross-module table, converting relocatable values to absolute PS
    addresses per the docstring above. Raises LinkError on a duplicate
    definition (APLOAD itself warns and keeps the first -- ERRMES(8),
    LED100.FTN ~3624-3628 -- but silently shadowing a duplicate symbol is
    exactly the kind of mistake a linker should refuse to guess past)."""
    table: dict[str, ResolvedEntry] = {}
    for m in modules:
        base = ldaddr[id(m)]
        for e in m.entries:
            value = e.value + base if e.kind != 0 else e.value
            name = e.name.strip()
            if name in table:
                raise LinkError(
                    f"duplicate entry '{name}': defined in both "
                    f"{table[name].module.title} and {m.title}"
                )
            table[name] = ResolvedEntry(name=name, value=value, kind=e.kind, module=m)
    return table


def resolve_externs(modules: list[Module], symtab: dict[str, ResolvedEntry]) -> list[str]:
    """Return the names referenced via $EXT that have no matching entry
    anywhere in `modules`. An empty list means every external resolved."""
    missing = []
    for m in modules:
        for name in m.externs:
            if name.strip() not in symtab:
                missing.append(f"{m.title}: unresolved external '{name.strip()}'")
    return missing
