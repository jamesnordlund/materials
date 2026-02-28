#!/usr/bin/env python3
import argparse
import json
import os
import sys
from typing import Optional, Union

import numpy as np
import scipy.sparse


# Enable import of shared utilities from skills/_shared/
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", ".."))
from _shared._matrix_io import load_matrix  # noqa: E402


def compute_stats(matrix: Union[np.ndarray, scipy.sparse.spmatrix], symmetry_tol: float) -> dict:
    """Compute sparsity statistics for a matrix.

    Supports both dense numpy arrays and sparse scipy matrices.
    For sparse matrices, computes NNZ and density from sparse format directly.

    Args:
        matrix: Input matrix (dense or sparse)
        symmetry_tol: Tolerance for symmetry check

    Returns:
        Dictionary with sparsity statistics
    """
    is_sparse = scipy.sparse.issparse(matrix)

    if matrix.ndim != 2:
        raise ValueError("matrix must be 2D")

    m, n = matrix.shape

    # Compute NNZ and density
    if is_sparse:
        # Check finiteness for sparse matrices using the .data array
        if not np.all(np.isfinite(matrix.data)):
            raise ValueError("matrix contains non-finite values")
        # For sparse matrices, use the nnz attribute directly
        nnz = int(matrix.nnz)
        density = float(nnz) / float(m * n) if m * n > 0 else 0.0
    else:
        # Dense case (original behavior)
        if not np.all(np.isfinite(matrix)):
            raise ValueError("matrix contains non-finite values")
        nnz = int(np.count_nonzero(matrix))
        density = float(nnz) / float(m * n) if m * n > 0 else 0.0

    # Bandwidth: max |i-j| where A_ij != 0
    if is_sparse:
        # For sparse matrices, use nonzero() method
        rows, cols = matrix.nonzero()
    else:
        rows, cols = np.nonzero(matrix)

    if rows.size:
        bandwidth = int(np.max(np.abs(rows - cols)))
    else:
        bandwidth = 0

    # Symmetry check - for sparse, convert to dense only for check (or skip for very large)
    if is_sparse and m > 10000:
        # Skip symmetry check for large sparse matrices
        symmetric = None
    elif is_sparse:
        # Convert to dense for symmetry check (small matrices only)
        symmetric = bool(
            np.allclose(matrix.toarray(), matrix.T.toarray(), atol=symmetry_tol, rtol=0.0)
        )
    else:
        symmetric = bool(np.allclose(matrix, matrix.T, atol=symmetry_tol, rtol=0.0))

    return {
        "shape": [m, n],
        "nnz": nnz,
        "density": density,
        "bandwidth": bandwidth,
        "symmetry": symmetric,
        "is_sparse": is_sparse,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Compute sparsity statistics for a matrix.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("--matrix", required=True, help="Path to matrix file (.npy or text)")
    parser.add_argument(
        "--delimiter",
        default=None,
        help="Delimiter for text matrices (default: any whitespace)",
    )
    parser.add_argument(
        "--symmetry-tol",
        type=float,
        default=1e-8,
        help="Tolerance for symmetry check",
    )
    parser.add_argument("--json", action="store_true", help="Emit JSON output")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if not os.path.exists(args.matrix):
        print(f"Matrix not found: {args.matrix}", file=sys.stderr)
        sys.exit(2)

    try:
        matrix = load_matrix(args.matrix, args.delimiter)
        results = compute_stats(matrix, args.symmetry_tol)
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        sys.exit(2)

    payload = {
        "inputs": {
            "matrix": args.matrix,
            "symmetry_tol": args.symmetry_tol,
        },
        "results": results,
    }

    if args.json:
        print(json.dumps(payload, indent=2, sort_keys=True))
        return

    print("Sparsity stats")
    print(f"  shape: {results['shape']}")
    print(f"  nnz: {results['nnz']}")
    print(f"  density: {results['density']:.6g}")
    print(f"  bandwidth: {results['bandwidth']}")
    print(f"  symmetric: {results['symmetry']}")


if __name__ == "__main__":
    main()
