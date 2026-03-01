#!/usr/bin/env python3
"""Compute the Pareto frontier for multi-objective materials screening.

Reads a JSON array of candidate materials, applies optional constraints,
computes non-dominated sorting (Pareto shells), crowding distance, and
emits structured JSON output.

Exit codes:
    0 - success
    1 - input error (bad file, parse error, invalid spec)
    2 - no candidates remain after filtering
"""

from __future__ import annotations

import argparse
import json
import math
import re
import sys
from typing import Any

# ---------------------------------------------------------------------------
# Parsing helpers
# ---------------------------------------------------------------------------

def parse_objectives(spec: str) -> list[dict[str, str]]:
    """Parse objective specification string into structured list.

    Args:
        spec: Comma-separated objective specs, e.g.
              ``"min:energy_above_hull_eV,max:band_gap_eV"``

    Returns:
        List of dicts with ``field`` and ``direction`` keys.

    Raises:
        SystemExit: If the spec is malformed.
    """
    objectives: list[dict[str, str]] = []
    for item in spec.split(","):
        item = item.strip()
        if not item:
            continue
        parts = item.split(":", maxsplit=1)
        if len(parts) != 2 or parts[0] not in ("min", "max"):
            _error(f"Invalid objective spec '{item}'. Expected 'min:field' or 'max:field'.")
        direction, field = parts
        if not field:
            _error(f"Empty field name in objective spec '{item}'.")
        objectives.append({"field": field, "direction": direction})
    if not objectives:
        _error("No objectives provided.")
    return objectives


_CONSTRAINT_RE = re.compile(r"^([A-Za-z_]\w*)(<=|>=)([+-]?\d+(?:\.\d+)?(?:[eE][+-]?\d+)?)$")


def parse_constraints(spec: str) -> list[dict[str, Any]]:
    """Parse constraint specification string.

    Args:
        spec: Comma-separated constraints, e.g.
              ``"energy_above_hull_eV<=0.05,band_gap_eV>=1.5"``

    Returns:
        List of dicts with ``field``, ``op``, and ``value`` keys.

    Raises:
        SystemExit: If a constraint is malformed.
    """
    constraints: list[dict[str, Any]] = []
    for item in spec.split(","):
        item = item.strip()
        if not item:
            continue
        m = _CONSTRAINT_RE.match(item)
        if not m:
            _error(
                f"Invalid constraint '{item}'. "
                "Expected 'field<=value' or 'field>=value'."
            )
        field, op, val_str = m.groups()
        constraints.append({"field": field, "op": op, "value": float(val_str)})
    return constraints


# ---------------------------------------------------------------------------
# Constraint filtering
# ---------------------------------------------------------------------------

def apply_constraints(
    candidates: list[dict[str, Any]],
    constraints: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Filter candidates that satisfy all constraints.

    Candidates with missing or non-numeric constraint fields are excluded
    (warning emitted to stderr).
    """
    if not constraints:
        return list(candidates)

    filtered: list[dict[str, Any]] = []
    for cand in candidates:
        passes = True
        for con in constraints:
            field = con["field"]
            val = cand.get(field)
            if val is None or not isinstance(val, (int, float)) or math.isnan(val):
                _warn(
                    f"Candidate '{cand.get('material_id', '?')}' excluded: "
                    f"missing or non-numeric field '{field}'."
                )
                passes = False
                break
            if con["op"] == "<=" and not (val <= con["value"]):
                passes = False
                break
            if con["op"] == ">=" and not (val >= con["value"]):
                passes = False
                break
        if passes:
            filtered.append(cand)
    return filtered


# ---------------------------------------------------------------------------
# Objective value extraction
# ---------------------------------------------------------------------------

def _obj_value(
    candidate: dict[str, Any],
    objective: dict[str, str],
) -> float:
    """Extract the objective value for a candidate, handling missing/NaN.

    For *min* objectives, missing/NaN maps to +inf (worst).
    For *max* objectives, missing/NaN maps to -inf (worst).
    """
    field = objective["field"]
    val = candidate.get(field)
    if val is None or not isinstance(val, (int, float)):
        _warn(
            f"Candidate '{candidate.get('material_id', '?')}' has "
            f"missing/non-numeric field '{field}'; treating as worst."
        )
        return float("inf") if objective["direction"] == "min" else float("-inf")
    if math.isnan(val):
        return float("inf") if objective["direction"] == "min" else float("-inf")
    return float(val)


# ---------------------------------------------------------------------------
# Pareto dominance
# ---------------------------------------------------------------------------

def _dominates(
    vals_a: list[float],
    vals_b: list[float],
    objectives: list[dict[str, str]],
) -> bool:
    """Return True if candidate A dominates candidate B.

    A dominates B iff A is at least as good in every objective and strictly
    better in at least one.  For *min* objectives, lower is better; for *max*,
    higher is better.

    Complexity: O(k) where k = number of objectives.
    """
    at_least_as_good = True
    strictly_better = False
    for va, vb, obj in zip(vals_a, vals_b, objectives, strict=True):
        if obj["direction"] == "min":
            if va > vb:
                at_least_as_good = False
                break
            if va < vb:
                strictly_better = True
        else:  # max
            if va < vb:
                at_least_as_good = False
                break
            if va > vb:
                strictly_better = True
    return at_least_as_good and strictly_better


def non_dominated_sort(
    obj_vals: list[list[float]],
    objectives: list[dict[str, str]],
) -> list[list[int]]:
    """Assign each candidate to a Pareto shell via iterative peeling.

    Args:
        obj_vals: Pre-computed objective values for all candidates
            (one list per candidate, one float per objective).
        objectives: Objective specifications.

    Returns a list of fronts, where ``fronts[0]`` contains the indices of
    first-front (non-dominated) candidates, ``fronts[1]`` the second front,
    and so on.

    Complexity: O(n^2 * k) per front extraction; total O(F * n^2 * k) where
    F is the number of fronts.  In the worst case F = n, giving O(n^3 * k),
    but for typical materials-screening data F << n.
    """
    n = len(obj_vals)
    remaining = set(range(n))
    fronts: list[list[int]] = []

    while remaining:
        front: list[int] = []
        remaining_list = sorted(remaining)  # deterministic ordering
        for i in remaining_list:
            dominated = False
            for j in remaining_list:
                if i == j:
                    continue
                if _dominates(obj_vals[j], obj_vals[i], objectives):
                    dominated = True
                    break
            if not dominated:
                front.append(i)
        fronts.append(front)
        remaining -= set(front)

    return fronts


# ---------------------------------------------------------------------------
# Crowding distance
# ---------------------------------------------------------------------------

def crowding_distance(
    indices: list[int],
    obj_vals: list[list[float]],
    objectives: list[dict[str, str]],
) -> dict[int, float]:
    """Compute NSGA-II crowding distance for candidates on a single front.

    Boundary candidates receive ``float('inf')``.

    Args:
        indices: Candidate indices belonging to this front.
        obj_vals: Pre-computed objective values for *all* candidates.
        objectives: Objective specifications.

    Returns:
        Mapping of candidate index to crowding distance.
    """
    n = len(indices)
    if n <= 2:
        return {idx: float("inf") for idx in indices}

    distances: dict[int, float] = {idx: 0.0 for idx in indices}
    k = len(objectives)

    for m in range(k):
        # Sort indices by the m-th objective value
        sorted_idx = sorted(indices, key=lambda i, _m=m: obj_vals[i][_m])
        obj_min = obj_vals[sorted_idx[0]][m]
        obj_max = obj_vals[sorted_idx[-1]][m]
        span = obj_max - obj_min

        # Boundary points get infinite distance
        distances[sorted_idx[0]] = float("inf")
        distances[sorted_idx[-1]] = float("inf")

        if span == 0.0:
            continue

        for j in range(1, n - 1):
            distances[sorted_idx[j]] += (
                (obj_vals[sorted_idx[j + 1]][m] - obj_vals[sorted_idx[j - 1]][m]) / span
            )

    return distances


# ---------------------------------------------------------------------------
# JSON sanitisation
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

_warned: set[str] = set()


def _warn(msg: str) -> None:
    """Emit a deduplicated warning to stderr."""
    if msg not in _warned:
        _warned.add(msg)
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
        prog="pareto_frontier.py",
        description=(
            "Compute Pareto frontier for multi-objective materials screening."
        ),
    )
    parser.add_argument(
        "--input",
        required=True,
        metavar="PATH",
        help="Path to candidates JSON file (array of objects).",
    )
    parser.add_argument(
        "--objectives",
        required=True,
        metavar="SPEC",
        help=(
            'Comma-separated objective specs: "min:field" or "max:field". '
            'Example: "min:energy_above_hull_eV,max:band_gap_eV"'
        ),
    )
    parser.add_argument(
        "--constraints",
        default=None,
        metavar="SPEC",
        help=(
            'Optional comma-separated constraints: "field<=value" or '
            '"field>=value". '
            'Example: "energy_above_hull_eV<=0.05,band_gap_eV>=1.5"'
        ),
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

    # --- Parse objectives ---------------------------------------------------
    objectives = parse_objectives(args.objectives)

    # --- Parse constraints --------------------------------------------------
    constraints: list[dict[str, Any]] = []
    if args.constraints:
        constraints = parse_constraints(args.constraints)

    # --- Load candidates ----------------------------------------------------
    try:
        with open(args.input, encoding="utf-8") as fh:
            candidates = json.load(fh)
    except FileNotFoundError:
        _error(f"Input file not found: {args.input}")
    except json.JSONDecodeError as exc:
        _error(f"Invalid JSON in input file: {exc}")

    if not isinstance(candidates, list):
        _error("Input JSON must be an array of objects.")

    total_candidates = len(candidates)
    if total_candidates == 0:
        _error("Input JSON array is empty.")

    # --- Apply constraints --------------------------------------------------
    filtered = apply_constraints(candidates, constraints)

    if not filtered:
        print("ERROR: No candidates remain after applying constraints.", file=sys.stderr)
        sys.exit(2)

    # --- Compute Pareto shells (non-dominated sorting) ----------------------
    obj_vals: list[list[float]] = [
        [_obj_value(c, obj) for obj in objectives] for c in filtered
    ]

    fronts = non_dominated_sort(obj_vals, objectives)

    # Build dominance rank map: front index -> rank (1-based)
    dominance_rank: dict[int, int] = {}
    for rank_idx, front in enumerate(fronts, start=1):
        for idx in front:
            dominance_rank[idx] = rank_idx

    # --- Compute crowding distance per front --------------------------------
    crowd_dist: dict[int, float] = {}
    for front in fronts:
        cd = crowding_distance(front, obj_vals, objectives)
        crowd_dist.update(cd)

    # --- Count how many candidates each frontier member dominates ------------
    frontier_indices = set(fronts[0])
    dominated_count_map: dict[int, int] = {}
    for i in frontier_indices:
        count = 0
        for j in range(len(filtered)):
            if j == i:
                continue
            if _dominates(obj_vals[i], obj_vals[j], objectives):
                count += 1
        dominated_count_map[i] = count

    # --- Build output -------------------------------------------------------
    frontier_out: list[dict[str, Any]] = []
    dominated_out: list[dict[str, Any]] = []
    scores: dict[str, dict[str, Any]] = {}

    for idx, cand in enumerate(filtered):
        mid = cand.get("material_id", f"unknown_{idx}")
        scores[mid] = {
            "crowding_distance": crowd_dist.get(idx, 0.0),
            "dominance_rank": dominance_rank.get(idx, 1),
        }
        if idx in frontier_indices:
            entry = dict(cand)
            entry["rank"] = dominance_rank[idx]
            entry["dominated_count"] = dominated_count_map.get(idx, 0)
            frontier_out.append(entry)
        else:
            dominated_out.append(dict(cand))

    output: dict[str, Any] = {
        "metadata": {
            "script": "pareto_frontier.py",
            "version": "1.0.0",
            "n_candidates": total_candidates,
            "n_objectives": len(objectives),
            "n_constraints": len(constraints),
            "n_after_constraints": len(filtered),
            "n_frontier": len(frontier_out),
        },
        "objectives": objectives,
        "constraints_applied": constraints,
        "frontier": frontier_out,
        "dominated": dominated_out,
        "scores": scores,
    }

    # --- Sanitize NaN/Inf ---------------------------------------------------
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
