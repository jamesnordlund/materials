#!/usr/bin/env python3
"""
Comparison Tool - Compare simulation results with reference data.

Computes error metrics between simulation output and reference/experimental data.
Supports various error norms (L1, L2, Linf, RMSE, MAE) and handles interpolation.

Usage:
    python comparison_tool.py --simulation result.json --reference expected.json \
        --metric l2_error --json
    python comparison_tool.py --simulation result.json --reference experiment.csv \
        --metric rmse --json
"""

import argparse
import json
import math
import os
import sys
from typing import Any

# Import shared utilities
try:
    from ._utils import flatten_field, load_csv_file, load_json_file
except ImportError:
    # Fallback for standalone execution
    import importlib.util
    _utils_path = os.path.join(os.path.dirname(__file__), "_utils.py")
    spec = importlib.util.spec_from_file_location("_utils", _utils_path)
    _utils = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(_utils)
    load_json_file = _utils.load_json_file
    load_csv_file = _utils.load_csv_file
    flatten_field = _utils.flatten_field


def load_data(filepath: str) -> dict[str, Any]:
    """Load data based on file extension."""
    if filepath.endswith(".json"):
        return load_json_file(filepath)
    elif filepath.endswith(".csv"):
        return load_csv_file(filepath)
    else:
        raise ValueError(f"Unsupported file format: {filepath}")


def extract_values(
    data: dict[str, Any],
    field: str | None = None
) -> tuple[list[float], list[float] | None]:
    """Extract values and optional coordinates from data."""
    values = None
    coords = None

    # Try to find values
    if field and field in data:
        values = data[field]
    elif "values" in data:
        values = data["values"]
    elif "y" in data:
        values = data["y"]
    elif "_data" in data:
        # CSV format
        keys = list(data["_data"].keys())
        if len(keys) >= 2:
            coords = data["_data"][keys[0]]
            values = data["_data"][keys[1]]
        elif len(keys) == 1:
            values = data["_data"][keys[0]]

    # Try to find coordinates
    if coords is None:
        for key in ["x", "coordinates", "distance", "time", "t"]:
            if key in data:
                coords = data[key]
                break

    # Flatten if nested
    if isinstance(values, list) and values and isinstance(values[0], list):
        values = flatten_list(values)

    return values, coords


# Use flatten_field from _utils (renamed from flatten_list for consistency)
flatten_list = flatten_field


def interpolate_1d(
    x_new: list[float],
    x_old: list[float],
    y_old: list[float]
) -> list[float]:
    """Linear interpolation from (x_old, y_old) to x_new."""
    if not x_old or not y_old:
        return []

    y_new = []
    for x in x_new:
        # Find surrounding points
        if x <= x_old[0]:
            y_new.append(y_old[0])
        elif x >= x_old[-1]:
            y_new.append(y_old[-1])
        else:
            # Binary search for interval
            lo, hi = 0, len(x_old) - 1
            while hi - lo > 1:
                mid = (lo + hi) // 2
                if x_old[mid] <= x:
                    lo = mid
                else:
                    hi = mid

            # Linear interpolation
            t = (x - x_old[lo]) / (x_old[hi] - x_old[lo])
            y_new.append(y_old[lo] * (1 - t) + y_old[hi] * t)

    return y_new


def compute_l1_error(sim: list[float], ref: list[float]) -> float:
    """Compute L1 error (mean absolute error normalized by reference norm)."""
    if len(sim) != len(ref):
        raise ValueError(f"Length mismatch: {len(sim)} vs {len(ref)}")

    l1_diff = sum(abs(s - r) for s, r in zip(sim, ref, strict=True))
    l1_ref = sum(abs(r) for r in ref)

    if l1_ref > 0:
        return l1_diff / l1_ref
    return l1_diff


def compute_l2_error(sim: list[float], ref: list[float]) -> float:
    """Compute L2 error (relative RMS error)."""
    if len(sim) != len(ref):
        raise ValueError(f"Length mismatch: {len(sim)} vs {len(ref)}")

    l2_diff_sq = sum((s - r) ** 2 for s, r in zip(sim, ref, strict=True))
    l2_ref_sq = sum(r ** 2 for r in ref)

    if l2_ref_sq > 0:
        return math.sqrt(l2_diff_sq / l2_ref_sq)
    return math.sqrt(l2_diff_sq)


def compute_linf_error(sim: list[float], ref: list[float]) -> float:
    """Compute L-infinity error (max absolute error normalized)."""
    if len(sim) != len(ref):
        raise ValueError(f"Length mismatch: {len(sim)} vs {len(ref)}")

    max_diff = max(abs(s - r) for s, r in zip(sim, ref, strict=True))
    max_ref = max(abs(r) for r in ref)

    if max_ref > 0:
        return max_diff / max_ref
    return max_diff


def compute_rmse(sim: list[float], ref: list[float]) -> float:
    """Compute Root Mean Square Error (absolute)."""
    if len(sim) != len(ref):
        raise ValueError(f"Length mismatch: {len(sim)} vs {len(ref)}")

    n = len(sim)
    mse = sum((s - r) ** 2 for s, r in zip(sim, ref, strict=True)) / n
    return math.sqrt(mse)


def compute_mae(sim: list[float], ref: list[float]) -> float:
    """Compute Mean Absolute Error."""
    if len(sim) != len(ref):
        raise ValueError(f"Length mismatch: {len(sim)} vs {len(ref)}")

    n = len(sim)
    return sum(abs(s - r) for s, r in zip(sim, ref, strict=True)) / n


def compute_max_difference(sim: list[float], ref: list[float]) -> float:
    """Compute maximum absolute difference."""
    if len(sim) != len(ref):
        raise ValueError(f"Length mismatch: {len(sim)} vs {len(ref)}")

    return max(abs(s - r) for s, r in zip(sim, ref, strict=True))


def compute_correlation(sim: list[float], ref: list[float]) -> float:
    """Compute Pearson correlation coefficient."""
    if len(sim) != len(ref):
        raise ValueError(f"Length mismatch: {len(sim)} vs {len(ref)}")

    n = len(sim)
    mean_sim = sum(sim) / n
    mean_ref = sum(ref) / n

    cov = sum(
        (s - mean_sim) * (r - mean_ref)
        for s, r in zip(sim, ref, strict=True)
    )
    std_sim = math.sqrt(sum((s - mean_sim) ** 2 for s in sim))
    std_ref = math.sqrt(sum((r - mean_ref) ** 2 for r in ref))

    if std_sim > 0 and std_ref > 0:
        return cov / (std_sim * std_ref)
    return 0.0


def compute_r_squared(sim: list[float], ref: list[float]) -> float:
    """Compute coefficient of determination (R^2)."""
    if len(sim) != len(ref):
        raise ValueError(f"Length mismatch: {len(sim)} vs {len(ref)}")

    mean_ref = sum(ref) / len(ref)

    ss_res = sum((r - s) ** 2 for s, r in zip(sim, ref, strict=True))
    ss_tot = sum((r - mean_ref) ** 2 for r in ref)

    if ss_tot > 0:
        return 1 - ss_res / ss_tot
    return 0.0


METRIC_FUNCTIONS = {
    "l1_error": compute_l1_error,
    "l2_error": compute_l2_error,
    "linf_error": compute_linf_error,
    "rmse": compute_rmse,
    "mae": compute_mae,
    "max_difference": compute_max_difference,
    "correlation": compute_correlation,
    "r_squared": compute_r_squared
}


def interpret_error(metric: str, value: float) -> str:
    """Provide interpretation of error value."""
    if metric in ["l1_error", "l2_error", "linf_error"]:
        if value < 0.01:
            return "excellent"
        elif value < 0.05:
            return "good"
        elif value < 0.10:
            return "moderate"
        else:
            return "poor"

    elif metric in ["correlation", "r_squared"]:
        if value > 0.99:
            return "excellent"
        elif value > 0.95:
            return "good"
        elif value > 0.90:
            return "moderate"
        else:
            return "poor"

    return "N/A"


def compare_data(
    sim_values: list[float],
    ref_values: list[float],
    metrics: list[str]
) -> dict[str, Any]:
    """Compare simulation and reference values using specified metrics."""
    results = {}

    for metric in metrics:
        if metric in METRIC_FUNCTIONS:
            try:
                value = METRIC_FUNCTIONS[metric](sim_values, ref_values)
                results[metric] = {
                    "value": value,
                    "interpretation": interpret_error(metric, value)
                }
            except Exception as e:
                results[metric] = {"error": str(e)}
        else:
            results[metric] = {"error": f"Unknown metric: {metric}"}

    return results


def main():
    parser = argparse.ArgumentParser(
        description="Compare simulation results with reference data"
    )
    parser.add_argument(
        "--simulation", "-s",
        required=True,
        help="Simulation result file (JSON or CSV)"
    )
    parser.add_argument(
        "--reference", "-r",
        required=True,
        help="Reference data file (JSON or CSV)"
    )
    parser.add_argument(
        "--metric", "-m",
        default="l2_error",
        help="Error metric(s), comma-separated (default: l2_error)"
    )
    parser.add_argument(
        "--field", "-f",
        help="Field name to compare (if data has multiple fields)"
    )
    parser.add_argument(
        "--interpolate",
        action="store_true",
        help="Interpolate reference to simulation coordinates"
    )
    parser.add_argument(
        "--all-metrics",
        action="store_true",
        help="Compute all available metrics"
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output as JSON"
    )

    args = parser.parse_args()

    try:
        # Load data
        if not os.path.exists(args.simulation):
            print(f"Error: Simulation file not found: {args.simulation}",
                  file=sys.stderr)
            sys.exit(1)

        if not os.path.exists(args.reference):
            print(f"Error: Reference file not found: {args.reference}",
                  file=sys.stderr)
            sys.exit(1)

        sim_data = load_data(args.simulation)
        ref_data = load_data(args.reference)

        # Extract values
        sim_values, sim_coords = extract_values(sim_data, args.field)
        ref_values, ref_coords = extract_values(ref_data, args.field)

        if sim_values is None:
            print("Error: Could not extract simulation values", file=sys.stderr)
            sys.exit(1)

        if ref_values is None:
            print("Error: Could not extract reference values", file=sys.stderr)
            sys.exit(1)

        # Interpolate if requested and coordinates available
        if args.interpolate and sim_coords and ref_coords:
            ref_values = interpolate_1d(sim_coords, ref_coords, ref_values)

        # Check lengths match
        if len(sim_values) != len(ref_values) and not args.interpolate:
            print(f"Warning: Length mismatch ({len(sim_values)} vs {len(ref_values)}). "
                  "Consider using --interpolate", file=sys.stderr)

            # Truncate to shorter length
            min_len = min(len(sim_values), len(ref_values))
            sim_values = sim_values[:min_len]
            ref_values = ref_values[:min_len]

        # Determine metrics to compute
        if args.all_metrics:
            metrics = list(METRIC_FUNCTIONS.keys())
        else:
            metrics = [m.strip() for m in args.metric.split(",")]

        # Compute comparison
        comparison_results = compare_data(sim_values, ref_values, metrics)

        # Build result
        result = {
            "simulation_file": args.simulation,
            "reference_file": args.reference,
            "simulation_points": len(sim_values),
            "reference_points": len(ref_values),
            "interpolated": args.interpolate and sim_coords is not None,
            "metrics": comparison_results
        }

        # Add summary statistics
        result["simulation_summary"] = {
            "min": min(sim_values),
            "max": max(sim_values),
            "mean": sum(sim_values) / len(sim_values)
        }
        result["reference_summary"] = {
            "min": min(ref_values),
            "max": max(ref_values),
            "mean": sum(ref_values) / len(ref_values)
        }

        # Output
        if args.json:
            print(json.dumps(result, indent=2))
        else:
            print("Comparison Results")
            print("=" * 50)
            print(f"Simulation: {args.simulation}")
            print(f"Reference: {args.reference}")
            print(f"Points compared: {len(sim_values)}")
            if args.interpolate:
                print("(Reference interpolated to simulation coordinates)")
            print()

            print("Simulation Summary:")
            print(f"  Range: [{result['simulation_summary']['min']:.6g}, "
                  f"{result['simulation_summary']['max']:.6g}]")
            print(f"  Mean: {result['simulation_summary']['mean']:.6g}")
            print()

            print("Reference Summary:")
            print(f"  Range: [{result['reference_summary']['min']:.6g}, "
                  f"{result['reference_summary']['max']:.6g}]")
            print(f"  Mean: {result['reference_summary']['mean']:.6g}")
            print()

            print("Error Metrics:")
            for metric, data in comparison_results.items():
                if "value" in data:
                    interp = data.get("interpretation", "")
                    print(f"  {metric}: {data['value']:.6g} ({interp})")
                else:
                    print(f"  {metric}: Error - {data.get('error', 'unknown')}")

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
