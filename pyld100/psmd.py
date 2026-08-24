"""PS + MD text emitter, matching asm2lm.py's input format exactly
(see asm2lm.py's own module docstring for the authoritative spec).

The PS side (format_ps) is straightforward and fully verified: a
LinkedProgram's words are already absolute-addressed 4-word lines: exactly
asm2lm.py's `[addr] w1 w2 w3 w4` PS format.

The MD side ($COMMON/$DATA) is new, unverified territory: no .APO file in
this project's test corpus (APFLIB.APO, SYMLIB.APO) declares any
$COMMON/$DATA, so there's no real data to check a design against -- see
link.py's module docstring. Two things had to be decided without that
grounding:

  1. Common-block base addresses: assigned here by matching CommonBlock
     NAME across modules (mirroring how $ENTRY/$EXT symbols are matched
     in symtab.py), in a separate MD address space concatenated in link
     order. This is an inference by analogy, not confirmed against real
     APLOAD source or data -- DTALNK/DTAREL's own PTRDB/DBDTA0 tables
     (LED100.FTN ~758-1097) are populated from APLOAD's internal DBLUN
     scratch file, which objfile.py's docstring already notes isn't
     directly portable.
  2. asm2lm.py accepts only one VTYPE per MD file/invocation, but a
     linked program's DataRecords can mix type 1 (integer), 2 (real) and
     4 (triple) freely. Resolved here by splitting into up to three MD
     texts, one per VTYPE, so the caller runs asm2lm.py -m ... --vtype N
     once per non-empty one (see __main__.py).
"""

from __future__ import annotations

from dataclasses import dataclass

from pyasm100.bitops import iadd16

from .link import LinkedProgram
from .objfile import Module
from .relocate import compute_val
from .symtab import LinkError


def format_ps(program: LinkedProgram) -> str:
    lines = [
        f"{w.addr:06o} {w.words[0]:06o} {w.words[1]:06o} {w.words[2]:06o} {w.words[3]:06o}"
        for w in program.ps
    ]
    return "\n".join(lines) + ("\n" if lines else "")


def assign_common_bases(modules: list[Module], origin: int = 0) -> dict[str, int]:
    """Base MD address for each named $COMMON block, keyed by name (not
    matched to any real APLOAD table -- see module docstring)."""
    bases: dict[str, int] = {}
    addr = origin
    for m in modules:
        for cb in m.common_blocks:
            name = cb.name.strip()
            if name in bases:
                continue
            bases[name] = addr
            addr += sum(elmcnt for _typ, elmcnt in cb.groups)
    return bases


@dataclass
class MdEntry:
    addr: int
    type: int  # 1, 2, or 4 (never +16 -- relocation is already applied)
    value: int | None = None  # type 1
    text: str | None = None  # type 2
    words: tuple[int, int] | None = None  # type 4


def relocate_data(
    modules: list[Module],
    program: LinkedProgram,
    common_bases: dict[str, int],
) -> list[MdEntry]:
    """Resolve every DataRecord's address and relocatable value into a
    flat list of MdEntry, applying compute_val() (is_data=True, so no
    PC-relative adjustment -- DTAREL never does that either) for any
    record whose type carries the +16 relocatable flag."""
    common_index: dict[int, dict[int, str]] = {}
    for m in modules:
        common_index[id(m)] = {cb.id: cb.name.strip() for cb in m.common_blocks}

    out: list[MdEntry] = []
    for m in modules:
        blocks_by_id = common_index[id(m)]
        for rec in m.data_records:
            name = blocks_by_id.get(rec.id)
            if name is None:
                raise LinkError(
                    f"{m.title}: data record references unknown common block id {rec.id}"
                )
            base = common_bases.get(name)
            if base is None:
                raise LinkError(f"{m.title}: no base address assigned for $COMMON '{name}'")
            addr = base + rec.index

            base_type = rec.type & ~16
            if rec.reloc is not None:
                val = compute_val(
                    rec.reloc, m, program.ldaddr, loccur=None, symtab=program.symtab,
                    is_data=True,
                )
            else:
                val = 0

            if base_type == 2:
                out.append(MdEntry(addr=addr, type=2, text=rec.text))
            elif base_type == 4:
                # rec.exponent/hmant/value are GFIELD's AP-internal triple
                # encoding (see gfield.py); asm2lm.py's --vtype 4 expects
                # a pre-packed IBM System/360 hex float instead (see its
                # module docstring). No test data exercises this path and
                # no grounded conversion between the two encodings was
                # found, so refuse rather than guess.
                raise NotImplementedError(
                    f"{m.title}: $DATA triple-type MD records aren't "
                    "supported -- their AP-internal (exponent, hmant, "
                    "value) encoding hasn't been mapped to asm2lm.py's "
                    "IBM-hex --vtype 4 format"
                )
            else:  # integer
                value = iadd16(rec.value, val) if val else rec.value
                out.append(MdEntry(addr=addr, type=1, value=value))
    return out


def format_md(entries: list[MdEntry], vtype: int) -> str:
    """Text for one asm2lm.py --vtype invocation; only entries of that
    vtype are included."""
    lines = []
    for e in entries:
        if e.type != vtype:
            continue
        if vtype == 1:
            lines.append(f"{e.addr:06o} {e.value}")
        elif vtype == 2:
            lines.append(f"{e.addr:06o} {e.text}")
        elif vtype == 4:
            lines.append(f"{e.addr:06o} {e.words[0]:06o} {e.words[1]:06o}")
    return "\n".join(lines) + ("\n" if lines else "")
