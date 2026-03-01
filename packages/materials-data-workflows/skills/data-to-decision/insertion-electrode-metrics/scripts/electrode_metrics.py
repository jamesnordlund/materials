#!/usr/bin/env python3
"""Compute key performance metrics for an insertion electrode material.

Reads a normalized electrode document JSON (from ``mp_insertion_electrodes_search``)
and computes derived metrics: average voltage, gravimetric/volumetric capacity,
energy density, and stability flags.

Exit codes:
    0 - success
    1 - input error (bad file, parse error, missing required fields)
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
# Field extraction (R-ERR-005: missing fields -> null + warning)
# ---------------------------------------------------------------------------

def _get_numeric(doc: dict[str, Any], field: str) -> float | None:
    """Extract a numeric field from the document.

    Returns the value as a float if present and numeric, otherwise ``None``
    with a warning logged to stderr.
    """
    val = doc.get(field)
    if val is None:
        _warn(f"Missing field '{field}'; substituting null.")
        return None
    if not isinstance(val, (int, float)):
        _warn(f"Non-numeric field '{field}' (got {type(val).__name__}); substituting null.")
        return None
    if math.isnan(val) or math.isinf(val):
        _warn(f"Field '{field}' is NaN or Inf; substituting null.")
        return None
    return float(val)


def _get_bool(doc: dict[str, Any], field: str) -> bool | None:
    """Extract a boolean field, returning None if missing."""
    val = doc.get(field)
    if val is None:
        _warn(f"Missing field '{field}'; substituting null.")
        return None
    if isinstance(val, bool):
        return val
    _warn(f"Non-boolean field '{field}' (got {type(val).__name__}); substituting null.")
    return None


# ---------------------------------------------------------------------------
# Metrics computation
# ---------------------------------------------------------------------------

def compute_metrics(doc: dict[str, Any]) -> dict[str, Any]:
    """Compute electrode metrics from a normalized electrode document.

    Args:
        doc: Normalized electrode document dictionary.

    Returns:
        Dictionary containing computed metrics.
    """
    material_id = doc.get("material_id")
    if material_id is None:
        _error("Input document missing required field 'material_id'.")
    working_ion = doc.get("working_ion")
    if working_ion is None:
        _error("Input document missing required field 'working_ion'.")

    avg_voltage = _get_numeric(doc, "average_voltage")
    grav_capacity = _get_numeric(doc, "capacity_grav")
    vol_capacity = _get_numeric(doc, "capacity_vol")

    # Energy density = avg_voltage * grav_capacity (Wh/kg = V * mAh/g)
    if avg_voltage is not None and grav_capacity is not None:
        energy_density = avg_voltage * grav_capacity
    else:
        energy_density = None
        if avg_voltage is None or grav_capacity is None:
            _warn(
                "Cannot compute energy_density_Wh_kg: "
                "requires average_voltage and capacity_grav."
            )

    # Stability metrics (eV above hull; 0.0 = on hull / stable)
    stability_charge = _get_numeric(doc, "stability_charge")
    stability_discharge = _get_numeric(doc, "stability_discharge")
    max_delta_volume = _get_numeric(doc, "max_delta_volume")

    stability_flags: dict[str, Any] = {
        "stability_charge_eV": stability_charge,
        "stability_discharge_eV": stability_discharge,
        "max_delta_volume_pct": max_delta_volume,
    }

    return {
        "metadata": {
            "script": "electrode_metrics.py",
            "version": "1.0.0",
        },
        "material_id": material_id,
        "working_ion": working_ion,
        "avg_voltage_V": avg_voltage,
        "grav_capacity_mAh_g": grav_capacity,
        "vol_capacity_mAh_cm3": vol_capacity,
        "energy_density_Wh_kg": energy_density,
        "stability_flags": stability_flags,
    }


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def build_parser() -> argparse.ArgumentParser:
    """Construct the argument parser."""
    parser = argparse.ArgumentParser(
        prog="electrode_metrics.py",
        description=(
            "Compute key performance metrics for an insertion electrode material."
        ),
    )
    parser.add_argument(
        "--input",
        required=True,
        metavar="PATH",
        help="Path to normalized electrode document JSON.",
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
            doc = json.load(fh)
    except FileNotFoundError:
        _error(f"Input file not found: {args.input}")
    except json.JSONDecodeError as exc:
        _error(f"Invalid JSON in input file: {exc}")
    except OSError as exc:
        _error(f"Cannot read input file: {exc}")

    if not isinstance(doc, dict):
        _error("Input JSON must be an object (electrode document).")

    # --- Compute metrics ----------------------------------------------------
    output = compute_metrics(doc)

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
