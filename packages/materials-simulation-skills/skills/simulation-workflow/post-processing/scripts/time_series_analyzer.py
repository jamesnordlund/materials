#!/usr/bin/env python3
"""
Time Series Analyzer - Analyze temporal evolution of simulation quantities.

Computes statistics, trends, moving averages, and detects steady state
in time series data from simulation history files.

Usage:
    python time_series_analyzer.py --input history.json --quantity energy --json
    python time_series_analyzer.py --input history.json \
        --quantity residual --detect-steady-state --json
"""

import argparse
import json
import math
import os
import sys
from typing import Any

# Import shared utilities
try:
    from ._utils import load_csv_file, load_json_file
except ImportError:
    # Fallback for standalone execution
    import importlib.util
    _utils_path = os.path.join(os.path.dirname(__file__), "_utils.py")
    spec = importlib.util.spec_from_file_location("_utils", _utils_path)
    _utils = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(_utils)
    load_json_file = _utils.load_json_file
    load_csv_file = _utils.load_csv_file


def load_time_series(filepath: str) -> dict[str, Any]:
    """Load time series data from file."""
    if filepath.endswith(".json"):
        data = load_json_file(filepath)
        # Handle nested history format
        if "history" in data:
            return data["history"]
        return data
    elif filepath.endswith(".csv"):
        return load_csv_file(filepath)
    else:
        raise ValueError(f"Unsupported format: {filepath}")


def extract_quantity(data: dict[str, Any], quantity: str) -> list[float] | None:
    """Extract a quantity time series from data."""
    # Try direct access
    if quantity in data:
        values = data[quantity]
        if isinstance(values, list):
            return [float(v) for v in values if isinstance(v, (int, float))]

    # Try nested access (e.g., "results.energy")
    parts = quantity.split(".")
    current = data
    for part in parts:
        if isinstance(current, dict) and part in current:
            current = current[part]
        else:
            return None

    if isinstance(current, list):
        return [float(v) for v in current if isinstance(v, (int, float))]

    return None


def get_time_axis(data: dict[str, Any]) -> list[float] | None:
    """Get time axis from data."""
    for key in ["time", "t", "timestep", "step", "iteration"]:
        if key in data:
            values = data[key]
            if isinstance(values, list):
                return [float(v) for v in values]
    return None


def compute_statistics(values: list[float]) -> dict[str, Any]:
    """Compute basic statistics for a time series."""
    if not values:
        return {
            "count": 0,
            "min": None,
            "max": None,
            "mean": None,
            "std": None,
            "first": None,
            "last": None
        }

    n = len(values)
    mean = sum(values) / n

    if n > 1:
        variance = sum((x - mean) ** 2 for x in values) / (n - 1)
        std = math.sqrt(variance)
    else:
        std = 0.0

    return {
        "count": n,
        "min": min(values),
        "max": max(values),
        "mean": mean,
        "std": std,
        "first": values[0],
        "last": values[-1]
    }


def compute_moving_average(values: list[float], window: int) -> list[float]:
    """Compute moving average with given window size."""
    if window < 1:
        window = 1
    if window > len(values):
        window = len(values)

    result = []
    for i in range(len(values)):
        start = max(0, i - window + 1)
        window_values = values[start:i + 1]
        result.append(sum(window_values) / len(window_values))

    return result


def compute_rate_of_change(
    values: list[float],
    times: list[float] | None = None
) -> list[float]:
    """Compute rate of change (derivative) of time series."""
    if len(values) < 2:
        return []

    rates = []
    for i in range(1, len(values)):
        if times:
            dt = times[i] - times[i - 1]
            rate = (values[i] - values[i - 1]) / dt if dt > 0 else 0.0
        else:
            rate = values[i] - values[i - 1]
        rates.append(rate)

    return rates


def detect_steady_state(
    values: list[float],
    tolerance: float = 1e-6,
    window: int = 10
) -> dict[str, Any]:
    """Detect if time series has reached steady state."""
    if len(values) < window:
        return {
            "reached": False,
            "reason": f"Not enough data points (need {window})",
            "index": None,
            "value": None
        }

    # Check last window values
    recent = values[-window:]
    mean = sum(recent) / len(recent)

    if mean == 0:
        relative_variation = max(abs(v) for v in recent)
    else:
        relative_variation = max(abs(v - mean) / abs(mean) for v in recent)

    is_steady = relative_variation < tolerance

    # Find when steady state was reached
    steady_index = None
    if is_steady:
        # Look backwards for when it became steady
        for i in range(len(values) - window, -1, -1):
            window_vals = values[i:i + window]
            w_mean = sum(window_vals) / len(window_vals)
            if w_mean == 0:
                w_var = max(abs(v) for v in window_vals)
            else:
                w_var = max(abs(v - w_mean) / abs(w_mean) for v in window_vals)

            if w_var >= tolerance:
                steady_index = i + window
                break

        if steady_index is None:
            steady_index = 0

    return {
        "reached": is_steady,
        "tolerance": tolerance,
        "window": window,
        "relative_variation": relative_variation,
        "index": steady_index,
        "value": mean if is_steady else None
    }


def detect_monotonicity(values: list[float]) -> dict[str, Any]:
    """Detect if time series is monotonic."""
    if len(values) < 2:
        return {"monotonic": True, "direction": "constant", "violations": 0}

    increasing = 0
    decreasing = 0
    constant = 0

    for i in range(1, len(values)):
        diff = values[i] - values[i - 1]
        if diff > 0:
            increasing += 1
        elif diff < 0:
            decreasing += 1
        else:
            constant += 1

    total = increasing + decreasing + constant

    if increasing == total - constant:
        return {"monotonic": True, "direction": "increasing", "violations": 0}
    elif decreasing == total - constant:
        return {"monotonic": True, "direction": "decreasing", "violations": 0}
    else:
        violations = min(increasing, decreasing)
        dominant = "increasing" if increasing > decreasing else "decreasing"
        return {
            "monotonic": False,
            "dominant_trend": dominant,
            "violations": violations,
            "increasing_steps": increasing,
            "decreasing_steps": decreasing
        }


def detect_oscillations(
    values: list[float],
    threshold: float = 0.01
) -> dict[str, Any]:
    """Detect oscillations in time series."""
    if len(values) < 3:
        return {"oscillating": False, "zero_crossings": 0}

    # Compute detrended values (remove mean)
    mean = sum(values) / len(values)
    detrended = [v - mean for v in values]

    # Count zero crossings
    zero_crossings = 0
    for i in range(1, len(detrended)):
        if detrended[i - 1] * detrended[i] < 0:
            zero_crossings += 1

    # Estimate amplitude
    amplitude = (max(values) - min(values)) / 2
    relative_amplitude = amplitude / abs(mean) if mean != 0 else amplitude

    # Significant oscillation if many zero crossings and notable amplitude
    is_oscillating = (
        zero_crossings > len(values) / 10 and
        relative_amplitude > threshold
    )

    return {
        "oscillating": is_oscillating,
        "zero_crossings": zero_crossings,
        "amplitude": amplitude,
        "relative_amplitude": relative_amplitude,
        "frequency_estimate": zero_crossings / (2 * len(values)) if len(values) > 0 else 0
    }


def compute_convergence_rate(
    values: list[float],
    target: float | None = None
) -> dict[str, Any]:
    """Estimate convergence rate from a time series.

    Fits a linear regression to log(|value - target|) vs iteration index
    to estimate the per-iteration decay factor.

    Args:
        values: Time series of values (e.g., residuals, errors, field quantities).
        target: Target value the series is converging to.
            - For residuals / error norms: use 0.0 (residuals should decay
              to zero).
            - For field values approaching steady state: use the known
              steady-state value, or None to auto-estimate from the final
              value.
            If None (the default), the function infers the target using a
            heuristic: 0.0 when all recent values are strictly positive
            (typical of residual norms), otherwise the final value in the
            series.

    Returns:
        Dictionary with convergence rate, type, iterations per decade,
        and the target value used.
    """
    if len(values) < 3:
        return {"rate": None, "type": "unknown"}

    # If no explicit target, infer from the data:
    #   - All-positive tail (typical of residual norms) -> target 0.0
    #   - Otherwise (e.g. field values oscillating around a limit) -> final value
    if target is None:
        tail = values[-min(10, len(values)):]
        target = 0.0 if all(v > 0 for v in tail) else values[-1]

    # Compute errors
    errors = [abs(v - target) for v in values]
    errors = [e for e in errors if e > 0]  # Remove zeros for log

    if len(errors) < 3:
        return {"rate": None, "type": "unknown"}

    # Estimate rate from log(error) vs iteration
    # Linear regression on log(errors)
    log_errors = [math.log(e) for e in errors]
    n = len(log_errors)
    x = list(range(n))
    x_mean = sum(x) / n
    y_mean = sum(log_errors) / n

    numerator = sum((x[i] - x_mean) * (log_errors[i] - y_mean) for i in range(n))
    denominator = sum((x[i] - x_mean) ** 2 for i in range(n))

    if denominator > 0:
        slope = numerator / denominator
        rate = math.exp(slope)
    else:
        rate = None

    # Classify convergence
    if rate is None:
        conv_type = "unknown"
    elif rate > 0.99:
        conv_type = "stalled"
    elif rate > 0.9:
        conv_type = "slow"
    elif rate > 0.5:
        conv_type = "linear"
    else:
        conv_type = "fast"

    return {
        "rate": rate,
        "type": conv_type,
        "target_used": target,
        "iterations_per_decade": -1 / math.log10(rate) if rate and rate < 1 else None
    }


def main():
    parser = argparse.ArgumentParser(
        description="Analyze time series data from simulations"
    )
    parser.add_argument(
        "--input", "-i",
        required=True,
        help="Input file (JSON or CSV)"
    )
    parser.add_argument(
        "--quantity", "-q",
        required=True,
        help="Quantity to analyze"
    )
    parser.add_argument(
        "--window", "-w",
        type=int,
        default=10,
        help="Window size for moving average (default: 10)"
    )
    parser.add_argument(
        "--detect-steady-state",
        action="store_true",
        help="Detect if steady state reached"
    )
    parser.add_argument(
        "--tolerance",
        type=float,
        default=1e-6,
        help="Tolerance for steady state detection (default: 1e-6)"
    )
    parser.add_argument(
        "--target",
        type=float,
        default=None,
        help="Target value for convergence rate (default: None for auto-detect; "
             "0.0 for residuals, final value otherwise)"
    )
    parser.add_argument(
        "--include-smoothed",
        action="store_true",
        help="Include smoothed data in output"
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output as JSON"
    )

    args = parser.parse_args()

    try:
        # Load data
        if not os.path.exists(args.input):
            print(f"Error: File not found: {args.input}", file=sys.stderr)
            sys.exit(1)

        data = load_time_series(args.input)

        # Extract quantity
        values = extract_quantity(data, args.quantity)
        if values is None:
            available = list(data.keys())
            print(f"Error: Quantity '{args.quantity}' not found. "
                  f"Available: {available}", file=sys.stderr)
            sys.exit(1)

        if not values:
            print(f"Error: No numeric data in '{args.quantity}'", file=sys.stderr)
            sys.exit(1)

        # Get time axis if available
        times = get_time_axis(data)

        # Compute analysis
        result = {
            "source_file": args.input,
            "quantity": args.quantity,
            "statistics": compute_statistics(values),
            "monotonicity": detect_monotonicity(values),
            "oscillations": detect_oscillations(values),
            "convergence": compute_convergence_rate(values, target=args.target)
        }

        if times:
            result["time_range"] = {
                "start": times[0],
                "end": times[-1],
                "duration": times[-1] - times[0]
            }

        if args.detect_steady_state:
            result["steady_state"] = detect_steady_state(
                values,
                tolerance=args.tolerance,
                window=args.window
            )

        if args.include_smoothed:
            result["smoothed_values"] = compute_moving_average(values, args.window)
            result["rate_of_change"] = compute_rate_of_change(values, times)

        # Output
        if args.json:
            print(json.dumps(result, indent=2))
        else:
            print(f"Time Series Analysis: {args.quantity}")
            print(f"Source: {args.input}")
            print()

            stats = result["statistics"]
            print("Statistics:")
            print(f"  Count: {stats['count']}")
            print(f"  Range: [{stats['min']:.6g}, {stats['max']:.6g}]")
            print(f"  Mean: {stats['mean']:.6g}")
            print(f"  Std: {stats['std']:.6g}")
            print(f"  First: {stats['first']:.6g}")
            print(f"  Last: {stats['last']:.6g}")

            mono = result["monotonicity"]
            print(f"\nMonotonicity: {mono.get('direction', mono.get('dominant_trend', 'N/A'))}")
            if not mono["monotonic"]:
                print(f"  Violations: {mono['violations']}")

            osc = result["oscillations"]
            if osc["oscillating"]:
                print("\nOscillations detected:")
                print(f"  Amplitude: {osc['amplitude']:.6g}")
                print(f"  Frequency: ~{osc['frequency_estimate']:.4f} per step")

            conv = result["convergence"]
            if conv["rate"] is not None:
                print("\nConvergence:")
                print(f"  Type: {conv['type']}")
                print(f"  Rate: {conv['rate']:.4f}")
                if conv.get("target_used") is not None:
                    print(f"  Target: {conv['target_used']:.6g}")
                if conv["iterations_per_decade"]:
                    print(f"  Iterations per decade: {conv['iterations_per_decade']:.1f}")

            if "steady_state" in result:
                ss = result["steady_state"]
                print("\nSteady State:")
                print(f"  Reached: {ss['reached']}")
                if ss["reached"]:
                    print(f"  At index: {ss['index']}")
                    print(f"  Value: {ss['value']:.6g}")
                else:
                    print(f"  Variation: {ss['relative_variation']:.2e}")
                    print(f"  (need < {ss['tolerance']:.2e})")

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
