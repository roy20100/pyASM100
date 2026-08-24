"""Reader for the .APO object file format written by pyasm100's PASS1/PASS2.

This is new code (not a port) -- but the format itself isn't a guess: it's
exactly what pyasm100/pass1.py and pass2.py write, verified byte-for-byte
against a real reference object file (APFLIB.APO) while porting the
assembler. Every block shape below is transcribed directly from the
FORMAT strings in pass1.py/pass2.py's fwrite() calls, not reconstructed
from examples.

Block grammar (each recognized by a "***MARKER" substring on a line):

  ***LSB              -- $LIB seen, no data (1 line)
  ***TITLE            -- module title (marker line + 1 name line)
  ***AENTRY           -- $ENTRY with an SPAD param count 0-15
                          (marker+data line: name, value, literal "2", count)
  ***ENTRY            -- $ENTRY/$GLOBAL/$SUBR (marker+data line: name,
                          value, kind 0=global/1=entry, count)
  ***CODE             -- header line (IWCT, MLOC) + IWCT data lines, each
                          either 4 octal words, or "*"-prefixed with a
                          trailing (fielddes, type, arg) relocation triplet
  ***DBDB             -- $COMMON block header (elmcnt, name, id) + a
                          variable run of "type elmcnt" group-summary
                          lines (no explicit count; each is exactly two
                          bare decimal tokens, which no other block
                          produces, so that's the terminator heuristic)
  ***DBIB             -- one $DATA element; marker line is immediately
                          followed by exactly one data line in one of four
                          shapes depending on element type and whether the
                          value was a relocatable expression (see
                          _read_dbib). REAL-typed elements never carry a
                          relocation triplet -- they go through RTOE and
                          are written as normalized text, never through
                          the relocation-triplet path at all.
  ***EXT              -- header line (count) + that many name lines
  ***END              -- marker line + 1 title-name line
  ***LEB              -- &ENDLIB seen in place of a final ***END, no data

Neither test corpus (APFLIB.APO, SYMLIB.APO) exercises $COMMON/$DATA, so
the DBDB/DBIB paths are unverified against real data -- verify those via
round-tripping a small pyasm100-assembled test program with $COMMON/$DATA
declarations instead (see the test suite).
"""

from __future__ import annotations

from dataclasses import dataclass, field


class ObjFileError(Exception):
    pass


@dataclass
class Reloc:
    flddes: int
    type: int
    arg: int


@dataclass
class CodeWord:
    words: tuple[int, int, int, int]
    reloc: Reloc | None = None


@dataclass
class CodeBlock:
    iwct: int
    mloc: int
    words: list[CodeWord] = field(default_factory=list)


@dataclass
class Entry:
    name: str
    value: int
    kind: int  # 0 = $GLOBAL, 1 = $ENTRY/$SUBR
    paramcount: int | None = None  # present for $ENTRY (AENTRY/plain ENTRY), None for $GLOBAL


@dataclass
class CommonBlock:
    name: str
    id: int
    groups: list[tuple[int, int]] = field(default_factory=list)  # (type, elmcnt)


@dataclass
class DataRecord:
    id: int  # which CommonBlock this belongs to
    index: int  # element offset within the block
    rptcnt: int
    type: int  # 1=int 2=real 4=triple, +16 if the value was relocatable
    value: int | None = None  # integer element value, or triple's low mantissa/IVAL
    exponent: int | None = None  # triple only
    hmant: int | None = None  # triple only
    text: str | None = None  # real only: RTOE-normalized "SSSSSSSSSEsNN" text
    reloc: Reloc | None = None


@dataclass
class Module:
    path: str
    is_lib: bool = False
    is_endlib: bool = False
    title: str | None = None
    entries: list[Entry] = field(default_factory=list)
    code_blocks: list[CodeBlock] = field(default_factory=list)
    common_blocks: list[CommonBlock] = field(default_factory=list)
    data_records: list[DataRecord] = field(default_factory=list)
    externs: list[str] = field(default_factory=list)


def read_object_file(path: str) -> list[Module]:
    """A .APO file can contain several $TITLE...$END modules (a $LIB..
    &ENDLIB library file), so this returns a list, one Module per
    $TITLE/$END (or the final $LIB/&ENDLIB) pair."""
    with open(path, "r") as fh:
        lines = [ln.rstrip("\n").rstrip("\r") for ln in fh if ln.strip()]

    modules: list[Module] = []
    cur = Module(path=path)
    i = 0
    n = len(lines)

    def peek():
        return lines[i] if i < n else None

    while i < n:
        line = lines[i]
        if "***LSB" in line:
            cur.is_lib = True
            i += 1
        elif "***TITLE" in line:
            i += 1
            cur.title = lines[i].strip()
            i += 1
        elif "***AENTRY" in line:
            i += 1
            tok = lines[i].split()
            cur.entries.append(
                Entry(name=tok[0], value=int(tok[1], 8), kind=1, paramcount=int(tok[3], 8))
            )
            i += 1
        elif "***ENTRY" in line:
            i += 1
            tok = lines[i].split()
            cur.entries.append(
                Entry(name=tok[0], value=int(tok[1], 8), kind=int(tok[2]), paramcount=int(tok[3], 8))
            )
            i += 1
        elif "***CODE" in line:
            tok = line.split()
            iwct = int(tok[1], 8)
            mloc = int(tok[2], 8)
            block = CodeBlock(iwct=iwct, mloc=mloc)
            i += 1
            for _ in range(iwct):
                block.words.append(_read_code_word(lines[i]))
                i += 1
            cur.code_blocks.append(block)
        elif "***DBDB" in line:
            tok = line.split()
            elmcnt0 = int(tok[1], 8)
            name = tok[2]
            block_id = int(tok[3])
            cb = CommonBlock(name=name, id=block_id)
            i += 1
            while i < n:
                nxt = peek()
                gtoks = nxt.split() if nxt else []
                if len(gtoks) != 2 or not all(_is_int(t) for t in gtoks):
                    break
                cb.groups.append((int(gtoks[0]), int(gtoks[1], 8)))
                i += 1
            if not cb.groups:
                cb.groups.append((0, elmcnt0))
            cur.common_blocks.append(cb)
        elif "***DBIB" in line:
            i += 1
            cur.data_records.append(_read_dbib(lines[i]))
            i += 1
        elif "***EXT" in line:
            tok = line.split()
            count = int(tok[1], 8)
            i += 1
            for _ in range(count):
                cur.externs.append(lines[i].strip())
                i += 1
        elif "***END" in line:
            i += 1
            i += 1  # title-name line, already captured at $TITLE time
            modules.append(cur)
            cur = Module(path=path)
        elif "***LEB" in line:
            # &ENDLIB is a bare end-of-library sentinel following the last
            # module's own ***END -- it does not open a new module, so
            # there's nothing to append here.
            modules[-1].is_endlib = True
            break
        else:
            raise ObjFileError(f"{path}: unrecognized line {i + 1}: {line!r}")

    return modules


def _is_int(tok: str) -> bool:
    try:
        int(tok)
        return True
    except ValueError:
        return False


def _read_code_word(line: str) -> CodeWord:
    tok = line.split()
    if tok and tok[0] == "*":
        words = tuple(int(t, 8) for t in tok[1:5])
        flddes, typ, arg = int(tok[5]), int(tok[6]), int(tok[7], 8)
        return CodeWord(words=words, reloc=Reloc(flddes, typ, arg))
    words = tuple(int(t, 8) for t in tok[:4])
    return CodeWord(words=words)


def _read_dbib(line: str) -> DataRecord:
    tok = line.split()
    id_ = int(tok[0], 8)
    index = int(tok[1], 8)
    # The TYPE field is decimal '2' for REAL (a totally different line
    # shape -- see module docstring) and otherwise octal-rendered by
    # ITAS. '2' reads identically either way, so check it as a string
    # first to pick the branch, matching pass2.py's l1850 dispatch.
    if tok[2] == "2":
        rptcnt = int(tok[3], 8)
        # RTOE fills unused mantissa-digit slots with blanks (not zeros),
        # so the raw text can read e.g. "3.14   E+00" -- join with no
        # separator (RTOE's own digits never contain embedded blanks) so
        # the result stays a plain float()-parseable numeral.
        text = "".join(tok[4:])
        return DataRecord(id=id_, index=index, rptcnt=rptcnt, type=2, text=text)

    typ = int(tok[2], 8)
    rptcnt = int(tok[3], 8)

    if typ in (4, 20):
        exponent = int(tok[4])
        hmant = int(tok[5])
        value = int(tok[6])
        if len(tok) > 7:
            reloc = Reloc(flddes=int(tok[7]), type=int(tok[8]), arg=int(tok[9], 8))
        else:
            reloc = None
        return DataRecord(
            id=id_, index=index, rptcnt=rptcnt, type=typ,
            exponent=exponent, hmant=hmant, value=value, reloc=reloc,
        )

    # INTEGER (1 or 17 if relocatable)
    value = int(tok[4])
    if len(tok) > 5:
        reloc = Reloc(flddes=int(tok[5]), type=int(tok[6]), arg=int(tok[7], 8))
    else:
        reloc = None
    return DataRecord(id=id_, index=index, rptcnt=rptcnt, type=typ, value=value, reloc=reloc)
