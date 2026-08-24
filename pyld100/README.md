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

`APLOAD` doesn't exist as its own file. Of `LED100.FTN`'s 43 named
subroutines, 40 turned out to be `APLOAD` code, misfiled under the
unrelated Library Editor's name — identifiable because each one's own
header comment says which program it's really from ("THIS VERSION OF
**APLOAD** WAS PRODUCED BY CROCK...", vs. "...OF **APLED**..." for the 2
genuine Library Editor routines actually in there). A 43rd banner,
`PAKSTR`, is a bare comment line with no header and no body at all — one
routine name that didn't survive whatever produced this archive, sitting
right next to 42 that did.

That recovered source is real, but still not cleanly portable as a whole:

- Its core loader (`LOAD1`, ~940 lines) has overlay/task/ISR handling
  woven directly into its control flow, not separable from plain linking.
- Its data-relocation path (`DTALNK`/`DTAREL`) reads APLOAD's own internal
  scratch-file format (`DBLUN`), not the `.APO` format directly.
- There's no real APLOAD output anywhere to diff a full port against —
  unlike `pyasm100`, which was verified byte-for-byte against a real
  reference object file.
- It also constantly calls a couple dozen small string/table utilities
  (`EXTTOK`, `STOI`, `SRCST`, `EXTVT`, `EXTST`, `INSST`, `RPLVT`, `RMVET`,
  `LENT`, `INSCS`, `EXTSS`, `RPLIS`, `RMVCS`, `INTT`, `CMPSS`, `IADDC`,
  `RPLST`, `SRCCS`, and a few more) that are defined nowhere in
  `LED100.FTN` itself. A later, separately-acquired archive of found FPS
  source (large — kept outside this repo, see `.gitignore`) turned out to
  contain them after all: they're real, complete routines in that
  archive's `IUTIL.FTN` ("INDEPENDENT UTILITIES" — a self-described
  generic string/table library, not APLOAD-specific, shared across
  several of the tools in that archive). Only 4 names LED100.FTN calls —
  `TABGET`, `UPAKS`, `WRTLIN`, `RDLIN` — stayed unaccounted for even
  there; the last two turned out to be called by `IUTIL.FTN` itself
  without being defined in it either, so they're missing from a layer
  below IUTIL, not specific to APLOAD.

So `pyld100` reuses only what's directly grounded and independently
checkable: the relocation-address (`VAL`) formulas from `LINKUP` (code
words, `LED100.FTN` ~2668-2810) and `DTAREL` (data records, ~992-1097),
reproduced in `relocate.py`. Note that even that reused logic isn't a
literal, complete transcription: the real `VAL` computation calls
`EXTST`/`SRCST`/`EXTVT` to look an external symbol's value up by name in
APLOAD's own in-memory tables. `relocate.py` ports the *arithmetic and
branch structure* around those calls (which TYPEN does what, the RELTYP
bitmask, the PC-relative subtraction) but not the calls themselves —
`symtab.py` does that lookup with a plain Python `dict` instead, the same
way `pyasm100` reimplemented `INFILE`/`DATTIM` from their contract rather
than their body. Everything else here — the `.APO` reader, the symbol
table, link orchestration, PS/MD emission, the CLI — is new code, because
the equivalent APLOAD pieces are either missing, tangled up with
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
