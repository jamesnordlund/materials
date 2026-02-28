"""Shared validators and error-response helper for MCP Materials tools."""

from __future__ import annotations

import json
import re
from typing import Any

from mcp.types import ToolAnnotations

from mcp_materials._sanitize import sanitize_message

# ============================================================================
# Existing validators (moved from server.py)
# ============================================================================

_MATERIAL_ID_RE = re.compile(r"^(mp|mvc)-\d+$")


def _validate_material_id(mid: str) -> str | None:
    """Return an error message if material_id is invalid, else None."""
    if not mid or not _MATERIAL_ID_RE.match(mid):
        return f"Invalid material_id '{mid}'. Expected format: 'mp-XXXXX'"
    return None


def _validate_max_results(n: int) -> str | None:
    """Return an error message if max_results is out of range, else None."""
    if n < 1:
        return "max_results must be at least 1"
    if n > 100:
        return "max_results must be at most 100"
    return None


_FORMULA_RE = re.compile(r"^[A-Z][a-zA-Z0-9().\-]*$")


def _validate_formula(formula: str) -> str | None:
    """Return an error message if formula is invalid, else None."""
    if not formula or not formula.strip():
        return "formula must not be empty"
    if not _FORMULA_RE.match(formula.strip()):
        return f"Invalid formula '{formula}'. Expected a chemical formula like 'Fe2O3' or 'LiFePO4'"
    return None


def _validate_elements(elements: list[str]) -> str | None:
    """Return an error message if elements list is invalid, else None."""
    if not elements:
        return "elements list must not be empty"
    for el in elements:
        if not el or not re.match(r"^[A-Z][a-z]?$", el):
            return f"Invalid element symbol '{el}'. Expected 1-2 letter symbol like 'Fe' or 'O'"
    return None


# ============================================================================
# Error response helper (moved from server.py)
# ============================================================================


def _error_response(
    message: str,
    *,
    error_category: str = "internal_error",
    **extra: Any,
) -> str:
    """Build a JSON error response string with sanitized message.

    The message is passed through :func:`sanitize_message` to strip any
    API keys that may have leaked into error text.

    Args:
        message: Human-readable error description.
        error_category: Classification of the error (e.g. ``"validation_error"``,
            ``"auth_error"``, ``"api_error"``, ``"internal_error"``).
        **extra: Additional string-keyed, JSON-serializable values merged
            into the response dict.  Cannot override the ``"error"`` key.

    Returns:
        A JSON-encoded string with at least ``"error"`` and
        ``"error_category"`` keys.
    """
    sanitized = sanitize_message(message)
    response: dict[str, Any] = {
        "error": sanitized,
        "error_category": error_category,
    }
    response.update(extra)
    # Prevent **extra from overriding the error key.
    response["error"] = sanitized
    return json.dumps(response, indent=2)


# ============================================================================
# Validators
# ============================================================================

_PROJECT_NAME_RE = re.compile(r"^[a-zA-Z0-9_]{3,31}$")


def _validate_project_name(name: str) -> str | None:
    """Return error message if project name is invalid, else None."""
    if not name or not _PROJECT_NAME_RE.match(name):
        return (
            f"Invalid project name '{name}'. "
            "Expected 3-31 alphanumeric/underscore characters."
        )
    return None


_OBJECT_ID_RE = re.compile(r"^[0-9a-f]{24}$")


def _validate_object_id(oid: str, entity_type: str = "object") -> str | None:
    """Return error message if ObjectId is invalid, else None."""
    if not oid or not _OBJECT_ID_RE.match(oid):
        return f"Invalid {entity_type} ID '{oid}'. Expected 24-character hex string."
    return None


def _validate_per_page(n: int) -> str | None:
    """Return error message if per_page is out of range, else None."""
    if n < 1:
        return "per_page must be at least 1"
    if n > 100:
        return "per_page must be at most 100"
    return None


def _validate_page(n: int) -> str | None:
    """Return error message if page is out of range, else None."""
    if n < 1:
        return "page must be at least 1"
    return None


# ============================================================================
# Shared MCP tool annotations
# ============================================================================

TOOL_ANNOTATIONS = ToolAnnotations(
    readOnlyHint=True,
    destructiveHint=False,
    idempotentHint=True,
    openWorldHint=False,
)
