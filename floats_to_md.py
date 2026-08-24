#!/usr/bin/env python3
"""
floats_to_md.py -- turn a plain list of numbers into MD text.

Takes a file of bare numbers (no addresses -- one per line, comma- or
whitespace-separated, or a Python list literal like [1.0, 2.0, ...];
every numeric token in the file is picked up regardless of layout),
assigns them sequential addresses starting at --start, and writes one
"addr value" line per number: the same shape as a hand-written
asm2lm.py --vtype 2 MD file (see data.md) and what pyld100's own
psmd.py writes to stem.md2 -- so the result is ready for either
`py asm2lm.py -m out.md2 --vtype 2 ...` or
`py ps_md_to_c.py -m out.md2 --vtype 2 ...` unchanged.

Addresses are written in octal (no padding beyond what's needed),
matching asm2lm.py's `int(tok[0], 8)` address parser -- --start is given
in plain decimal for convenience and converted for you.

Usage:
    py floats_to_md.py floats.txt -o out.md2
    py floats_to_md.py floats.txt -o out.md2 --start 100
"""

from __future__ import annotations

import argparse
import re
import sys

_NUM = re.compile(r"[-+]?\d+\.?\d*(?:[eE][-+]?\d+)?")


def extract_floats(text: str) -> list[float]:
    return [float(m) for m in _NUM.findall(text)]


def main(argv=None):
    ap = argparse.ArgumentParser(description="Convert a plain list of numbers into asm2lm.py/pyld100-style MD text.")
    ap.add_argument("input", metavar="FILE", help="text file of numbers, any common layout")
    ap.add_argument("-o", "--output", required=True, metavar="FILE")
    ap.add_argument("--start", type=int, default=0, metavar="N",
                     help="starting address, decimal (default 0)")
    args = ap.parse_args(argv)

    with open(args.input) as fh:
        values = extract_floats(fh.read())
    if not values:
        ap.error(f"no numbers found in {args.input}")

    with open(args.output, "w") as fh:
        for i, v in enumerate(values):
            fh.write(f"{args.start + i:o} {v!r}\n")

    last = args.start + len(values) - 1
    print(f"wrote {args.output}: {len(values)} value(s), "
          f"addresses {args.start:o}..{last:o} (octal)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
