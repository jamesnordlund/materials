"""Standardized output builder for MCP tool responses."""

from __future__ import annotations

import json
import math


def _sanitize_floats(obj):
    """Recursively replace NaN and Inf float values with None."""
    if isinstance(obj, float) and (math.isnan(obj) or math.isinf(obj)):
        return None
    if isinstance(obj, dict):
        return {k: _sanitize_floats(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_sanitize_floats(v) for v in obj]
    return obj


def _build_response(
    tool_name: str,
    query: dict,
    records: list[dict],
    *,
    db_version: str | None = None,
    db_version_error: str | None = None,
    query_time_ms: float = 0,
    note: str | None = None,
) -> str:
    """Build a standardized JSON response string.

    - Replaces NaN/Inf with None in all records (R-OUT-003).
    - Uses unit-suffixed key names (R-OUT-002).
    - Includes metadata.db_version (R-MCP-004).
    - Handles db_version fallback (R-ERR-006).
    """
    errors: list[str] = []
    if db_version_error:
        errors.append(f"db_version unavailable: {db_version_error}")
    response = {
        "metadata": {
            "db_version": db_version,
            "tool_name": tool_name,
            "query_time_ms": round(query_time_ms, 1),
        },
        "query": query,
        "count": len(records),
        "records": _sanitize_floats(records),
        "errors": errors,
    }
    if db_version_error:
        response["metadata"]["db_version_error"] = db_version_error
    if note:
        response["note"] = note
    return json.dumps(response, indent=2, default=str)
