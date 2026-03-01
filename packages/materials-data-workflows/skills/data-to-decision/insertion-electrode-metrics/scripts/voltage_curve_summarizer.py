#!/usr/bin/env python3
"""Summarize a voltage curve for an insertion electrode material.

Reads a JSON array of ``{x, voltage_V}`` data points (charge/discharge curve)
and computes summary statistics: step count, min/max/avg voltage, plateau
detection, and hysteresis proxy.

Exit codes:
    0 - success
    1 - input error (bad file, parse error, invalid data)
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from typing import Any

# ---------------------------------------------------------------------------
# JSON sanitisation (R-OUT-003)
# ---------------------------------------------------------------------------

def _sanitize_value(v: Any) -> Any:
    """Replace NaN / Inf / -Inf with None for JSON serialization."""
    if isinstance(v, float) and (math.isnan(v) or math.isinf(v)):
        return None
    return v


def _sanitize(obj: Any) -> Any:
    """Recursively sanitize a nested structure for JSON."""
    if isinstance(obj, dict):
        return {k: _sanitize(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_sanitize(item) for item in obj]
    return _sanitize_value(obj)


# ---------------------------------------------------------------------------
# Logging helpers
# ---------------------------------------------------------------------------

def _warn(msg: str) -> None:
    """Emit a warning to stderr."""
    print(f"WARNING: {msg}", file=sys.stderr)


def _error(msg: str) -> None:
    """Print error to stderr and exit with code 1."""
    print(f"ERROR: {msg}", file=sys.stderr)
    sys.exit(1)


# ---------------------------------------------------------------------------
# Data validation
# ---------------------------------------------------------------------------

def _validate_points(raw_points: list[Any]) -> list[dict[str, float]]:
    """Validate and normalize voltage curve data points.

    Each point must have ``x`` and ``voltage_V`` numeric fields.
    Invalid points are skipped with a warning.

    Returns:
        List of validated points sorted by ``x``.
    """
    valid: list[dict[str, float]] = []
    for i, pt in enumerate(raw_points):
        if not isinstance(pt, dict):
            _warn(f"Point {i}: expected object, got {type(pt).__name__}; skipping.")
            continue

        x_val = pt.get("x")
        v_val = pt.get("voltage_V")

        if x_val is None or v_val is None:
            _warn(f"Point {i}: missing 'x' or 'voltage_V'; skipping.")
            continue

        if not isinstance(x_val, (int, float)) or not isinstance(v_val, (int, float)):
            _warn(f"Point {i}: non-numeric 'x' or 'voltage_V'; skipping.")
            continue

        if math.isnan(x_val) or math.isinf(x_val):
            _warn(f"Point {i}: 'x' is NaN or Inf; skipping.")
            continue
        if math.isnan(v_val) or math.isinf(v_val):
            _warn(f"Point {i}: 'voltage_V' is NaN or Inf; skipping.")
            continue

        valid.append({"x": float(x_val), "voltage_V": float(v_val)})

    # Sort by x (capacity fraction)
    valid.sort(key=lambda p: p["x"])
    return valid


# ---------------------------------------------------------------------------
# Plateau detection
# ---------------------------------------------------------------------------

def detect_plateaus(
    points: list[dict[str, float]],
    voltage_tolerance: float = 0.05,
    min_fraction: float = 0.1,
) -> list[dict[str, float]]:
    """Detect voltage plateaus in the curve.

    A plateau is a contiguous region where the voltage stays within
    ``voltage_tolerance`` V of the segment's mean voltage, spanning at least
    ``min_fraction`` of the total capacity range.

    Args:
        points: Sorted list of ``{x, voltage_V}`` points.
        voltage_tolerance: Maximum voltage deviation from mean to consider
            part of the same plateau (in V).
        min_fraction: Minimum capacity fraction span for a valid plateau.

    Returns:
        List of plateau dicts with ``voltage_V`` (mean) and
        ``capacity_fraction`` (span).
    """
    if len(points) < 2:
        return []

    total_x_range = points[-1]["x"] - points[0]["x"]
    if total_x_range <= 0:
        return []

    plateaus: list[dict[str, float]] = []
    i = 0
    n = len(points)

    while i < n:
        # Start a potential plateau segment
        seg_start = i
        seg_voltages = [points[i]["voltage_V"]]
        running_mean = points[i]["voltage_V"]

        j = i + 1
        while j < n:
            candidate_mean = (running_mean * len(seg_voltages) + points[j]["voltage_V"]) / (
                len(seg_voltages) + 1
            )
            if abs(points[j]["voltage_V"] - candidate_mean) <= voltage_tolerance:
                seg_voltages.append(points[j]["voltage_V"])
                running_mean = candidate_mean
                j += 1
            else:
                break

        # Check if segment qualifies as a plateau
        x_span = points[j - 1]["x"] - points[seg_start]["x"]
        frac = x_span / total_x_range if total_x_range > 0 else 0.0

        if frac >= min_fraction and len(seg_voltages) >= 2:
            mean_v = sum(seg_voltages) / len(seg_voltages)
            plateaus.append({
                "voltage_V": round(mean_v, 4),
                "capacity_fraction": round(frac, 4),
            })

        # Advance past this segment
        i = j if j > i + 1 else i + 1

    return plateaus


# ---------------------------------------------------------------------------
# Summary computation
# ---------------------------------------------------------------------------

def summarize_curve(points: list[dict[str, float]]) -> dict[str, Any]:
    """Compute voltage curve summary statistics.

    Args:
        points: Validated and sorted list of ``{x, voltage_V}`` points.

    Returns:
        Summary dictionary.
    """
    if not points:
        return {
            "metadata": {"script": "voltage_curve_summarizer.py", "version": "1.0.0"},
            "n_steps": 0,
            "min_voltage_V": None,
            "max_voltage_V": None,
            "avg_voltage_V": None,
            "plateaus": [],
            "hysteresis_proxy_V": None,
        }

    voltages = [p["voltage_V"] for p in points]
    n_steps = len(points)
    min_v = min(voltages)
    max_v = max(voltages)
    avg_v = sum(voltages) / len(voltages)

    plateaus = detect_plateaus(points)

    # Hysteresis proxy: difference between max and min voltage.
    # A true hysteresis measure would require both charge and discharge curves;
    # with a single curve we report the voltage spread as a proxy, or null
    # if there are fewer than 2 points.
    hysteresis_proxy: float | None = None
    if n_steps >= 2:
        hysteresis_proxy = round(max_v - min_v, 4)

    return {
        "metadata": {"script": "voltage_curve_summarizer.py", "version": "1.0.0"},
        "n_steps": n_steps,
        "min_voltage_V": round(min_v, 4),
        "max_voltage_V": round(max_v, 4),
        "avg_voltage_V": round(avg_v, 4),
        "plateaus": plateaus,
        "hysteresis_proxy_V": hysteresis_proxy,
    }


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def build_parser() -> argparse.ArgumentParser:
    """Construct the argument parser."""
    parser = argparse.ArgumentParser(
        prog="voltage_curve_summarizer.py",
        description=(
            "Summarize a voltage curve for an insertion electrode material."
        ),
    )
    parser.add_argument(
        "--input",
        required=True,
        metavar="PATH",
        help="Path to voltage curve JSON (array of {x, voltage_V} points).",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        dest="emit_json",
        help="Emit JSON to stdout (logs to stderr).",
    )
    parser.add_argument(
        "--out",
        default=None,
        metavar="PATH",
        help="Write output to file instead of stdout.",
    )
    return parser


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main(argv: list[str] | None = None) -> None:
    """Entry point."""
    parser = build_parser()
    args = parser.parse_args(argv)

    # --- Load input ---------------------------------------------------------
    try:
        with open(args.input, encoding="utf-8") as fh:
            raw = json.load(fh)
    except FileNotFoundError:
        _error(f"Input file not found: {args.input}")
    except json.JSONDecodeError as exc:
        _error(f"Invalid JSON in input file: {exc}")
    except OSError as exc:
        _error(f"Cannot read input file: {exc}")

    if not isinstance(raw, list):
        _error("Input JSON must be an array of {x, voltage_V} point objects.")

    # --- Validate points ----------------------------------------------------
    points = _validate_points(raw)

    if not points:
        _warn("No valid data points after validation; producing empty summary.")

    # --- Compute summary ----------------------------------------------------
    output = summarize_curve(points)

    # --- Sanitize NaN/Inf (R-OUT-003) ---------------------------------------
    output = _sanitize(output)

    # --- Serialize ----------------------------------------------------------
    json_str = json.dumps(output, indent=2)

    if args.out:
        try:
            with open(args.out, "w", encoding="utf-8") as fh:
                fh.write(json_str)
                fh.write("\n")
            print(f"Output written to {args.out}", file=sys.stderr)
        except OSError as exc:
            _error(f"Failed to write output file: {exc}")

    if args.emit_json or not args.out:
        print(json_str)

    sys.exit(0)


if __name__ == "__main__":
    main()
