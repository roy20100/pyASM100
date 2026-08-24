"""I/O runtime: logical-unit file management and a FORTRAN FORMAT interpreter.

ASM100.FTN talks to the outside world three ways, all reimplemented here:

- ``INFILE(mode, namearr, lun)`` -- the RSX-11 file-assign/close/delete/
  rewind dispatcher. No source for it was provided (comments in APALI call
  it host-dependent); its mode codes were inferred from every call site in
  ASM100.FTN: 1=open existing for read, 2=create/open for write, 4=close,
  5=close+delete, 6=rewind, 7=create a scratch temp file.
- ``DATTIM(times)`` -- fills the 10-element ``TIMES`` array with the current
  date/time as individual digits. The digit layout (MMDDYYHHMM, one digit
  per element) is pinned down by how HEADER's FORMAT 200 consumes it
  (``2I1,'/',2I1,'/',2I1,...,2I1,':',2I1``).
- FORTRAN formatted READ/WRITE, via ``fread``/``fwrite`` plus a small
  FORMAT-string parser covering exactly the edit descriptors ASM100.FTN
  uses: ``Iw``, ``Aw`` (w is 1 or 2 -- 1 means one raw ASCII code per
  array element, 2 means a Hollerith-packed pair, matching how the source
  itself distinguishes A1 character arrays from A2 Hollerith arrays),
  ``nX``, ``nHtext``, ``'text'``, ``/``, and parenthesized repeat groups.

Console unit 5 (ITTI/ITTO in the source) is special-cased to Python's
stdin/stdout so the tool's interactive prompts behave the same as the
original terminal session.
"""

from __future__ import annotations

import datetime
import os
import tempfile

from .farray import FArray
from .hollerith import holl, unholl

CONSOLE_LUN = 5


# ---------------------------------------------------------------------------
# Logical unit registry
# ---------------------------------------------------------------------------


class IoUnits:
    def __init__(self):
        self._files: dict[int, object] = {}
        self._paths: dict[int, str] = {}

    def open_read(self, lun: int, path: str) -> bool:
        try:
            f = open(path, "r", newline="")
        except OSError:
            return False
        self._files[lun] = f
        self._paths[lun] = path
        return True

    def open_write(self, lun: int, path: str) -> bool:
        try:
            f = open(path, "w", newline="")
        except OSError:
            return False
        self._files[lun] = f
        self._paths[lun] = path
        return True

    def open_scratch(self, lun: int) -> bool:
        f = tempfile.NamedTemporaryFile(
            mode="w+", newline="", suffix=".tmp", delete=False
        )
        self._files[lun] = f
        self._paths[lun] = f.name
        return True

    def close(self, lun: int) -> None:
        f = self._files.pop(lun, None)
        self._paths.pop(lun, None)
        if f is not None:
            f.close()

    def close_delete(self, lun: int) -> None:
        path = self._paths.pop(lun, None)
        f = self._files.pop(lun, None)
        if f is not None:
            f.close()
        if path and os.path.exists(path):
            os.remove(path)

    def rewind(self, lun: int) -> None:
        f = self._files.get(lun)
        if f is not None:
            f.flush()
            f.seek(0)

    def get(self, lun: int):
        return self._files[lun]


UNITS = IoUnits()


def _arr_to_filename(namearr: FArray) -> str:
    """Build a filename string from a LENGTH-formatted buffer: slot 1 holds
    the character count, slot 2.. hold the characters (see length.py --
    every INFILE(1/2, ...) call site in the source calls LENGTH first).
    Each character slot holds an A1-style Hollerith word (char in the low
    byte, blank in the high byte -- see hollerith.py), not a raw ASCII
    code, so it's unpacked with unholl(..., 1)."""
    n = namearr[1]
    if not isinstance(n, int) or n <= 0:
        return ""
    n = min(n, len(namearr) - 1)
    return "".join(unholl(namearr[i], 1) for i in range(2, 2 + n))


def infile(mode: int, namearr: FArray, lun: int) -> int:
    """Reimplementation of RSX-11's INFILE. Returns 0 on success, else 1."""
    if mode == 1:
        return 0 if UNITS.open_read(lun, _arr_to_filename(namearr)) else 1
    if mode == 2:
        return 0 if UNITS.open_write(lun, _arr_to_filename(namearr)) else 1
    if mode == 4:
        UNITS.close(lun)
        return 0
    if mode == 5:
        UNITS.close_delete(lun)
        return 0
    if mode == 6:
        UNITS.rewind(lun)
        return 0
    if mode == 7:
        return 0 if UNITS.open_scratch(lun) else 1
    raise ValueError(f"INFILE: unknown mode {mode}")


def dattim(times: FArray) -> None:
    now = datetime.datetime.now()
    digits = "{:02d}{:02d}{:02d}{:02d}{:02d}".format(
        now.month, now.day, now.year % 100, now.hour, now.minute
    )
    for i, ch in enumerate(digits, start=1):
        times[i] = int(ch)


# ---------------------------------------------------------------------------
# FORMAT parsing
# ---------------------------------------------------------------------------


def parse_format(fmt: str) -> list[tuple]:
    s = fmt.strip()
    if s.startswith("(") and s.endswith(")"):
        s = s[1:-1]
    return _parse_items(s)


def _parse_items(s: str) -> list[tuple]:
    tokens: list[tuple] = []
    i, n = 0, len(s)
    while i < n:
        c = s[i]
        if c in " \t,":
            i += 1
            continue
        if c == "/":
            tokens.append(("SLASH",))
            i += 1
            continue
        if c == "'":
            j = s.index("'", i + 1)
            tokens.append(("LIT", s[i + 1 : j]))
            i = j + 1
            continue
        if c == "(":
            depth, j = 1, i + 1
            while depth:
                if s[j] == "(":
                    depth += 1
                elif s[j] == ")":
                    depth -= 1
                j += 1
            tokens.append(("GROUP", 1, s[i + 1 : j - 1]))
            i = j
            continue
        if c.isdigit():
            j = i
            while j < n and s[j].isdigit():
                j += 1
            num = int(s[i:j])
            if j < n and s[j] == "H":
                text = s[j + 1 : j + 1 + num]
                tokens.append(("LIT", text))
                i = j + 1 + num
                continue
            if j < n and s[j] == "(":
                depth, k = 1, j + 1
                while depth:
                    if s[k] == "(":
                        depth += 1
                    elif s[k] == ")":
                        depth -= 1
                    k += 1
                tokens.append(("GROUP", num, s[j + 1 : k - 1]))
                i = k
                continue
            if j < n and s[j] in "XIA":
                code = s[j]
                if code == "X":
                    tokens.append(("X", num))
                    i = j + 1
                    continue
                k = j + 1
                w0 = k
                while k < n and s[k].isdigit():
                    k += 1
                width = int(s[w0:k]) if k > w0 else 1
                tokens.append((code, width, num))
                i = k
                continue
            i = j
            continue
        if c in "XIA":
            k = i + 1
            w0 = k
            while k < n and s[k].isdigit():
                k += 1
            width = int(s[w0:k]) if k > w0 else 1
            if c == "X":
                tokens.append(("X", width))
            else:
                tokens.append((c, width, 1))
            i = k
            continue
        i += 1

    out: list[tuple] = []
    for t in tokens:
        if t[0] == "GROUP":
            _, rep, inner = t
            inner_tokens = _parse_items(inner)
            for _ in range(rep):
                out.extend(inner_tokens)
        else:
            out.append(t)
    return out


_fmt_cache: dict[str, list[tuple]] = {}


def _tokens(fmt_str: str) -> list[tuple]:
    t = _fmt_cache.get(fmt_str)
    if t is None:
        t = parse_format(fmt_str)
        _fmt_cache[fmt_str] = t
    return t


# ---------------------------------------------------------------------------
# Formatted WRITE / READ
# ---------------------------------------------------------------------------


def _fmt_int(v: int, width: int) -> str:
    s = str(v)
    if len(s) > width:
        return "*" * width
    return s.rjust(width)


def fwrite_lines(tokens: list[tuple], values: list) -> list[str]:
    lines: list[str] = []
    cur: list[str] = []
    vi = 0
    for tok in tokens:
        kind = tok[0]
        if kind == "SLASH":
            lines.append("".join(cur))
            cur = []
        elif kind == "LIT":
            cur.append(tok[1])
        elif kind == "X":
            cur.append(" " * tok[1])
        elif kind == "I":
            _, width, repeat = tok
            for _ in range(repeat):
                cur.append(_fmt_int(values[vi], width))
                vi += 1
        elif kind == "A":
            _, width, repeat = tok
            for _ in range(repeat):
                v = values[vi]
                vi += 1
                cur.append(unholl(v, width))
    lines.append("".join(cur))
    return lines


def _parse_int(field: str) -> int:
    field = field.strip()
    return int(field) if field else 0


def fread_line(line: str, tokens: list[tuple]) -> list:
    values: list = []
    pos = 0
    for tok in tokens:
        kind = tok[0]
        if kind == "SLASH":
            continue
        if kind == "LIT":
            pos += len(tok[1])
        elif kind == "X":
            pos += tok[1]
        elif kind == "I":
            _, width, repeat = tok
            for _ in range(repeat):
                values.append(_parse_int(line[pos : pos + width]))
                pos += width
        elif kind == "A":
            _, width, repeat = tok
            for _ in range(repeat):
                field = line[pos : pos + width]
                pos += width
                # Aw with w < storage width (2 bytes/word here) left-justifies
                # the characters read and blank-fills the rest of the word --
                # not a raw ASCII code. holl() blank-pads to 2 chars the same way.
                values.append(holl(field[:2]))
    return values


def read_unit_line(lun: int):
    if lun == CONSOLE_LUN:
        try:
            return input()
        except EOFError:
            return None
    f = UNITS.get(lun)
    line = f.readline()
    if line == "":
        return None
    return line.rstrip("\r\n")


def write_unit_line(lun: int, text: str) -> None:
    if lun == CONSOLE_LUN:
        print(text)
        return
    f = UNITS.get(lun)
    f.write(text + "\n")


def fwrite(lun: int, fmt_str: str, values=()) -> None:
    for line in fwrite_lines(_tokens(fmt_str), list(values)):
        write_unit_line(lun, line)


def fread(lun: int, fmt_str: str):
    """Returns a list of values, or None on EOF (matches FORTRAN END=)."""
    line = read_unit_line(lun)
    if line is None:
        return None
    return fread_line(line, _tokens(fmt_str))
