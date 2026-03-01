#!/usr/bin/env python3
"""Build a reproducibility manifest from a list of tool call records.

Reads a JSON array of ``{tool_name, args, response_hash}`` objects,
computes deterministic hashes over the inputs and outputs, and emits a
structured manifest JSON.

Exit codes:
    0 - success
    1 - input error (bad file, parse error, schema violation)
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import UTC, datetime
from typing import Any

_VERSION = "1.0.0"

# ---------------------------------------------------------------------------
# Hashing helpers
# ---------------------------------------------------------------------------


def _sha256_hex(data: str) -> str:
    """Return the SHA-256 hex digest of *data* (UTF-8 encoded)."""
    return hashlib.sha256(data.encode("utf-8")).hexdigest()


def compute_input_hash(tool_calls: list[dict[str, Any]]) -> str:
    """Compute a deterministic SHA-256 hash over the full input payload.

    The input list is serialized with ``sort_keys=True`` to guarantee
    determinism regardless of key ordering in the source file.
    """
    canonical = json.dumps(tool_calls, sort_keys=True, separators=(",", ":"))
    return f"sha256:{_sha256_hex(canonical)}"


def compute_hash_of_outputs(tool_calls: list[dict[str, Any]]) -> str:
    """Compute a SHA-256 hash over the combined response hashes.

    Response hashes are sorted lexicographically and concatenated before
    hashing so the result is independent of tool-call ordering.
    """
    hashes = sorted(tc["response_hash"] for tc in tool_calls)
    combined = "".join(hashes)
    return f"sha256:{_sha256_hex(combined)}"


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------

_REQUIRED_KEYS = {"tool_name", "args", "response_hash"}


def validate_tool_calls(tool_calls: list[Any]) -> list[dict[str, Any]]:
    """Validate that every element has the required keys.

    Returns the validated list on success or calls ``_error`` on failure.
    """
    validated: list[dict[str, Any]] = []
    for idx, entry in enumerate(tool_calls):
        if not isinstance(entry, dict):
            _error(f"Item at index {idx} is not a JSON object.")
        missing = _REQUIRED_KEYS - entry.keys()
        if missing:
            _error(
                f"Item at index {idx} is missing required key(s): "
                f"{', '.join(sorted(missing))}."
            )
        if not isinstance(entry["tool_name"], str):
            _error(f"Item at index {idx}: 'tool_name' must be a string.")
        if not isinstance(entry["response_hash"], str):
            _error(f"Item at index {idx}: 'response_hash' must be a string.")
        validated.append(entry)
    return validated


# ---------------------------------------------------------------------------
# Manifest assembly
# ---------------------------------------------------------------------------


def build_manifest(tool_calls: list[dict[str, Any]]) -> dict[str, Any]:
    """Assemble the provenance manifest from validated tool call records.

    Returns the full output document including ``metadata`` and ``manifest``
    top-level keys.
    """
    now = datetime.now(UTC).isoformat()

    manifest: dict[str, Any] = {
        "metadata": {
            "script": "build_manifest.py",
            "version": _VERSION,
        },
        "manifest": {
            "inputs": {
                "input_hash": compute_input_hash(tool_calls),
                "tool_calls_count": len(tool_calls),
            },
            "tool_calls": tool_calls,
            "db_version": None,
            "timestamps": {
                "generated_at": now,
            },
            "hash_of_outputs": compute_hash_of_outputs(tool_calls),
        },
    }
    return manifest


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
# CLI
# ---------------------------------------------------------------------------


def build_parser() -> argparse.ArgumentParser:
    """Construct the argument parser."""
    parser = argparse.ArgumentParser(
        prog="build_manifest.py",
        description=(
            "Build a reproducibility manifest from tool call records."
        ),
    )
    parser.add_argument(
        "--input",
        required=True,
        metavar="PATH",
        help=(
            "Path to tool calls JSON file "
            "(array of {tool_name, args, response_hash} objects)."
        ),
    )
    parser.add_argument(
        "--json",
        action="store_true",
        dest="emit_json",
        help="Emit JSON to stdout (diagnostics still go to stderr).",
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

    if not isinstance(raw, list):
        _error("Input JSON must be an array of objects.")

    if len(raw) == 0:
        _error("Input JSON array is empty.")

    # --- Validate -----------------------------------------------------------
    tool_calls = validate_tool_calls(raw)

    # --- Build manifest -----------------------------------------------------
    output = build_manifest(tool_calls)

    # --- Serialize (deterministic) ------------------------------------------
    json_str = json.dumps(output, indent=2, sort_keys=True)

    # --- Write output -------------------------------------------------------
    if args.out:
        try:
            with open(args.out, "w", encoding="utf-8") as fh:
                fh.write(json_str)
                fh.write("\n")
            print(f"Manifest written to {args.out}", file=sys.stderr)
        except OSError as exc:
            _error(f"Failed to write output file: {exc}")

    if args.emit_json or not args.out:
        print(json_str)

    sys.exit(0)


if __name__ == "__main__":
    main()
