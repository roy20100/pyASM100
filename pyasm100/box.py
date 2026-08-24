"""Mutable single-value container emulating FORTRAN call-by-reference scalars.

FORTRAN passes every argument by reference, so a subroutine like
``SUBROUTINE PASS1(RETFLG)`` can assign into ``RETFLG`` and the caller sees
the new value. Array arguments already have reference semantics in Python
(an FArray object is shared), but plain scalar in/out parameters need an
explicit box.
"""

from __future__ import annotations


class Box:
    __slots__ = ("value",)

    def __init__(self, value=0):
        self.value = value

    def __repr__(self):
        return f"Box({self.value!r})"
