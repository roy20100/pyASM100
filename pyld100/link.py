"""Multi-module link orchestration.

New code: assigns addresses, builds the symbol table, and walks every
module's code words applying relocate.compute_val() -- the parts that
are grounded are symtab.py (address assignment) and relocate.py (the VAL
formulas); this module is just the plumbing that drives them in order,
matching LINKUP's own outer loop (read module -> relocate its code ->
advance LOCCUR) without reproducing its task/overlay/library machinery.

Data-record ($COMMON/$DATA) relocation and common-block base-address
assignment aren't implemented here: no .APO file in this project's test
corpus (APFLIB.APO, SYMLIB.APO) uses $COMMON/$DATA, so there's nothing to
verify a design against, and psmd.py (milestone 4) additionally needs to
decide how to split mixed-VTYPE data across asm2lm.py's single-VTYPE-per
-file MD format before that path is worth building out.
"""

from __future__ import annotations

from dataclasses import dataclass

from pyasm100.bitops import iadd16

from .objfile import Module
from .relocate import compute_val
from .symtab import LinkError, ResolvedEntry, assign_ldaddr, build_symtab, resolve_externs


@dataclass
class LinkedWord:
    addr: int
    words: tuple[int, int, int, int]


@dataclass
class LinkedProgram:
    ps: list[LinkedWord]
    symtab: dict[str, ResolvedEntry]
    ldaddr: dict[int, int]


def link(modules: list[Module], origin: int = 0) -> LinkedProgram:
    """Link `modules` (in the given order) into one PS address space
    starting at `origin`. Raises LinkError listing every unresolved
    external if any module's $EXT can't be matched."""
    ldaddr = assign_ldaddr(modules, origin)
    symtab = build_symtab(modules, ldaddr)

    missing = resolve_externs(modules, symtab)
    if missing:
        raise LinkError("unresolved externals:\n  " + "\n  ".join(missing))

    ps: list[LinkedWord] = []
    for m in modules:
        base = ldaddr[id(m)]
        pos = 0
        for cb in m.code_blocks:
            for w in cb.words:
                words = list(w.words)
                if w.reloc is not None:
                    val = compute_val(
                        w.reloc, m, ldaddr, loccur=base + pos, symtab=symtab
                    )
                    words[3] = iadd16(words[3], val)
                ps.append(LinkedWord(addr=base + pos, words=tuple(words)))
                pos += 1

    return LinkedProgram(ps=ps, symtab=symtab, ldaddr=ldaddr)
