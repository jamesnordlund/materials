#!/usr/bin/env python3
import argparse
import json
import os
import sys

import numpy as np


def parse_eigs(raw: str) -> np.ndarray:
    parts = [p.strip() for p in raw.split(",") if p.strip()]
    if not parts:
        raise ValueError("eigs must be a comma-separated list")
    return np.array([complex(p) for p in parts], dtype=complex)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Detect stiffness from eigenvalues or a Jacobian matrix.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--eigs", help="Comma-separated eigenvalues")
    group.add_argument("--jacobian", help="Path to Jacobian matrix (.npy or text)")
    parser.add_argument(
        "--delimiter",
        default=None,
        help="Delimiter for text Jacobians (default: any whitespace)",
    )
    parser.add_argument(
        "--threshold",
        type=float,
        default=1e3,
        help="Stiffness ratio threshold",
    )
    parser.add_argument("--json", action="store_true", help="Emit JSON output")
    return parser.parse_args()


def load_matrix(path: str, delimiter: str | None) -> np.ndarray:
    _, ext = os.path.splitext(path)
    if ext == ".npy":
        return np.load(path, allow_pickle=False)
    return np.loadtxt(path, delimiter=delimiter)


def compute_stiffness(eigs: np.ndarray, threshold: float) -> dict[str, object]:
    """
    Compute stiffness ratio from eigenvalues using real parts.

    The stiffness ratio is defined as max(|Re(lambda)|) / min(|Re(lambda)|)
    for eigenvalues with nonzero real parts. This correctly identifies stiffness
    in systems with significant imaginary eigenvalue components.

    Eigenvalues with zero real part (pure imaginary) are excluded from the
    stiffness calculation as they do not contribute to stiffness.

    Reference: Hairer & Wanner, "Solving Ordinary Differential Equations II:
    Stiff and Differential-Algebraic Problems," 2nd ed. (1996), Section IV.2.

    Args:
        eigs: Array of eigenvalues (may be complex)
        threshold: Stiffness ratio threshold for classification

    Returns:
        Dictionary with stiffness_ratio, stiff flag, recommendation, and counts
    """
    if threshold <= 0:
        raise ValueError("threshold must be positive")
    if eigs.size == 0:
        raise ValueError("eigs must be non-empty")
    if not np.all(np.isfinite(eigs)):
        raise ValueError("eigs contain non-finite values")

    # Use real parts of eigenvalues, not modulus
    real_parts = np.real(eigs)
    abs_real = np.abs(real_parts)

    # Exclude eigenvalues with zero real part (pure imaginary)
    nonzero_real = abs_real[abs_real > 0]

    if nonzero_real.size == 0:
        # All eigenvalues are pure imaginary (zero real part)
        # Oscillatory systems without damping are not stiff by typical definitions
        ratio = None
        stiff = False
        recommendation = "P-stable or symplectic method (oscillatory system)"
    else:
        ratio = float(np.max(nonzero_real) / np.min(nonzero_real))
        stiff = ratio >= threshold
        recommendation = "implicit (BDF/Radau)" if stiff else "explicit (RK/Adams)"

    return {
        "stiffness_ratio": ratio,
        "stiff": stiff,
        "recommendation": recommendation,
        "nonzero_count": int(nonzero_real.size),
        "total_count": int(eigs.size),
    }


def main() -> None:
    args = parse_args()
    try:
        if args.eigs is not None:
            eigs = parse_eigs(args.eigs)
            source = "eigs"
        else:
            if not os.path.exists(args.jacobian):
                print(f"Jacobian not found: {args.jacobian}", file=sys.stderr)
                sys.exit(2)
            jacobian = load_matrix(args.jacobian, args.delimiter)
            if jacobian.ndim != 2 or jacobian.shape[0] != jacobian.shape[1]:
                print("Jacobian must be square.", file=sys.stderr)
                sys.exit(2)
            eigs = np.linalg.eigvals(jacobian)
            source = "jacobian"
        results = compute_stiffness(eigs, args.threshold)
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        sys.exit(2)

    payload = {
        "inputs": {
            "source": source,
            "threshold": args.threshold,
        },
        "results": results,
    }

    if args.json:
        print(json.dumps(payload, indent=2, sort_keys=True))
        return

    print("Stiffness detection")
    sr = results["stiffness_ratio"]
    print(f"  stiffness ratio: {sr:.6g}" if sr is not None else "  stiffness ratio: N/A")
    print(f"  stiff: {results['stiff']}")
    print(f"  recommendation: {results['recommendation']}")


if __name__ == "__main__":
    main()
