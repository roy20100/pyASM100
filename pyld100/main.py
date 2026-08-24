"""CLI entry point for pyld100.

Usage:  py -3.11 -m pyld100 mod1.apo mod2.apo ... -o out [--origin N]

Links the given .APO files (in the order given) and writes out.ps
(always) plus out.md1 / out.md2 for any integer / real $DATA present
(triple-type $DATA isn't supported -- see psmd.py). Feed the results to
asm2lm.py separately, once per file:

    py asm2lm.py -p out.ps -o prog.lm
    py asm2lm.py -m out.md1 --vtype 1 -o data.lm   (if out.md1 exists)
    py asm2lm.py -m out.md2 --vtype 2 -o data.lm   (if out.md2 exists)
"""

from __future__ import annotations

import argparse
import sys

from .link import link
from .objfile import read_object_file
from .psmd import assign_common_bases, format_md, format_ps, relocate_data
from .symtab import LinkError


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        prog="pyld100", description="Link .APO object files into PS/MD text."
    )
    ap.add_argument("objfiles", nargs="+", metavar="FILE.APO")
    ap.add_argument("-o", "--output", required=True, metavar="STEM", help="output file stem")
    ap.add_argument("--origin", type=int, default=0, help="PS base address (default 0)")
    args = ap.parse_args(argv)

    modules = []
    for path in args.objfiles:
        try:
            modules.extend(read_object_file(path))
        except OSError as e:
            print(f"pyld100: {path}: {e}", file=sys.stderr)
            return 1
    print(f"read {len(modules)} module(s) from {len(args.objfiles)} file(s)")

    try:
        program = link(modules, origin=args.origin)
    except LinkError as e:
        print(f"pyld100: link failed:\n{e}", file=sys.stderr)
        return 1

    ps_path = f"{args.output}.ps"
    with open(ps_path, "w") as fh:
        fh.write(format_ps(program))
    print(f"wrote {ps_path}: {len(program.ps)} PS word(s)")

    has_data = any(m.data_records for m in modules)
    if has_data:
        common_bases = assign_common_bases(modules)
        try:
            entries = relocate_data(modules, program, common_bases)
        except (LinkError, NotImplementedError) as e:
            print(f"pyld100: MD linking failed: {e}", file=sys.stderr)
            return 1
        for vtype, ext in ((1, "md1"), (2, "md2")):
            text = format_md(entries, vtype)
            if not text:
                continue
            md_path = f"{args.output}.{ext}"
            with open(md_path, "w") as fh:
                fh.write(text)
            n = text.count("\n")
            print(f"wrote {md_path}: {n} MD location(s), --vtype {vtype}")
    else:
        print("no $COMMON/$DATA in input, no MD file written")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
