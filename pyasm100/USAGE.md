# pyasm100 usage guide

A practical reference for writing APAL source and running `pyasm100`.
For the port's internal architecture, module map, and known gaps, see
the [root README](../README.md); this document is about the assembler's
*user-facing* behavior, extracted from `pass1.py`/`pass2.py`'s pseudo-op
dispatch tables and the 45-entry error-message table in `sndmes.py`.

## Running it

```
py -3.11 -m pyasm100
```

It's interactive and asks four or five questions in order:

```
source file =
object file =
listing file =
listing (y/n) =
listing radix =        (only asked if you said y; 8, 10, or 16)
```

The source file is read from disk; the object file is `pyasm100`'s
`.APO` text format (see [`pyld100/README.md`](../pyld100/README.md) for
its grammar — it's what `pyld100` links); the listing file gets a
formatted source echo plus any error messages, paginated with a running
header every 54 lines.

## Source line format

- **Comments**: introduced by `"` — everything from `"` to end of line is
  discarded.
- **Statement separators**: `;` and `,` both end a statement; multiple
  statements can share a line.
- **Tabs** are converted to blanks; leading blanks are stripped.
- **Labels**: a symbol immediately followed by `:` at the start of a
  statement.
- **Symbols**: up to 6 characters, from whatever the source's character
  set allows (packed 2-per-word for table lookup — see the "Hollerith
  byte order" note in the root README if you're ever comparing packed
  values directly).
- **Break characters** (terminate a symbol or number token): blank,
  `+ - * / . $ = ( ) < ; , : " # & % ' > @ !`, plus the radix suffix
  letters below.

## Number literals

A numeral takes an optional trailing radix suffix; without one, the
current `$RADIX` setting applies:

| Suffix | Radix |
|---|---|
| `K` | octal |
| `X` | hex |
| `.` | decimal |
| `B` | binary — **effectively dead**: the digit scanner already consumes `B` as a valid hex digit (11) before it gets a chance to act as a radix suffix, an original ASM100.FTN quirk preserved as-is (see `gnum.py`) |

`$RADIX <8|10|16>` changes the default for suffix-less numerals for the
rest of the module.

## Pseudo-ops

All take a `$` prefix except `&LIB`/`&ENDLIB`, which use `&` instead (a
distinct, library-mode-only pair recognized before normal statement
parsing even begins — see `pass1.py`'s `&LIB`/`&ENDLIB` handling).

| Pseudo-op | What it does |
|---|---|
| `$TITLE name` | Names the module; starts a new `.APO` module block. Must appear before most other pseudo-ops (ordering is enforced). |
| `$ENTRY name,value[,n]` | Declares a relocatable, FORTRAN/HASI-callable entry point at `value`. With a 0-15 `,n`, it's an S-PAD-parameter entry (`***AENTRY` in the object file). |
| `$SUBR name,value` | Declares a relocatable subroutine entry point, like `$ENTRY` but always the plain (non-S-PAD) form. |
| `$GLOBAL name,value` | Declares a fixed, **absolute** address for `name` — not relocated at link time. This is how `SYMLIB.APO`'s constants (`!DIV`, `!PI`, ...) are defined. |
| `$VAL v1[,v2[,v3]]` | Writes up to 3 raw values directly into the current instruction word's fields, bypassing normal field assembly. |
| `$EQU value` (or `name = value`) | Assigns `value` to the preceding label's symbol-table entry. |
| `$LOC value` | Sets the location counter — where the next code word is placed. Flushes the code block assembled so far. |
| `$FP value` | Emits a floating-point literal, converted via the FPGET/RTOE machinery (see `fpget.py`/`rtoe.py`). |
| `$END` | Ends the current module, flushing final tables and switching to the next `$TITLE` (or end of file). |
| `$EXT name[,name...]` | Declares external symbol references this module needs resolved at link time. |
| `$INTEGER`/`$REAL`/`$TRIPLE name[,name...]` | Declares a list of symbols as integer/real/triple type — structurally the same mechanism as `$EXT` above (`pass1.py` routes all four through one shared handler, distinguished only by a type tag), so most likely a way to pre-declare `$COMMON` members' types outside the `$COMMON` line itself, as an alternative to the inline `/I`/`/R`/`/T` suffix below. Not independently verified by assembly, unlike `$COMMON`/`$DATA`. |
| `$INSERT` | Switches to reading from an inserted/included secondary input stream. |
| `$IF expr` / `$ENDIF` | Conditional assembly: if `expr` evaluates to 0, everything up to the matching `$ENDIF` is skipped. |
| `$BOX` / `$ENDBOX` | Brackets a region skipped on some condition (box/skip-scan region — see `pass1.py`'s box handling for the exact trigger). |
| `&LIB` / `&ENDLIB` | Brackets a whole file as a library (`.APO` gets a `***LSB`/`***LEB` marker pair instead of per-module `***END`s) — this is the format `APFLIB.APO`/`SYMLIB.APO` use. |
| `$RADIX n` | Sets the default numeral radix (8, 10, or 16) for suffix-less numbers, for the rest of the module. |
| `$PAGE` | Forces a page break in the listing. |
| `$LIST` / `$NOLIST` | Turns listing output on/off for the following lines. |
| `$COMMON /name/ sym[(count)][/I\|R\|T][,sym2...]` | Declares/opens a named data block (`***DBDB` in the object file) — the AP-side shared-data area `pyld100`'s `TYPEN 3` relocation resolves. Each member gets an optional element count in `(...)` and an optional one-letter type — `I` integer (default), `R` real, `T` triple — after a `/`. Bare `$COMMON` (no `/name/`) opens the anonymous `.BLANK` block. Confirmed by actually assembling `$COMMON /MYBLK/ SYM1/R,SYM2/I` (0 errors) — see the worked example below. |
| `$DATA sym[(index)][/count] value[,sym2 value2...]` | Emits initialized data elements (`***DBIB`) for members of the currently open `$COMMON` block, referenced **by name**, in whatever type that member was declared with — *not* a bare positional value list (an earlier version of this table guessed wrong; confirmed by actually assembling `$DATA SYM1 1.5,SYM2 -2` against the block above, 0 errors). `sym(index)` addresses one element of a multi-element (table) member, **1-based** (`(1)` is the first element — confirmed empirically: `(0)` assembles but resolves to index `-1`, an off-by-one FORTRAN-style convention baked into `pass1.py`'s handling, not a bug to route around). A `/count` after that repeats the *same* value at `count` consecutive elements in one statement — e.g. `$DATA TABLE(1)/5 0.0` zero-fills a 5-element table — confirmed by assembling it and linking the result through `pyld100`, which expands the repeat count into that many separate MD locations (its own real bug, found and fixed the same way — see git history). There's no syntax for a compact list of *different* values in one statement; each distinct value needs its own `sym(index) value` pair. |
| `$COMIO` | Declares a `$COMMON` block as connected to host I/O (from the name — exact host-side contract not independently verified; see the root README's "no independent oracle" note). |
| `$PARAM` | Declares a formal parameter for a HASI-callable entry (from the name and its relation to `pyld100`'s unimplemented `TYPEN 4`; see `pyld100/relocate.py`'s docstring — not independently verified). |
| `$CALL` | Source-level call declaration (distinct from `LOD100`'s own link-time `CALL` command, which generates the HASI stub — see `pyld100/README.md`'s "Where this comes from" section). Exact contract not independently verified. |
| `$TASK` / `$ISR` | Task/interrupt-service-routine declarations. Recognized (an ordering check runs) but otherwise out of scope for this port, same as for `pyld100` — see both READMEs' "known gaps." |

The last four rows are flagged because, unlike the pseudo-ops this whole
project's assembler and linker were validated against real `.APO` output
for, nothing in the available test corpus (`APFSRC.APS`/`APFLIB.APO`,
`SYMSRC.APS`/`SYMLIB.APO`) actually exercises them.

## Instructions

The full instruction set is a 231-entry mnemonic table (`optab.py`,
mechanically extracted from `ASM100.FTN`'s own `OPTAB` `DATA`
statements) — too large to usefully reproduce here, but it follows
regular families you'll recognize quickly from the mnemonics:

- **Arithmetic/logic**: `ADD`, `SUB`, `MOV`, `AND`, `OR`, `EQV`, each with
  `L`/`R`/`RR` suffix variants selecting which S-PAD/data-pad the
  operation reads from and writes to.
- **Clear/increment/decrement**: `CLR`, `INC`, `DEC`, same suffix
  pattern.
- **Write/transfer**: `WRTEXP`, `WRTHMN`, `WRTLMN` and similar.

For the authoritative mnemonic-to-bit-pattern mapping, either read
`optab.py` directly or assemble something and read the listing — every
recognized opcode round-trips through the same table both ways.

## Errors and warnings

Every message follows `** <text> (nn) ON LINE nnnn`, where the leading
letter is a category: `W`=warning, `C`=conflict, `M`=missing, `O`=out of
range, `B`=bad statement. Up to 12 errors are recorded per line; a 13th
on the same line is silently dropped (`errmes.py`).

| # | Message |
|---|---|
| 1 | LINE BUFFER OVERFLOW |
| 2 | MULTIPLY DEFINED SYMBOL |
| 3 | CONFLICTING OP-CODES |
| 4 | S-PAD ADDRESS OUT OF RANGE |
| 5 | BRANCH ADDRESS OUT OF RANGE |
| 6 | CONFLICTING BRANCH ADDRESS |
| 7 | MISSING BRANCH ADDRESS |
| 8 | CONFLICTING DATA PAD INDEXES |
| 9 | BAD OR MISSING EXPRESSION |
| 10 | BAD FADD ARGUMENT |
| 11 | BAD FMUL ARGUMENT |
| 12 | MISSING FADD OR FMUL ARGUMENT |
| 13 | VALUE FIELD CONFLICT |
| 14 | MISSING DATA PAD INDEX |
| 15 | UNDEFINED OP-CODE |
| 16 | $EXT SYMBOL IN EXPRESSION |
| 17 | UNDEFINED USER SYMBOL |
| 18 | INTEGER OVERFLOW |
| 19 | BAD OPTION - DEFAULT VALUE USED |
| 20 | UNRECOGNIZED STATEMENT |
| 21 | IMPROPER $LOC VALUE |
| 22 | BAD COMMON STATEMENT |
| 23 | MISSING $END |
| 24 | DATA PAD INDEX OUT OF RANGE |
| 25 | BAD DATA STATEMENT |
| 26 | BAD DATA PAD INDEX EXPR |
| 27 | COMMA MISSING |
| 28 | NUMBER TOO LARGE, TRUNCATED |
| 29 | MISSING SEP AFTER D.P. INDEX |
| 30 | EXTRANEOUS BROUHAHA |
| 31 | BAD FLOATING POINT CONSTANT |
| 32 | ILLEGAL PSEUDO-OP POSITION |
| 33 | ENTRY SYMBOL NOT LOCAL |
| 34 | BAD PARAMETER |
| 35 | UNDEFINED ENTRY SYMBOL |
| 36 | DATA PAD BUS CONFLICT |
| 37 | MISSING S-PAD ADDRESS |
| 38 | MISSING PROGRAM SOURCE ADDRESS |
| 39 | XW/YW CONFLICT |
| 40 | UNRECOGNIZED PSEUDO OP |
| 41 | SYMBOL TABLE OVERFLOW |
| 42 | COMIO STATEMENT OUT OF ORDER OR ILL-FORMATTED |
| 43 | BAD PARAM STATEMENT |
| 44 | SUBROUTINE NAME MUST BE DECLARED EXTERNAL |
| 45 | BAD OR MISSING SYMBOL STRING |

(Message 4 is the one an inverted range check used to misfire on 34
times when this port first assembled a real 2386-line library — see the
root README's testing section. If you see a wall of identical errors,
suspect the assembler before the source.)

## A minimal worked example

S-PAD operand names like `BA` below aren't built-in register mnemonics —
every real source file (including `APFSRC.APS`) defines its own via
`$EQU` first, same as here:

```
$TITLE DEMO
$ENTRY START,0
BA     $EQU 0
START: NOP
       MOV  BA,BA
$END
```

Assemble it (verified against this exact source — 0 errors):

```
py -3.11 -m pyasm100
source file = demo.s
object file = demo.apo
listing file = demo.lst
listing (y/n) = y
listing radix = 8
```

`demo.apo` will contain a single `***TITLE`/`***AENTRY`/`***CODE`/`***END`
module — feed it to `pyld100` to link, or diff it against a known-good
`.APO` the way `APFLIB.APO` validated the whole pipeline.

Note: keep your file paths short. `INFILE`'s reimplementation (see the
root README) inherited RSX-11's small fixed-width filename buffers, so a
long path (e.g. deep in a temp directory) gets silently rejected and the
prompt just repeats instead of erroring clearly — run from a directory
close to the file, or use short relative paths.

## A $COMMON/$DATA example

`$COMMON`/`$DATA` (verified the same way — actually assembled, 0 errors,
then linked with `pyld100` and converted with `ps_md_to_c.py`):

```
$TITLE DEMO3
$COMMON /MYBLK/ SYM1/R,SYM2/I
$DATA SYM1 1.5,SYM2 -2
$END
```

This produces one `***DBDB` block (`MYBLK`, one real element and one
integer element) and two `***DBIB` records. Link it —

```
py -3.11 -m pyld100 demo3.apo -o demo3linked
```

— and, since the module has no code, `pyld100` writes an empty
`demo3linked.ps` plus `demo3linked.md1` (`SYM2`'s integer, `-2`) and
`demo3linked.md2` (`SYM1`'s real, RTOE-normalized text). Convert either
to a C header with `ps_md_to_c.py`; `--vtype 2` output is 3
`uint16_t` words per value (the AP-120B's own native exponent/high-
mantissa/low-mantissa float, not a C `double` — see that script's own
docstring) so it can be DMA'd straight into AP memory.
