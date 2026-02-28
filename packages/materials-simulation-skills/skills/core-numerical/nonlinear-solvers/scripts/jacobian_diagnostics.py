#!/usr/bin/env python3
"""Analyze Jacobian matrix quality for nonlinear solvers."""
import argparse
import json
import os
import sys
from typing import Any

import numpy as np
import scipy.io
import scipy.sparse
import scipy.sparse.linalg

# Enable import of shared utilities from skills/_shared/
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", ".."))
from _shared._matrix_io import load_matrix  # noqa: E402


def diagnose_jacobian(
    matrix: np.ndarray | scipy.sparse.spmatrix,
    finite_diff_matrix: np.ndarray | scipy.sparse.spmatrix | None = None,
    tolerance: float = 1e-6,
) -> dict[str, Any]:
    """Analyze Jacobian matrix quality.

    Supports both dense numpy arrays and sparse scipy matrices.
    For sparse matrices, uses scipy.sparse.linalg.svds for singular value computation.

    Args:
        matrix: The Jacobian matrix to analyze (dense or sparse)
        finite_diff_matrix: Optional finite-difference approximation for comparison
        tolerance: Tolerance for rank deficiency detection

    Returns:
        Dictionary with Jacobian diagnostics
    """
    is_sparse = scipy.sparse.issparse(matrix)

    if matrix.ndim != 2:
        raise ValueError("matrix must be 2-dimensional")

    if matrix.size == 0:
        raise ValueError("matrix must not be empty")

    if tolerance <= 0:
        raise ValueError("tolerance must be positive")

    m, n = matrix.shape
    notes: list[str] = []

    if is_sparse:
        density = matrix.nnz / (m * n)
        notes.append(
            f"Sparse Jacobian detected (nnz={matrix.nnz}, density={density:.4g})."
        )

    # Compute SVD for condition number and rank analysis
    try:
        if is_sparse:
            # For sparse matrices, use svds to compute largest and smallest singular values
            k = min(6, min(m, n) - 2) if min(m, n) > 7 else max(1, min(m, n) - 2)
            if k < 1:
                # Matrix too small for svds, convert to dense
                singular_values = np.linalg.svd(matrix.toarray(), compute_uv=False)
            else:
                # Compute largest and smallest singular values
                s_max = scipy.sparse.linalg.svds(
                    matrix, k=k, which='LM', return_singular_vectors=False
                )
                s_min = scipy.sparse.linalg.svds(
                    matrix, k=k, which='SM', return_singular_vectors=False
                )
                # Combine and sort
                singular_values = np.sort(np.concatenate([s_max, s_min]))[::-1]
        else:
            # Dense case (original behavior)
            singular_values = np.linalg.svd(matrix, compute_uv=False)
    except (
        np.linalg.LinAlgError,
        scipy.sparse.linalg.ArpackNoConvergence,
        scipy.sparse.linalg.ArpackError,
    ):
        return {
            "shape": [m, n],
            "condition_number": float("inf"),
            "rank_deficient": True,
            "estimated_rank": 0,
            "singular_value_min": 0.0,
            "singular_value_max": 0.0,
            "jacobian_quality": "singular",
            "finite_diff_error": None,
            "is_sparse": is_sparse,
            "notes": ["SVD computation failed; matrix may be ill-formed."],
        }

    sv_max = float(singular_values[0])
    sv_min = float(singular_values[-1])

    # Condition number
    condition_number = sv_max / sv_min if sv_min > 1e-30 else float("inf")

    # Estimate numerical rank
    rank_tol = max(m, n) * sv_max * np.finfo(float).eps
    estimated_rank = int(np.sum(singular_values > rank_tol))
    rank_deficient = estimated_rank < min(m, n)

    # Classify Jacobian quality
    if condition_number == float("inf") or sv_min < 1e-14:
        jacobian_quality = "near-singular"
        notes.append("Near-singular Jacobian; regularization may be needed.")
    elif condition_number > 1e10:
        jacobian_quality = "ill-conditioned"
        notes.append("Highly ill-conditioned; use iterative refinement or scaling.")
    elif condition_number > 1e6:
        jacobian_quality = "moderately-conditioned"
        notes.append("Moderate conditioning; standard methods should work.")
    else:
        jacobian_quality = "good"
        notes.append("Well-conditioned Jacobian.")

    if rank_deficient:
        notes.append(f"Rank deficient: estimated rank {estimated_rank} < min({m}, {n}).")

    # Compare with finite difference approximation if provided
    finite_diff_error = None
    if finite_diff_matrix is not None:
        if finite_diff_matrix.shape != matrix.shape:
            notes.append("Finite-diff matrix shape mismatch; skipping comparison.")
        else:
            # Compute difference using sparse operations if applicable
            if is_sparse or scipy.sparse.issparse(finite_diff_matrix):
                # Use sparse norm computation
                if is_sparse and scipy.sparse.issparse(finite_diff_matrix):
                    diff = matrix - finite_diff_matrix
                    diff_norm = scipy.sparse.linalg.norm(diff)
                    matrix_norm = scipy.sparse.linalg.norm(matrix)
                elif is_sparse:
                    # matrix is sparse, finite_diff_matrix is dense
                    diff_norm = np.linalg.norm((matrix - finite_diff_matrix).toarray())
                    matrix_norm = scipy.sparse.linalg.norm(matrix)
                else:
                    # matrix is dense, finite_diff_matrix is sparse
                    diff_norm = np.linalg.norm(matrix - finite_diff_matrix.toarray())
                    matrix_norm = np.linalg.norm(matrix)
            else:
                # Both dense
                diff = matrix - finite_diff_matrix
                diff_norm = np.linalg.norm(diff)
                matrix_norm = np.linalg.norm(matrix)

            relative_error = diff_norm / (matrix_norm + 1e-30)
            finite_diff_error = float(relative_error)

            if relative_error > 0.1:
                notes.append(
                    f"Large discrepancy with finite-diff ({relative_error:.2e});"
                    " check analytic Jacobian."
                )
            elif relative_error > 0.01:
                notes.append(f"Moderate discrepancy with finite-diff ({relative_error:.2e}).")
            else:
                notes.append("Jacobian matches finite-difference approximation well.")

    return {
        "shape": [m, n],
        "condition_number": condition_number,
        "rank_deficient": rank_deficient,
        "estimated_rank": estimated_rank,
        "singular_value_min": sv_min,
        "singular_value_max": sv_max,
        "jacobian_quality": jacobian_quality,
        "finite_diff_error": finite_diff_error,
        "is_sparse": is_sparse,
        "notes": notes,
    }



def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Analyze Jacobian matrix quality.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--matrix",
        type=str,
        required=True,
        help="Path to Jacobian matrix file (text format)",
    )
    parser.add_argument(
        "--finite-diff-matrix",
        type=str,
        default=None,
        help="Path to finite-difference Jacobian for comparison",
    )
    parser.add_argument(
        "--tolerance",
        type=float,
        default=1e-6,
        help="Tolerance for rank deficiency detection",
    )
    parser.add_argument("--json", action="store_true", help="Emit JSON output")
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    try:
        matrix = load_matrix(args.matrix)
        if matrix.ndim == 1:
            matrix = matrix.reshape(1, -1)
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        sys.exit(2)

    finite_diff_matrix = None
    if args.finite_diff_matrix:
        try:
            finite_diff_matrix = load_matrix(args.finite_diff_matrix)
            if finite_diff_matrix.ndim == 1:
                finite_diff_matrix = finite_diff_matrix.reshape(1, -1)
        except ValueError as exc:
            print(str(exc), file=sys.stderr)
            sys.exit(2)

    try:
        result = diagnose_jacobian(
            matrix=matrix,
            finite_diff_matrix=finite_diff_matrix,
            tolerance=args.tolerance,
        )
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        sys.exit(2)

    payload: dict[str, Any] = {
        "inputs": {
            "matrix": args.matrix,
            "finite_diff_matrix": args.finite_diff_matrix,
            "tolerance": args.tolerance,
        },
        "results": result,
    }

    if args.json:
        print(json.dumps(payload, indent=2, sort_keys=True))
        return

    print("Jacobian diagnostics")
    print(f"  shape: {result['shape']}")
    print(f"  condition_number: {result['condition_number']:.2e}")
    print(f"  rank_deficient: {result['rank_deficient']}")
    print(f"  estimated_rank: {result['estimated_rank']}")
    print(f"  singular_value_min: {result['singular_value_min']:.2e}")
    print(f"  singular_value_max: {result['singular_value_max']:.2e}")
    print(f"  jacobian_quality: {result['jacobian_quality']}")
    if result["finite_diff_error"] is not None:
        print(f"  finite_diff_error: {result['finite_diff_error']:.2e}")
    for note in result["notes"]:
        print(f"  note: {note}")


if __name__ == "__main__":
    main()
