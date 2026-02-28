#!/usr/bin/env python3
import argparse
import json
import os
import sys
from typing import Dict, Optional, Union

import numpy as np
import scipy.io
import scipy.sparse
import scipy.sparse.linalg


# Enable import of shared utilities from skills/_shared/
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", ".."))
from _shared._matrix_io import load_matrix  # noqa: E402


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Compute condition number and eigenvalue spread.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("--matrix", required=True, help="Path to matrix file (.npy or text)")
    parser.add_argument(
        "--delimiter",
        default=None,
        help="Delimiter for text matrices (default: any whitespace)",
    )
    parser.add_argument(
        "--norm",
        default="2",
        help="Condition number norm: 2, fro, inf, -inf, 1, -1",
    )
    parser.add_argument(
        "--symmetry-tol",
        type=float,
        default=1e-8,
        help="Tolerance for symmetry check",
    )
    parser.add_argument(
        "--skip-eigs",
        action="store_true",
        help="Skip eigenvalue spread for large matrices",
    )
    parser.add_argument("--json", action="store_true", help="Emit JSON output")
    return parser.parse_args()


def parse_norm(value: str) -> Union[float, str]:
    value = value.strip().lower()
    if value in {"2", "1", "-1"}:
        return float(value)
    if value in {"inf", "-inf", "fro"}:
        return value
    raise ValueError("norm must be one of: 2, 1, -1, inf, -inf, fro")


def compute_condition(
    matrix: Union[np.ndarray, scipy.sparse.spmatrix],
    norm: Union[float, str],
    symmetry_tol: float,
    skip_eigs: bool,
) -> Dict[str, object]:
    """Compute condition number and eigenvalue spread.

    Supports both dense and sparse matrices.
    For sparse matrices, uses scipy.sparse.linalg.svds for condition estimation.

    Args:
        matrix: Input matrix (dense or sparse)
        norm: Norm for condition number computation
        symmetry_tol: Tolerance for symmetry check
        skip_eigs: Whether to skip eigenvalue computation

    Returns:
        Dictionary with condition number and diagnostics
    """
    is_sparse = scipy.sparse.issparse(matrix)

    if matrix.ndim != 2 or matrix.shape[0] != matrix.shape[1]:
        raise ValueError("matrix must be square")

    n = matrix.shape[0]

    # Compute condition number
    if is_sparse:
        # Check finiteness for sparse matrices using the .data array
        if not np.all(np.isfinite(matrix.data)):
            raise ValueError("matrix contains non-finite values")
        # For sparse matrices, estimate condition number using svds
        # Only 2-norm is supported for sparse condition estimation
        if norm not in [2, "2", 2.0]:
            raise ValueError("Only 2-norm is supported for sparse condition number")

        try:
            # Compute largest and smallest singular values
            # For small matrices, compute more singular values for better estimates
            k = min(6, n - 2) if n > 7 else max(1, n - 2)
            if k < 1:
                # Matrix too small for svds
                cond = float(np.linalg.cond(matrix.toarray(), p=2))
            else:
                s_max = scipy.sparse.linalg.svds(matrix, k=k, which='LM', return_singular_vectors=False)
                s_min = scipy.sparse.linalg.svds(matrix, k=k, which='SM', return_singular_vectors=False)
                cond = float(np.max(s_max) / np.min(s_min))
        except (scipy.sparse.linalg.ArpackNoConvergence, scipy.sparse.linalg.ArpackError):
            # If svds fails, fall back to dense computation for small matrices
            if n <= 1000:
                cond = float(np.linalg.cond(matrix.toarray(), p=2))
            else:
                cond = float("inf")
    else:
        # Dense case (original behavior)
        if not np.all(np.isfinite(matrix)):
            raise ValueError("matrix contains non-finite values")
        cond = float(np.linalg.cond(matrix, p=norm))

    # Symmetry check
    if is_sparse and n > 10000:
        # Skip symmetry check for large sparse matrices
        is_symmetric = None
    elif is_sparse:
        # Convert to dense for symmetry check (small matrices only)
        is_symmetric = bool(
            np.allclose(matrix.toarray(), matrix.T.toarray(), atol=symmetry_tol, rtol=0.0)
        )
    else:
        is_symmetric = bool(np.allclose(matrix, matrix.T, atol=symmetry_tol, rtol=0.0))

    # Eigenvalue spread computation
    spread = None
    eig_min = None
    eig_max = None
    if not skip_eigs:
        if is_sparse and n > 1000:
            # Skip full eigenvalue computation for large sparse matrices
            spread = None
            eig_min = None
            eig_max = None
        elif is_sparse:
            # For small sparse matrices, convert to dense for eigenvalues
            eigvals = np.linalg.eigvals(matrix.toarray())
            abs_eigs = np.abs(eigvals)
            nonzero = abs_eigs[abs_eigs > 0]
            if nonzero.size:
                eig_min = float(np.min(nonzero))
                eig_max = float(np.max(nonzero))
                spread = float(eig_max / eig_min)
            else:
                spread = float("inf")
        else:
            # Dense case
            eigvals = np.linalg.eigvals(matrix)
            abs_eigs = np.abs(eigvals)
            nonzero = abs_eigs[abs_eigs > 0]
            if nonzero.size:
                eig_min = float(np.min(nonzero))
                eig_max = float(np.max(nonzero))
                spread = float(eig_max / eig_min)
            else:
                spread = float("inf")

    status = "ok"
    note = None
    if cond > 1e10:
        status = "ill-conditioned"
        note = "Consider preconditioning or scaling."
    elif cond > 1e8:
        status = "poorly-conditioned"
        note = "Preconditioning likely needed."

    return {
        "condition_number": cond,
        "eigenvalue_spread": spread,
        "eigenvalue_min_abs": eig_min,
        "eigenvalue_max_abs": eig_max,
        "is_symmetric": is_symmetric,
        "is_sparse": is_sparse,
        "status": status,
        "note": note,
    }


def main() -> None:
    args = parse_args()
    if not os.path.exists(args.matrix):
        print(f"Matrix not found: {args.matrix}", file=sys.stderr)
        sys.exit(2)

    try:
        norm = parse_norm(args.norm)
        matrix = load_matrix(args.matrix, args.delimiter)
        results = compute_condition(matrix, norm, args.symmetry_tol, args.skip_eigs)
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        sys.exit(2)

    payload = {
        "inputs": {
            "matrix": args.matrix,
            "shape": list(matrix.shape),
            "norm": args.norm,
            "symmetry_tol": args.symmetry_tol,
            "skip_eigs": args.skip_eigs,
        },
        "results": results,
    }

    if args.json:
        print(json.dumps(payload, indent=2, sort_keys=True))
        return

    print("Matrix conditioning")
    print(f"  shape: {matrix.shape}")
    print(f"  condition number: {results['condition_number']:.6g}")
    if results["eigenvalue_spread"] is not None:
        print(f"  eigenvalue spread: {results['eigenvalue_spread']:.6g}")
    else:
        print("  eigenvalue spread: skipped")
    print(f"  symmetric: {results['is_symmetric']}")
    print(f"  status: {results['status']}")
    if results["note"]:
        print(f"  note: {results['note']}")


if __name__ == "__main__":
    main()
