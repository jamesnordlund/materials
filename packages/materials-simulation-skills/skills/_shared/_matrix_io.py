"""Shared matrix I/O utilities for materials-simulation-skills CLI scripts.

This module provides a canonical ``load_matrix`` function that is used by
multiple scripts (linear-solvers, numerical-stability, nonlinear-solvers) to
load dense and sparse matrices from disk.

Supported formats
-----------------
- Matrix Market (``.mtx``) -- loaded as sparse CSR via ``scipy.io.mmread``
- NumPy binary (``.npy``) -- loaded as a dense ``np.ndarray`` via ``np.load``
- Delimited text (any other extension) -- loaded via ``np.loadtxt``

Typical usage inside a CLI script::

    from skills._shared._matrix_io import load_matrix

    matrix = load_matrix("jacobian.mtx")
"""

from __future__ import annotations

import os

import numpy as np
import scipy.io
import scipy.sparse


def load_matrix(
    path: str,
    delimiter: str | None = None,
) -> np.ndarray | scipy.sparse.spmatrix:
    """Load a matrix from file, auto-detecting the format.

    Parameters
    ----------
    path : str
        Path to the matrix file.
    delimiter : str or None, optional
        Column delimiter for plain-text files.  Ignored for ``.mtx`` and
        ``.npy`` formats.  When *None* (the default), ``numpy.loadtxt``
        splits on any whitespace.

    Returns
    -------
    numpy.ndarray or scipy.sparse.spmatrix
        A dense NumPy array or a sparse SciPy matrix in CSR format.

    Raises
    ------
    ValueError
        If the file cannot be read or parsed.
    """
    _, ext = os.path.splitext(path)
    try:
        if ext == ".mtx":
            # Matrix Market format -- load as sparse and convert to CSR
            matrix = scipy.io.mmread(path)
            return scipy.sparse.csr_matrix(matrix)
        elif ext == ".npy":
            return np.load(path, allow_pickle=False)
        else:
            return np.loadtxt(path, delimiter=delimiter)
    except Exception as exc:
        raise ValueError(f"Failed to load matrix from {path}: {exc}") from exc
