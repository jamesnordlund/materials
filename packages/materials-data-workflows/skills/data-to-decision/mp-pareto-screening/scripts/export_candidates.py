#!/usr/bin/env python3
"""Export Pareto frontier candidates to CSV or JSON.

Reads the structured JSON output of ``pareto_frontier.py`` and writes the
frontier array to a user-specified format (CSV or JSON) for downstream
consumption.

Exit codes:
    0 - success
    1 - input error (bad file, parse error, missing keys)
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from typing import Any

# ---------------------------------------------------------------------------
# Logging helpers
# ---------------------------------------------------------------------------

def _error(msg: str) -> None:
    """Print error to stderr and exit with code 1."""
    print(f"ERROR: {msg}", file=sys.stderr)
    sys.exit(1)


def _info(msg: str) -> None:
    """Print informational message to stderr."""
    print(msg, file=sys.stderr)


# ---------------------------------------------------------------------------
# Export logic
# ---------------------------------------------------------------------------

def _sorted_columns(frontier: list[dict[str, Any]]) -> list[str]:
    """Collect all keys across frontier records, sorted alphabetically."""
    keys: set[str] = set()
    for record in frontier:
        keys.update(record.keys())
    return sorted(keys)


def write_csv(
    frontier: list[dict[str, Any]],
    out_path: str,
) -> int:
    """Write frontier records to a CSV file.

    Columns are sorted alphabetically.  Rows are sorted by the ``rank``
    field when present (ascending), preserving original order as a tiebreaker.

    Returns the number of rows written.
    """
    if not frontier:
        # Write an empty file with no headers
        with open(out_path, "w", encoding="utf-8", newline="") as fh:
            fh.write("")
        return 0

    columns = _sorted_columns(frontier)

    # Sort rows by rank (if present), then by original order
    sorted_rows = sorted(
        frontier,
        key=lambda r: (r.get("rank", float("inf")), frontier.index(r)),
    )

    with open(out_path, "w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=columns, extrasaction="ignore")
        writer.writeheader()
        for row in sorted_rows:
            writer.writerow(row)

    return len(sorted_rows)


def write_json(
    frontier: list[dict[str, Any]],
    out_path: str,
) -> int:
    """Write frontier records to a JSON file with deterministic key ordering.

    Returns the number of records written.
    """
    json_str = json.dumps(frontier, indent=2, sort_keys=True)
    with open(out_path, "w", encoding="utf-8") as fh:
        fh.write(json_str)
        fh.write("\n")
    return len(frontier)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def build_parser() -> argparse.ArgumentParser:
    """Construct the argument parser."""
    parser = argparse.ArgumentParser(
        prog="export_candidates.py",
        description=(
            "Export Pareto frontier candidates to CSV or JSON."
        ),
    )
    parser.add_argument(
        "--input",
        required=True,
        metavar="PATH",
        help="Path to frontier JSON (output of pareto_frontier.py).",
    )
    parser.add_argument(
        "--format",
        required=True,
        choices=["csv", "json"],
        dest="out_format",
        help="Output format: csv or json.",
    )
    parser.add_argument(
        "--out",
        required=True,
        metavar="PATH",
        help="Output file path.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        dest="emit_json",
        help="Emit status JSON to stdout.",
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
            data = json.load(fh)
    except FileNotFoundError:
        _error(f"Input file not found: {args.input}")
    except json.JSONDecodeError as exc:
        _error(f"Invalid JSON in input file: {exc}")
    except OSError as exc:
        _error(f"Cannot read input file: {exc}")

    if not isinstance(data, dict):
        _error("Input JSON must be an object with a 'frontier' key.")

    frontier = data.get("frontier")
    if frontier is None:
        _error("Input JSON is missing the 'frontier' key.")
    if not isinstance(frontier, list):
        _error("The 'frontier' value must be an array.")

    # --- Write output -------------------------------------------------------
    try:
        if args.out_format == "csv":
            n_rows = write_csv(frontier, args.out)
        else:
            n_rows = write_json(frontier, args.out)
    except OSError as exc:
        _error(f"Failed to write output file: {exc}")

    _info(f"Wrote {n_rows} rows to {args.out}")

    # --- Emit status JSON ---------------------------------------------------
    if args.emit_json:
        status = {"status": "ok", "path": args.out, "rows": n_rows}
        print(json.dumps(status))

    sys.exit(0)


if __name__ == "__main__":
    main()
