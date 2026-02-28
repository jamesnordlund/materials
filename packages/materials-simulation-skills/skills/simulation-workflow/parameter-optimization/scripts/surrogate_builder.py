#!/usr/bin/env python3
import argparse
import json
import sys

import numpy as np
from numpy.polynomial import Polynomial
from scipy.interpolate import RBFInterpolator


def parse_list(raw: str) -> list[float]:
    parts = [p.strip() for p in raw.split(",") if p.strip()]
    if not parts:
        raise ValueError("value list must be a comma-separated list")
    return [float(p) for p in parts]


def build_surrogate(
    x: list[float],
    y: list[float],
    model: str,
    rbf_epsilon: float = None,
) -> dict[str, object]:
    """Build and fit a surrogate model (RBF or polynomial).

    Args:
        x: Input values
        y: Output values
        model: Surrogate type ("rbf" or "poly")
        rbf_epsilon: RBF epsilon parameter; if None, computed as average distance between samples

    Returns:
        Dictionary with model_type, metrics (MSE, R², MSE), and model properties.
    """
    if len(x) != len(y):
        raise ValueError("x and y must have same length")
    if model not in {"rbf", "poly"}:
        raise ValueError("model must be rbf or poly")
    if len(x) < 2:
        raise ValueError("need at least 2 samples")

    x_arr = np.array(x)
    y_arr = np.array(y)

    # Compute baseline statistics
    mean_y = np.mean(y_arr)
    ss_tot = np.sum((y_arr - mean_y) ** 2)  # Total sum of squares
    pop_var = float(np.var(y_arr))
    n_samples = len(x)

    notes = [
        "Using SciPy RBF/polynomial models."
        " Consider Gaussian process surrogates for production use."
    ]

    if model == "rbf":
        # Auto-compute epsilon if not provided: use average distance between samples
        if rbf_epsilon is None:
            x_std = float(np.std(x_arr))
            rbf_epsilon = x_std if x_std > 0 else 1.0
            notes.append(
                f"Auto-computed epsilon={rbf_epsilon:.4g}"
                f" from data scale (std={x_std:.4g})"
            )

        # Fit RBF model with multiquadric kernel
        rbf_model = RBFInterpolator(
            x_arr.reshape(-1, 1), y_arr, kernel="multiquadric", epsilon=rbf_epsilon
        )
        y_pred = rbf_model(x_arr.reshape(-1, 1))
        ss_res = np.sum((y_arr - y_pred) ** 2)
        mse = float(ss_res / n_samples)
        r2 = float(1.0 - ss_res / ss_tot) if ss_tot > 0 else 1.0
        return {
            "model_type": "rbf",
            "rbf_function": "multiquadric",
            "rbf_epsilon": rbf_epsilon,
            "metrics": {
                "mse": mse,
                "r_squared": r2,
                "population_variance": pop_var,
            },
            "n_samples": n_samples,
            "notes": notes,
        }
    else:  # model == "poly"
        # Fit polynomial (degree 2 by default for simple surrogate)
        poly_model = Polynomial.fit(x_arr, y_arr, deg=2)
        y_pred = poly_model(x_arr)
        coeffs = poly_model.convert().coef
        ss_res = np.sum((y_arr - y_pred) ** 2)
        mse = float(ss_res / n_samples)
        r2 = float(1.0 - ss_res / ss_tot) if ss_tot > 0 else 1.0
        return {
            "model_type": "poly",
            "degree": 2,
            "coefficients": [float(c) for c in coeffs],
            "metrics": {
                "mse": mse,
                "r_squared": r2,
                "population_variance": pop_var,
            },
            "n_samples": n_samples,
            "notes": notes,
        }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build a simple surrogate model summary.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("--x", required=True, help="Comma-separated input values")
    parser.add_argument("--y", required=True, help="Comma-separated output values")
    parser.add_argument("--model", choices=["rbf", "poly"], default="rbf", help="Surrogate type")
    parser.add_argument(
        "--rbf-epsilon",
        type=float,
        default=None,
        help="RBF epsilon parameter (default: auto-computed from data scale)",
    )
    parser.add_argument("--json", action="store_true", help="Emit JSON output")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    try:
        x = parse_list(args.x)
        y = parse_list(args.y)
        result = build_surrogate(x, y, args.model, rbf_epsilon=args.rbf_epsilon)
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        sys.exit(2)

    payload = {
        "inputs": {"x": x, "y": y, "model": args.model},
        "results": result,
    }

    if args.json:
        print(json.dumps(payload, indent=2, sort_keys=True))
        return

    print("Surrogate summary")
    print(f"  model: {result['model_type']}")
    if result['model_type'] == 'rbf':
        print(f"  rbf_function: {result['rbf_function']}")
        print(f"  rbf_epsilon: {result['rbf_epsilon']}")
    else:
        print(f"  degree: {result['degree']}")
    print(f"  n_samples: {result['n_samples']}")
    print(f"  mse: {result['metrics']['mse']:.6g}")
    print(f"  r_squared: {result['metrics']['r_squared']:.6g}")


if __name__ == "__main__":
    main()
