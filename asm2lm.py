#!/usr/bin/env python3
"""
asm2lm.py  --  Octal/decimal assembly listings to SIM100 load-module binary.

Produces a binary load-module in APLOAD format, exactly as the real AP-120B
APLOAD utility would produce.  No extensions.

────────────────────────────────────────────────────────────────────────────
PS FILE  (64-bit instruction words)

  Each line:  [addr]  w1  w2  w3  w4
  Four 16-bit octal words per line = one 64-bit PS instruction word.
  addr is the PS location (0-based octal).  If omitted, auto-increments.

────────────────────────────────────────────────────────────────────────────
MD FILE  (38-bit AP float words)

  Three modes, one per file; choose with --vtype:

  --vtype 1   Integer  (default)
              Each line:  [addr]  value
              value is a signed decimal integer (-32768 to 32767).
              Stored in the low 16 bits of the AP 38-bit word; exponent
              is forced to zero.  Same as the real VTYPE=1 DB Init record.

  --vtype 2   Real  (IEEE 32-bit float -> AP 38-bit via FPINPT)
              Each line:  [addr]  value
              value is a decimal float.  Converted through FPINPT, which
              does a full binary renormalization into the 28-bit two's-
              complement AP mantissa.  This is the maximum-precision path
              for arbitrary values.
              NOTE: the file stores an IEEE 32-bit float (24-bit mantissa);
              the AP has 28 bits.  The bottom 4 mantissa bits are recovered
              by FPINPT's renormalization but the source precision is still
              limited to what a 32-bit IEEE float can represent.

  --vtype 4   Triple  (IBM System/360 hex float passthrough)
              Each line:  [addr]  w1  w2
              Two 16-bit octal words = one 32-bit IBM hex float:
                w1 [15]    sign
                w1 [14:8]  7-bit base-16 exponent, bias 64
                w1 [7:0]   mantissa bits 23-16
                w2 [15:0]  mantissa bits 15-0
              Bit-routed directly into the AP 38-bit register with no
              arithmetic.  Only 4 of the 10 AP exponent bits are populated
              (the top nibble of the IBM exponent).  Designed for loading
              pre-computed IBM-format coefficient tables.

────────────────────────────────────────────────────────────────────────────
EXAMPLES

  PS source:
    ; addr   w1      w2      w3      w4
    000     000000  000000  000000  000000   ; NOP

  MD source, --vtype 2 (decimal float):
    ; addr   value
    000      1.0
    001     -1.0
    002      3.14159265358979
    003      0.70710678118655

  MD source, --vtype 4 (IBM hex, two octal words):
    ; addr   w1      w2
    000     041100  000000     ; +1.0  in IBM hex float
    001     141100  000000     ; -1.0
    002     040220  000000     ; +0.5

USAGE
-----
  python asm2lm.py [-p ps_file] [-m md_file] [-o out.lm]
                   [--vtype {1,2,4}] [-v]
"""

import argparse, struct, sys

# ---------------------------------------------------------------------------
# AP float conversion  (FPINPT logic)
# ---------------------------------------------------------------------------

def _fpinpt(decin):
    """Python float -> 6-byte AP-120B native float [REG1..REG6]."""
    reg = [0] * 6
    if decin == 0.0:
        return reg
    isg = 1 if decin < 0 else 0
    dec = abs(decin)
    iexp = 512
    while dec < 0.5:  dec *= 2.0;  iexp -= 1
    while dec >= 1.0: dec /= 2.0;  iexp += 1
    mant = [0] * 8
    for i in range(8):
        dec *= 256.0; v = int(dec); mant[i] = v & 0xFF; dec -= v
    # right-shift 1 to make room for sign/guard
    carry = 0
    for i in range(7, -1, -1):
        nc = mant[i] & 1; mant[i] = (mant[i] >> 1) | (carry << 7); carry = nc
    # two's complement negate if negative
    if isg:
        carry = 1
        for i in range(7, -1, -1):
            s = (mant[i] ^ 0xFF) + carry; mant[i] = s & 0xFF; carry = s >> 8
    # normalize: top two bits must be 01 or 10
    for _ in range(40):
        if (mant[0] >> 6) & 3 in (1, 2): break
        c = 0
        for i in range(7, -1, -1):
            nc = (mant[i] >> 7) & 1
            mant[i] = ((mant[i] << 1) | c) & 0xFF
            c = nc
        iexp -= 1
    # right-shift 4 to align 28-bit field (keep 4 guard bits below)
    c = 0
    for i in range(8):
        nc = mant[i] & 0xF; mant[i] = (mant[i] >> 4) | (c << 4); c = nc
    reg[0] = (iexp >> 8) & 0xFF;  reg[1] = iexp & 0xFF
    reg[2] = mant[0]; reg[3] = mant[1]; reg[4] = mant[2]; reg[5] = mant[3]
    return reg

# ---------------------------------------------------------------------------
# Binary record helpers
# ---------------------------------------------------------------------------

_REC = struct.Struct('<8h')

def _s16(v):
    v = int(v) & 0xFFFF
    return v - 65536 if v >= 32768 else v

def _pack(*words):
    w = [_s16(x) for x in words] + [0] * 8
    return _REC.pack(*w[:8])

def _hdr(rtype, count, addr, page=0, dest=0):
    return _pack(rtype, count, addr, page, dest)

# ---------------------------------------------------------------------------
# Source parsers
# ---------------------------------------------------------------------------

def _strip(line):
    if ';' in line:
        line = line[:line.index(';')]
    return line.strip()

def _runs(entries):
    if not entries: return []
    runs, cur = [], [entries[0]]
    for e in entries[1:]:
        if e[0] == cur[-1][0] + 1: cur.append(e)
        else: runs.append(cur); cur = [e]
    runs.append(cur)
    return runs

def parse_ps(path):
    """PS: each line -> (addr, [w0,w1,w2,w3])."""
    out, nxt = [], 0
    with open(path) as fh:
        for n, raw in enumerate(fh, 1):
            line = _strip(raw)
            if not line: continue
            tok = line.split()
            addr = None
            if len(tok) >= 5:
                try: addr = int(tok[0], 8); tok = tok[1:5]
                except ValueError: tok = tok[:4]
            else:
                tok = tok[:4]
            if len(tok) < 4: continue
            try: words = [int(t, 8) & 0xFFFF for t in tok]
            except ValueError as e:
                print(f"  {path}:{n}: {e}", file=sys.stderr); continue
            if addr is None: addr = nxt
            out.append((addr, words)); nxt = addr + 1
    return out

def parse_md_vtype1(path):
    """VTYPE=1 integer: each line -> (addr, int16)."""
    out, nxt = [], 0
    with open(path) as fh:
        for n, raw in enumerate(fh, 1):
            line = _strip(raw)
            if not line: continue
            tok = line.split()
            addr = None
            if len(tok) >= 2:
                try: addr = int(tok[0], 8); tok = tok[1:2]
                except ValueError: tok = tok[:1]
            else:
                tok = tok[:1]
            if not tok: continue
            try: val = int(tok[0])
            except ValueError as e:
                print(f"  {path}:{n}: {e}", file=sys.stderr); continue
            if addr is None: addr = nxt
            out.append((addr, val & 0xFFFF)); nxt = addr + 1
    return out

def parse_md_vtype2(path):
    """VTYPE=2 real: each line -> (addr, float)."""
    out, nxt = [], 0
    with open(path) as fh:
        for n, raw in enumerate(fh, 1):
            line = _strip(raw)
            if not line: continue
            tok = line.split()
            addr = None
            if len(tok) >= 2:
                try: addr = int(tok[0], 8); tok = tok[1:2]
                except ValueError: tok = tok[:1]
            else:
                tok = tok[:1]
            if not tok: continue
            try: val = float(tok[0])
            except ValueError as e:
                print(f"  {path}:{n}: {e}", file=sys.stderr); continue
            if addr is None: addr = nxt
            out.append((addr, val)); nxt = addr + 1
    return out

def parse_md_vtype4(path):
    """VTYPE=4 triple (IBM hex): each line -> (addr, [w1,w2])."""
    out, nxt = [], 0
    with open(path) as fh:
        for n, raw in enumerate(fh, 1):
            line = _strip(raw)
            if not line: continue
            tok = line.split()
            addr = None
            if len(tok) >= 3:
                try: addr = int(tok[0], 8); tok = tok[1:3]
                except ValueError: tok = tok[:2]
            else:
                tok = tok[:2]
            if len(tok) < 2: continue
            try: words = [int(t, 8) & 0xFFFF for t in tok]
            except ValueError as e:
                print(f"  {path}:{n}: {e}", file=sys.stderr); continue
            if addr is None: addr = nxt
            out.append((addr, words)); nxt = addr + 1
    return out

# ---------------------------------------------------------------------------
# Block builders
# ---------------------------------------------------------------------------

def build_ps_block(entries, verbose=False):
    if not entries: return b''
    out = bytearray()
    for run in _runs(entries):
        start   = run[0][0]
        payload = [w for _, words in run for w in words]
        out += _hdr(0, len(payload), start, dest=0)
        for i in range(0, len(payload), 8):
            out += _pack(*payload[i:i+8])
        if verbose:
            print(f"  PS: {oct(start)}-{oct(start+len(run)-1)} ({len(run)} locs)")
    return bytes(out)

def build_md_vtype1(entries, verbose=False):
    """VTYPE=1: one DB Init sub-record per location, integer."""
    if not entries: return b''
    out = bytearray()
    for run in _runs(entries):
        start = run[0][0]
        out += _hdr(1, len(run), start)
        for addr, val in run:
            # W1=VTYPE=1, W2=rept=1, W3=addr, W4=0, W5=0, W6=0, W7=val, W8=0
            # LODINP integer path: UNPKRG(BUF(5), REG(5)) -- BUF is 1-indexed
            # BUF(5) in the 8-word sub-record = word index 4 (0-based)
            out += _pack(1, 1, addr, 0, val, 0, 0, 0)
        if verbose:
            print(f"  MD VTYPE=1: {oct(start)}-{oct(start+len(run)-1)} ({len(run)} locs)")
    return bytes(out)

def build_md_vtype2(entries, verbose=False):
    """VTYPE=2: one DB Init sub-record per location, IEEE 32-bit float.
    The float is packed as two little-endian 16-bit words in W5:W6.
    LODINP reads them via EQUIVALENCE as SPFPN(1) and calls FPINPT.
    Precision note: IEEE 32-bit has 24-bit mantissa; AP has 28.  The
    bottom 4 bits are reconstructed by FPINPT's normalization but the
    input precision is limited to what 32-bit IEEE can represent.
    """
    if not entries: return b''
    out = bytearray()
    for run in _runs(entries):
        start = run[0][0]
        out += _hdr(1, len(run), start)
        for addr, fval in run:
            fb = struct.pack('<f', fval)
            w5 = struct.unpack('<H', fb[0:2])[0]   # low word
            w6 = struct.unpack('<H', fb[2:4])[0]   # high word
            out += _pack(2, 1, addr, 0, w5, w6, 0, 0)
        if verbose:
            print(f"  MD VTYPE=2: {oct(start)}-{oct(start+len(run)-1)} ({len(run)} locs)")
    return bytes(out)

def build_md_vtype4(entries, verbose=False):
    """VTYPE=4: triple / IBM hex float passthrough.
    Two octal words per entry (w1=IBM high word, w2=IBM low word).
    LODINP decoder:
      REG[2]   = W6[15:12]          (4 bits, top nibble of IBM exp+sign)
      REG[3]   = W6[11:8]           (4 bits, low nibble of IBM exp)
      REG[4]   = W6[7:0]            (8 bits, IBM mantissa bits 23-16)
      REG[5]   = W7[15:8]           (8 bits, IBM mantissa bits 15-8)
      REG[6]   = W7[7:0]            (8 bits, IBM mantissa bits 7-0)
      REG[1]   = 0
    W6 in the sub-record = BUF(6) = word index 5 (0-based) = our w1.
    W7 in the sub-record = BUF(7) = word index 6 (0-based) = our w2.
    """
    if not entries: return b''
    out = bytearray()
    for run in _runs(entries):
        start = run[0][0]
        out += _hdr(1, len(run), start)
        for addr, (w1, w2) in run:
            # Sub-record: W1=4, W2=1, W3=addr, W4=0, W5=0, W6=w1, W7=w2, W8=0
            out += _pack(4, 1, addr, 0, 0, w1, w2, 0)
        if verbose:
            print(f"  MD VTYPE=4: {oct(start)}-{oct(start+len(run)-1)} ({len(run)} locs)")
    return bytes(out)

# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    ap = argparse.ArgumentParser(
        description="Convert assembly listings to SIM100 APLOAD load-module.",
        formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('-p', '--ps',     metavar='FILE', help='PS source (4 octal words/line)')
    ap.add_argument('-m', '--md',     metavar='FILE', help='MD source')
    ap.add_argument('-o', '--output', metavar='FILE', default='out.lm')
    ap.add_argument('--vtype', metavar='N', type=int, choices=[1, 2, 4], default=2,
                    help='MD encoding: 1=integer, 2=real (default), 4=IBM hex triple')
    ap.add_argument('-v', '--verbose', action='store_true')
    args = ap.parse_args()

    if not args.ps and not args.md:
        ap.error("Need at least one of -p (PS) or -m (MD).")

    body = bytearray()

    if args.ps:
        entries = parse_ps(args.ps)
        if args.verbose:
            print(f"PS: {len(entries)} instruction words from {args.ps}")
        body += build_ps_block(entries, verbose=args.verbose)

    if args.md:
        if args.vtype == 1:
            entries = parse_md_vtype1(args.md)
            body   += build_md_vtype1(entries, verbose=args.verbose)
        elif args.vtype == 2:
            entries = parse_md_vtype2(args.md)
            body   += build_md_vtype2(entries, verbose=args.verbose)
        elif args.vtype == 4:
            entries = parse_md_vtype4(args.md)
            body   += build_md_vtype4(entries, verbose=args.verbose)
        if args.verbose:
            print(f"MD: {len(entries)} locations from {args.md} (VTYPE={args.vtype})")

    # End record: TYPE=3, W2=1 (close file, restore MAE)
    body += _pack(3, 1, 0, 0, 0, 0, 0, 0)

    with open(args.output, 'wb') as fh:
        fh.write(body)

    n = len(body) // 16
    print(f"{args.output}: {len(body)} bytes ({n} records)")

if __name__ == '__main__':
    main()
