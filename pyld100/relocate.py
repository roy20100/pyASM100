"""Relocation VAL formulas (TYPEN 1-5), extracted from real APLOAD source.

This is the one piece of pyld100 that's a direct port rather than new
code: LED100.FTN's LINKUP (code-word relocation, ~lines 2707-2758) and
DTAREL (data-record relocation, ~lines 1059-1089) compute the exact same
five VAL formulas, just applied to different targets (a ***CODE word vs a
***DBIB record). Reproduced here as one function so both call sites in
link.py share it, mirroring that structural identity in the original.

TYPEN meanings (LED100.FTN LINKUP dispatch, GOTO(2150,2200,2400,2300,2200)):
  1: program-source-relocatable -- VAL = the referencing module's own
     load address (LDADDR/PSBRK). Not exercised by any real .APO in this
     project's test corpus (APFLIB.APO/SYMLIB.APO only ever use TYPEN 5)
     -- implemented from the source, not verified against real data.
  2: external reference, absolute encoding (e.g. an APFTN host call) --
     same lookup as 5, but LINKUP explicitly never applies the
     PC-relative subtraction for TYPEN 2 ("WE DON'T EVER DO THIS IF THE
     CALL IS FROM APFTN"). Not exercised by the test corpus either.
  3: DB (common-block) reference -- VAL = that block's assigned base
     address. Only meaningful for code-word relocation (DTAREL doesn't
     use it for data-record relocation at all -- see below). ARG is
     assumed to be a 1-based index into the referencing module's own
     $COMMON declarations, by direct analogy with how TYPEN 2/5's ARG
     indexes that module's ***EXT list (LINKUP: "VAL=ARG+PTREXT-1;
     VAL=EXTDT1(VAL)") -- this analogy is *not* independently confirmed
     in the source (LED100.FTN's DBLUN-based DTALNK, which fills in
     PTRDB/DBDTA0, wasn't portable -- see the module docstring in
     objfile.py) and is not exercised by the test corpus.
  4: subroutine-parameter reference, via the callee's local data block
     named ".<ENTRYNAME>" -- FORTRAN/HASI parameter-passing plumbing,
     out of scope per the project's explicit deferral of HASI/host-FORTRAN
     support. Raises NotImplementedError.
  5: external reference, relative encoding -- the common case for one
     APAL routine calling another. VAL = the matched entry's absolute
     value; if the entry is relocatable (kind/RELTYP != 0), VAL is then
     made PC-relative by subtracting the current PS location. This is
     the only TYPEN pyld100 can verify end-to-end (54 occurrences across
     APFLIB.APO, all resolved by SYMLIB.APO/APFLIB.APO's own entries).

Common formula for TYPEN 2/5, transcribed from LINKUP ~2719-2731:
    VAL=ARG+PTREXT-1; VAL=EXTDT1(VAL); ID=EXTST(EXTDTA,VAL,SYM,6)
    INDX=SRCST(ENTDTA,1,-1,SYM,6); VAL=EXTVT(ENTDTA,INDX,1,IVAL,2)
    RELTYP=IAND16(IVAL(2),7)
    IF (RELTYP.NE.0 .AND. TYPEN.NE.2) VAL=ISUB16(VAL,LOCCUR)
and from DTAREL ~1082-1089 (data-record case -- note DTAREL has *no*
RELTYP/LOCCUR adjustment at all; a data value that references an
external is always stored absolute):
    VAL=ARG+PTREXT-1; VAL=EXTDT1(VAL); ID=EXTST(EXTDTA,VAL,SYM,6)
    INDX=SRCST(ENTDTA,1,-1,SYM,6); DTAREL=EXTVT(ENTDTA,INDX,1,VAL,1)
"""

from __future__ import annotations

from pyasm100.arith import isub16

from .objfile import Module, Reloc
from .symtab import LinkError, ResolvedEntry


def compute_val(
    reloc: Reloc,
    module: Module,
    ldaddr: dict[int, int],
    loccur: int | None,
    symtab: dict[str, ResolvedEntry],
    common_base: dict[tuple[int, int], int] | None = None,
    is_data: bool = False,
) -> int:
    """Return the VAL to add into the relocated field.

    `loccur` is the current word's own absolute PS address -- required
    for code-word relocation (TYPEN 2/5's PC-relative case), ignored for
    data-record relocation (`is_data=True`), where DTAREL never applies
    it. `common_base` maps (id(module), arg) -> that common block's
    assigned base address, for TYPEN 3; only needed if TYPEN 3 is
    actually used.
    """
    typen = reloc.type

    if typen == 1:
        return ldaddr[id(module)]

    if typen == 3:
        if common_base is None or (id(module), reloc.arg) not in common_base:
            raise LinkError(
                f"{module.title}: no base address assigned for common "
                f"block reference (arg={reloc.arg})"
            )
        return common_base[(id(module), reloc.arg)]

    if typen == 4:
        raise NotImplementedError(
            "TYPEN 4 (subroutine-parameter reference via callee's local "
            "data block) is FORTRAN/HASI parameter-passing plumbing, "
            "explicitly out of scope for pyld100 -- see relocate.py"
        )

    if typen in (2, 5):
        if reloc.arg < 1 or reloc.arg > len(module.externs):
            raise LinkError(
                f"{module.title}: relocation arg {reloc.arg} out of range "
                f"for its {len(module.externs)}-entry $EXT list"
            )
        name = module.externs[reloc.arg - 1].strip()
        entry = symtab.get(name)
        if entry is None:
            raise LinkError(f"{module.title}: unresolved external '{name}'")
        val = entry.value
        if not is_data and entry.kind != 0 and typen != 2:
            if loccur is None:
                raise LinkError("loccur is required for code-word relocation")
            val = isub16(val, loccur)
        return val

    raise LinkError(f"{module.title}: invalid TYPEN {typen} (must be 1-5)")
