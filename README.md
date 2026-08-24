# pyasm100

A near-1:1 Python port of `ASM100.FTN`, the RSX-11 FORTRAN cross-assembler
for the Floating Point Systems FPS-100, ported to run under `py -3.11` with
one module per original FORTRAN subroutine/function.

## Running it

```
py -3.11 -m pyasm100
```

It's interactive, same as the original: it asks for a source file, an
object (binary) output file, a listing/error file, whether you want a
listing, and (if so) what radix to list in.

## Module map

Every `C+++ NAME` banner in `ASM100.FTN` has a matching lowercase module
here:

| FORTRAN | Python | FORTRAN | Python |
|---|---|---|---|
| MAIN | `main.py` | GLINE | `gline.py` |
| APALI | `apali.py` | GNUM | `gnum.py` |
| PASS1 | `pass1.py` | GSYM | `gsym.py` |
| PASS2 | `pass2.py` | GBRK | `gbrk.py` |
| TABLES | `tables.py` | GVAL | `gval.py` |
| OPTAB | `optab.py` | FLOAT2 | `float2.py` |
| ERRMES | `errmes.py` | PNUM | `pnum.py` |
| FPGET | `fpget.py` | ITAS | `itas.py` |
| RTOE | `rtoe.py` | SNDMES | `sndmes.py` |
| TYPCHR | `typchr.py` | WLIN | `wlin.py` |
| FSYM | `fsym.py` | HEADER | `header.py` |
| FUSYM | `fusym.py` | EXFLDS | `exflds.py` |
| GARG | `garg.py` | LENGTH | `length.py` |
| GFIELD | `gfield.py` | READLN | `readln.py` |
| PACKS | `packs.py` | | |

Runtime layer (no FORTRAN equivalent — see each module's docstring for why
it exists):

- `farray.py` — `FArray`, a 1-based (optionally multi-dimensional,
  column-major) array so ported code indexes exactly as the source does.
- `hollerith.py` — packs/unpacks `nH` Hollerith literals and `Aw`-format
  character data (see "Hollerith byte order" below).
- `bitops.py` — the six ADUTIL.MAC 16-bit intrinsics ASM100.FTN actually
  calls (`IOR16`, `IAND16`, `INOT16`, `IADD16`, `IRSH16`, `ILSH16`, plus
  `IP16`).
- `arith.py` — `fdiv` (FORTRAN truncating INTEGER division) and a handful
  of undocumented 16-bit host primitives (`NEGCHK`, `INEG16`, `ISUB16`,
  `ICMP16`, `IPFIX`, `PFLOAT`) that GVAL/FLOAT2 call but no source for was
  ever provided — semantics inferred from call sites.
- `box.py` — `Box`, a mutable container standing in for FORTRAN's
  by-reference scalar output parameters.
- `common.py` — the `G` singleton holding COMMON `/GEN/`, `/SYM/`, and
  `/EXPRST/` exactly as declared in the source.
- `fio.py` — logical-unit file registry (open/close/rewind/scratch,
  matching the `INFILE` mode codes inferred from every call site), a
  FORTRAN `FORMAT` interpreter, and `DATTIM`.

## The "block trampoline"

ASM100.FTN is dense with GOTO, computed GOTO, and three-way arithmetic IF.
Rather than restructure that into "normal" Python control flow by hand —
risky for logic this size — the denser subroutines (`gval.py`, `fpget.py`,
`rtoe.py`, `gfield.py`, `pass1.py`, `pass2.py`) are ported as a "block
trampoline": one small Python function per FORTRAN statement label, each
returning the next block (or `None` for `RETURN`), driven by a tiny loop
at the bottom (`blk = l100; while blk: blk = blk()`). This keeps a
near-exact structural correspondence to the original — one label, one
block, easy to diff against the source — without needing a real `goto`.
Simpler subroutines with no real GOTO-formed loops are just plain
structured Python.

## Assumptions and known gaps

- **Hollerith byte order**: a `2H` literal (or an `Aw` field with `w<`
  storage width) packs the first character into the **low** byte and the
  second into the **high** byte. This isn't documented anywhere in the
  source; it's pinned down by PACKS (`packs.py`), which packs run-time
  characters into words that must compare equal to the `2H`-packed OPSYM
  table for opcode lookup to work at all. Confirmed correct empirically —
  a real source line packed via PACKS and looked up via FSYM finds its
  opcode.
- **`INFILE`, `DATTIM`**: RSX-11-specific routines with no source provided
  anywhere (APALI's own comments call `INFILE` host-dependent). Their mode
  codes/contract were inferred from every call site and reimplemented
  natively in `fio.py` against the real filesystem.
- **LUN "+7" mapping**: the source addresses the same physical file under
  two different logical-unit numbers at different points (opened under a
  small raw number, then +7 for every subsequent READ/WRITE, then -7
  again for rewinds) — RSX-11 channel-mapping scaffolding with no meaning
  for a Python file registry. `fio.py`'s `IoUnits` normalizes `lun >= 8`
  down by 7 so both numbers resolve to the same file.
- **Undocumented 16-bit primitives**: `NEGCHK`, `INEG16`, `ISUB16`,
  `ICMP16`, `IPFIX`, `PFLOAT` are named in GVAL's/FLOAT2's "ROUTINES USED"
  comments but defined nowhere in the provided sources — same situation as
  `INFILE`. Reimplemented in `arith.py` from call-site behavior.
- **No independent oracle**: there's no real RSX-11/FPS-100 system to diff
  binary output against, so correctness was verified by (a) exact
  transcription discipline, (b) hand-tracing the trickiest control flow
  step by step against the source, (c) relative/structural checks where a
  direct answer wasn't available (e.g. FPGET's packed exponent field for
  `2.0` is exactly `1.0`'s + 1; RTOE's `significand * 10^exponent`
  reconstructs the original value exactly), and (d) end-to-end runs
  through real APAL source producing well-formed, internally-consistent
  object and listing output.
- **Two documented (not "fixed") original quirks**: GNUM's binary-radix
  suffix `B` is effectively dead code (the digit scanner consumes it as
  hex digit 11 first); PASS2's pseudo-op dispatch falls through to the
  `$LOC` handler on an unmatched index with no explicit error branch
  (should be unreachable since PASS1 already validates). Both preserved
  as-is — see `gnum.py` and `pass2.py`.
- Out of scope: `APCOM.FTN`, `ADUTIL.MAC` (beyond the handful of routines
  actually called), and `SIM100.FTN` (the FPS-100 simulator) — none of
  their routines are called from `ASM100.FTN`.

## Testing

Every module was verified individually as it was ported (see the git
history for what was checked). The full pipeline has been run end-to-end
through the real `py -3.11 -m pyasm100` entry point against small
hand-written APAL source. It has not yet been run against a large,
real-world APAL program.
