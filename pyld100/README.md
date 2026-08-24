# pyld100

A linker for `.APO` object files produced by [`pyasm100`](../README.md)
(the `ASM100.FTN` port). Reads one or more `.APO` modules, resolves `$EXT`
references against other modules' `$ENTRY`/`$GLOBAL` symbols, assigns
addresses, and emits **PS** (program space) and **MD** (main data) text
in the format [`asm2lm.py`](../asm2lm.py) expects, which turns them into
the binary `.lm` load-module format the pySIM100 simulator loads.

Unlike `pyasm100`, this is **not** a 1:1 port. The real 1979 linker,
`APLOAD`, doesn't have a clean standalone source file to port from — see
"Where this comes from" below. `pyld100` is new code that reuses APLOAD's
real relocation-address *formulas* (the one part that's directly grounded
and load-bearing) and writes fresh orchestration/parsing/emission code for
everything else.

## Running it

```
py -3.11 -m pyld100 mod1.apo mod2.apo ... -o stem
```

Links the given `.APO` files, in the order given, into one address space
starting at `0` (override with `--origin N`), and writes:

- `stem.ps` — always, the linked program-space words.
- `stem.md1` / `stem.md2` — only if the input declares `$COMMON`/`$DATA`
  (integer / real elements respectively; see "Known gaps" below).

Feed the results to `asm2lm.py` separately, one file at a time (it only
ever reads one PS or one MD file per run):

```
py asm2lm.py -p stem.ps -o prog.lm
py asm2lm.py -m stem.md1 --vtype 1 -o data.lm   # if stem.md1 exists
py asm2lm.py -m stem.md2 --vtype 2 -o data.lm   # if stem.md2 exists
```

## Where this comes from

`APLOAD` doesn't exist as its own file. Roughly 39 of its subroutines
turned out to be preserved — mislabeled — inside `LED100.FTN` (nominally
the unrelated Library Editor), identifiable by their own header comments
("THIS VERSION OF APLOAD WAS PRODUCED BY CROCK..."). That source is real,
but not cleanly portable as a whole:

- Several utilities it calls constantly (`EXTTOK`, `STOI`, `EXTVT`,
  `EXTST`, `SRCST`, `UPAKS`, `INSCS`, `WRTLIN`) are referenced everywhere
  and defined nowhere in the surviving file.
- Its core loader (`LOAD1`, ~940 lines) has overlay/task/ISR handling
  woven directly into its control flow, not separable from plain linking.
- Its data-relocation path (`DTALNK`/`DTAREL`) reads APLOAD's own internal
  scratch-file format (`DBLUN`), not the `.APO` format directly.
- There's no real APLOAD output anywhere to diff a full port against —
  unlike `pyasm100`, which was verified byte-for-byte against a real
  reference object file.

So `pyld100` reuses only what's directly grounded and independently
checkable: the relocation-address (`VAL`) formulas from `LINKUP` (code
words, `LED100.FTN` ~2668-2810) and `DTAREL` (data records, ~992-1097),
reproduced in `relocate.py`. Everything else — the `.APO` reader, the
symbol table, link orchestration, PS/MD emission, the CLI — is new code,
because the equivalent APLOAD pieces are either missing, tangled up with
out-of-scope features, or targeting a format that doesn't apply here.

## Module map

| Module | What it does |
|---|---|
| `objfile.py` | Reads `.APO` files (`***TITLE/***ENTRY/***CODE/***DBDB/***DBIB/***EXT/***END/***LEB`) into plain dataclasses. New code — but the format itself is fully known, not guessed: it's exactly what `pyasm100/pass1.py`/`pass2.py` write, verified while porting the assembler. |
| `symtab.py` | Assigns each module a base PS address (sequential concatenation) and builds one cross-module symbol table, converting relocatable `$ENTRY`/`$SUBR` values to absolute addresses per a rule read directly out of `LED100.FTN`'s real entry-record reader. |
| `relocate.py` | `compute_val()` — the TYPEN 1-5 relocation formulas, ported from `LINKUP`/`DTAREL`. The one part of this package that's a direct port rather than new code. |
| `link.py` | Drives `symtab.py` + `relocate.py` across a whole module list: assign addresses, build the symbol table, relocate every code word, report every unresolved external up front. |
| `psmd.py` | Emits `asm2lm.py`'s PS/MD text formats. Also does the MD-side analog of `link.py` — `$COMMON` base-address assignment and `$DATA` relocation — since no real `.APO` file needs it done anywhere else. |
| `main.py` / `__main__.py` | CLI: `py -3.11 -m pyld100 ...`. |

## Known gaps

- **TYPEN 4** (subroutine-parameter reference via a callee's local data
  block) is FORTRAN/HASI parameter-passing plumbing. `relocate.py` raises
  `NotImplementedError` rather than guess at it — it's out of scope per
  the same HASI/host-FORTRAN deferral below.
- **Triple-type `$DATA`** (AP-internal `(exponent, hmant, value)` records)
  isn't converted to MD output. `asm2lm.py --vtype 4` expects a pre-packed
  IBM System/360 hex float, a different encoding with no grounded mapping
  found from the AP-internal one — `psmd.py` refuses rather than guess.
- **`$COMMON` base-address assignment** (`psmd.py`'s `assign_common_bases`,
  matching blocks by name across modules) is inferred by analogy to how
  `$ENTRY`/`$EXT` symbols are matched, not confirmed against real APLOAD
  source — `DTALNK`'s own table-building logic reads from the
  non-portable `DBLUN` scratch format (see "Where this comes from").
- **TYPEN 1 and 3** (self-relocation, DB/common reference) are implemented
  from the grounded `LINKUP`/`DTAREL` source but, like the `$COMMON` point
  above, unverified against real data.
- Explicitly out of scope, matching `pyasm100`'s and APLOAD's own
  boundaries: overlays, `$TASK`/`$ISR`, library search mode (treating an
  `.APO` file as a searchable archive rather than a plain object file),
  map file generation, HASI/host-FORTRAN load-module output.

## Testing

No real APLOAD output exists to diff a full link against, so verification
is layered:

- **`objfile.py`**: round-trips `APFLIB.APO` (34 modules) and
  `SYMLIB.APO` (66 modules) cleanly; `SYMLIB.APO`'s `!DIV` entry decodes
  to exactly `0o10000`, matching its `$EQU 10000` source.
- **`symtab.py` + `relocate.py`**: hand-built fixtures with addresses
  known by construction (address assignment, absolute-vs-relocatable
  entry values, PC-relative subtraction, duplicate-entry and
  unresolved-external detection), *and* a real end-to-end link of
  `APFLIB.APO` against `SYMLIB.APO` — every external resolves, `!DIV` →
  `0o10000`, `!SQRT` → `0o10202`, all 54 real `TYPEN 5` relocations in the
  corpus apply without error.
- **`link.py`**: linking `SYMLIB.APO` + `APFLIB.APO` produces 456
  contiguous PS words (`APFLIB.APO`'s exact total code-word count);
  dropping `SYMLIB.APO` correctly raises on the first missing external.
- **`psmd.py` + CLI**: the real-data path (PS) was run through the actual
  CLI and its output fed straight into the unmodified `asm2lm.py`,
  accepted without error. The `$COMMON`/`$DATA` path (MD), which no real
  file exercises, was checked with a hand-built fixture (mixed
  integer/relocated/real elements) resolving to the expected addresses
  and values, with both resulting MD texts likewise accepted by
  `asm2lm.py`.

`TYPEN 1`/`3`/`4` and the triple-`$DATA` path remain unverified against
real data — see "Known gaps." If a real linked reference (or a `.APO`
file with `$COMMON`/`$DATA`/self-relocation) ever turns up, diff against
it the same way `APFLIB.APO` validated `pyasm100`.
