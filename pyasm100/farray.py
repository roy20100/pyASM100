"""1-based array emulation for translated FORTRAN DIMENSION/COMMON arrays.

FORTRAN arrays are 1-based and (when multi-dimensional) stored column-major.
Ported code indexes these exactly as the original FORTRAN did -- e.g.
``G.OPSYM[5, 219]`` or ``G.COD[12]`` -- rather than being shifted to 0-based,
since that shift is the single biggest source of off-by-one bugs in this kind
of port.
"""

from __future__ import annotations


class FArray:
    """A 1-based, optionally multi-dimensional array over a flat list.

    ``FArray(40)`` mirrors ``INTEGER SYM(40)``: valid indices are 1..40.
    ``FArray(8, 231)`` mirrors ``INTEGER OPSYM(8,231)``: index with a
    2-tuple, ``arr[5, 219]``, exactly as the FORTRAN source does.
    """

    __slots__ = ("dims", "_strides", "_data")

    def __init__(self, *dims: int, fill: int = 0):
        if not dims:
            raise ValueError("FArray needs at least one dimension")
        self.dims = tuple(dims)
        # Column-major strides, matching FORTRAN storage order.
        strides = []
        acc = 1
        for d in self.dims:
            strides.append(acc)
            acc *= d
        self._strides = tuple(strides)
        self._data = [fill] * acc

    def _offset(self, index) -> int:
        if isinstance(index, tuple):
            if len(index) != len(self.dims):
                raise IndexError(
                    f"FArray with dims {self.dims} indexed with {len(index)} subscripts"
                )
            idxs = index
        else:
            idxs = (index,)
        off = 0
        for i, d, s in zip(idxs, self.dims, self._strides):
            if not (1 <= i <= d):
                raise IndexError(f"subscript {i} out of range 1..{d}")
            off += (i - 1) * s
        return off

    def __getitem__(self, index):
        return self._data[self._offset(index)]

    def __setitem__(self, index, value):
        self._data[self._offset(index)] = value

    def __len__(self):
        return self.dims[0]

    def __iter__(self):
        """Iterate 1-based over the first dimension's values (1D arrays)."""
        for i in range(1, self.dims[0] + 1):
            yield self[i]

    def fill(self, value: int = 0) -> None:
        for i in range(len(self._data)):
            self._data[i] = value

    def raw(self) -> list:
        """The underlying flat, 0-based storage list."""
        return self._data

    def __repr__(self):
        return f"FArray(dims={self.dims})"
