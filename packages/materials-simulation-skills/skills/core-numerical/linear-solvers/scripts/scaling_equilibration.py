#!/usr/bin/env python3
import argparse
import json
import os
import sys

import numpy as np
import scipy.sparse

# Enable import of shared utilities from skills/_shared/
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", ".."))
from _shared._matrix_io import load_matrix  # noqa: E402


def compute_scaling(
    matrix: np.ndarray | scipy.sparse.spmatrix,
    symmetry_tol: float,
    symmetric: bool,
) -> dict[str, object]:
    """Compute row/column scaling factors for matrix equilibration.

    Supports both dense numpy arrays and sparse scipy matrices.
    For sparse matrices, uses sparse operations for efficient computation.

    Args:
        matrix: Input matrix (dense or sparse)
        symmetry_tol: Tolerance for symmetry check
        symmetric: Whether to compute symmetric scaling

    Returns:
        Dictionary with scaling factors and diagnostics
    """
    is_sparse = scipy.sparse.issparse(matrix)

    # Check dimensions
    if matrix.ndim != 2:
        raise ValueError("matrix must be 2D")

    m, n = matrix.shape
    if symmetric and m != n:
        raise ValueError("symmetric scaling requires a square matrix")

    # Compute row and column norms using sparse operations when applicable
    if is_sparse:
        # Check finiteness for sparse matrices using the .data array
        if not np.all(np.isfinite(matrix.data)):
            raise ValueError("matrix contains non-finite values")
        # For sparse matrices, use abs() to create absolute value matrix
        abs_matrix = abs(matrix)
        # max() on sparse matrix returns a sparse matrix, convert to dense array
        row_max_sparse = abs_matrix.max(axis=1)
        col_max_sparse = abs_matrix.max(axis=0)
        # toarray() converts sparse to dense, then flatten to 1D
        row_max = np.asarray(row_max_sparse.toarray()).flatten()
        col_max = np.asarray(col_max_sparse.toarray()).flatten()
    else:
        # Dense case (original behavior)
        if not np.all(np.isfinite(matrix)):
            raise ValueError("matrix contains non-finite values")
        abs_matrix = np.abs(matrix)
        row_max = np.max(abs_matrix, axis=1)
        col_max = np.max(abs_matrix, axis=0)

    zero_rows = [int(i) for i in range(len(row_max)) if row_max[i] == 0]
    zero_cols = [int(i) for i in range(len(col_max)) if col_max[i] == 0]

    row_scale = [1.0 / v if v > 0 else 1.0 for v in row_max]
    col_scale = [1.0 / v if v > 0 else 1.0 for v in col_max]

    symmetric_scale = None

    # Symmetry check - for sparse, convert to dense only for check (or skip for very large)
    if is_sparse and matrix.shape[0] > 10000:
        # Skip symmetry check for large sparse matrices
        is_symmetric = None
    elif is_sparse:
        # Convert to dense for symmetry check (small matrices only)
        is_symmetric = bool(
            np.allclose(matrix.toarray(), matrix.T.toarray(), atol=symmetry_tol, rtol=0.0)
        )
    else:
        is_symmetric = bool(np.allclose(matrix, matrix.T, atol=symmetry_tol, rtol=0.0))

    if symmetric:
        symmetric_scale = [1.0 / np.sqrt(v) if v > 0 else 1.0 for v in row_max]

    notes: list[str] = []
    if is_sparse:
        notes.append(f"Sparse matrix detected (nnz={matrix.nnz}, density={matrix.nnz/(m*n):.4g}).")
    if zero_rows:
        notes.append("Zero rows detected; scaling set to 1 for those rows.")
    if zero_cols:
        notes.append("Zero cols detected; scaling set to 1 for those cols.")
    if symmetric and is_symmetric is not None and not is_symmetric:
        notes.append("Matrix is not symmetric within tolerance; check inputs.")
    elif symmetric and is_symmetric is None:
        notes.append("Symmetry check skipped for large sparse matrix.")

    return {
        "shape": [m, n],
        "row_scale": row_scale,
        "col_scale": col_scale,
        "row_scale_min": float(min(row_scale)) if row_scale else 0.0,
        "row_scale_max": float(max(row_scale)) if row_scale else 0.0,
        "col_scale_min": float(min(col_scale)) if col_scale else 0.0,
        "col_scale_max": float(max(col_scale)) if col_scale else 0.0,
        "zero_rows": zero_rows,
        "zero_cols": zero_cols,
        "symmetric_scale": symmetric_scale,
        "symmetric": is_symmetric,
        "is_sparse": is_sparse,
        "notes": notes,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Suggest row/column scaling for matrix equilibration.",
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
    parser.add_argument(
        "--symmetric",
        action="store_true",
        help="Request symmetric scaling (uses row max norms)",
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
        results = compute_scaling(matrix, args.symmetry_tol, args.symmetric)
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        sys.exit(2)

    payload = {
        "inputs": {
            "matrix": args.matrix,
            "symmetry_tol": args.symmetry_tol,
            "symmetric": args.symmetric,
        },
        "results": results,
    }

    if args.json:
        print(json.dumps(payload, indent=2, sort_keys=True))
        return

    print("Scaling equilibration")
    print(f"  shape: {results['shape']}")
    print(f"  row_scale_min: {results['row_scale_min']:.6g}")
    print(f"  row_scale_max: {results['row_scale_max']:.6g}")
    print(f"  col_scale_min: {results['col_scale_min']:.6g}")
    print(f"  col_scale_max: {results['col_scale_max']:.6g}")
    if results["symmetric_scale"] is not None:
        print("  symmetric_scale: provided")
    for note in results["notes"]:
        print(f"  note: {note}")


if __name__ == "__main__":
    main()
