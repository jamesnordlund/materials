"""MPContribs tool functions (8 tools).

Each function is a plain ``async def`` registered via ``register_contribs_tools(mcp)``.
"""

from __future__ import annotations

import asyncio
import json
import math
import re
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from mcp.server.fastmcp import FastMCP

from mcp_materials._error_handler import contribs_error_handler
from mcp_materials._prereqs import HAS_MPCONTRIBS, _check_contribs_prerequisites
from mcp_materials._sanitize import sanitize_message
from mcp_materials._validation import (
    TOOL_ANNOTATIONS,
    _error_response,
    _validate_material_id,
    _validate_max_results,
    _validate_object_id,
    _validate_page,
    _validate_per_page,
    _validate_project_name,
)

# Conditional imports -- guarded by HAS_MPCONTRIBS to avoid ImportError
if HAS_MPCONTRIBS:
    from bravado.exception import HTTPError
    from mpcontribs.client import Client as ContribsClient

    try:
        from mpcontribs.client import MPContribsClientError
    except ImportError:
        # Some versions of mpcontribs-client do not expose MPContribsClientError.
        # The contribs_error_handler decorator performs its own lazy import with
        # the same fallback, so setting None here keeps the module-level symbol
        # available without breaking older client installations.
        MPContribsClientError = None
else:
    ContribsClient = None
    HTTPError = None
    # See note above -- kept as None so the symbol exists at module level even
    # when mpcontribs is not installed.
    MPContribsClientError = None

_DATA_FILTER_KEY_RE = re.compile(
    r"^data__[a-zA-Z_][a-zA-Z0-9_]*(__(?:gte|lte|gt|lt|contains|exact|value))*$"
)

_ALLOWED_FILTER_VALUE_TYPES = (str, int, float, bool)

_RESERVED_KWARGS = frozenset({
    "project", "_limit", "_skip", "_fields", "_sort",
    "identifier", "formula__contains",
})

# Timeout in seconds for upstream API calls via asyncio.to_thread.
API_TIMEOUT: float = 60.0

# Maximum number of rows to materialize into memory for table operations.
# Even if user requests -1 (all rows), this cap is enforced to prevent
# unbounded memory growth from extremely large tables.
MAX_ROWS_ABSOLUTE: int = 100_000

_TIMEOUT_MSG = (
    "Request timed out after {timeout} seconds. "
    "The upstream API may be slow or unresponsive. Please try again later."
)


_contribs_client = None
_contribs_api_key = None


def _get_contribs_client(api_key):
    """Return a cached ContribsClient, creating one if needed."""
    global _contribs_client, _contribs_api_key  # noqa: PLW0603
    if _contribs_client is None or _contribs_api_key != api_key:
        _contribs_client = ContribsClient(apikey=api_key)
        _contribs_api_key = api_key
    return _contribs_client


def _reset_contribs_client():
    """Clear the cached client. Intended for use in tests."""
    global _contribs_client, _contribs_api_key  # noqa: PLW0603
    _contribs_client = None
    _contribs_api_key = None


def _is_injection_string(value: str) -> bool:
    """Return True if a string value looks like a MongoDB/NoSQL injection pattern."""
    return isinstance(value, str) and value.startswith("$")


def _validate_filter_value(key: str, value: object) -> str | None:
    """Return error message if a single data_filters value is invalid, else None.

    Allowed values are primitives (str, int, float, bool) or flat lists of
    those primitives.  Nested dicts, None, and strings that start with '$'
    (potential MongoDB operator injection) are rejected.
    """
    if value is None:
        return (
            f"Invalid data_filters value for '{key}': None is not allowed."
        )

    if isinstance(value, dict):
        return (
            f"Invalid data_filters value for '{key}': nested objects/dicts are not "
            "allowed. Only simple types (str, int, float, bool) or lists of "
            "simple types are permitted."
        )

    if isinstance(value, list):
        for i, item in enumerate(value):
            if not isinstance(item, _ALLOWED_FILTER_VALUE_TYPES):
                return (
                    f"Invalid data_filters value for '{key}': list item at index "
                    f"{i} has type '{type(item).__name__}'. Only str, int, float, "
                    "bool are allowed inside lists."
                )
            if isinstance(item, str) and _is_injection_string(item):
                return (
                    f"Invalid data_filters value for '{key}': list item at index "
                    f"{i} contains a potential injection pattern ('{item}'). "
                    "String values must not start with '$'."
                )
        return None

    if not isinstance(value, _ALLOWED_FILTER_VALUE_TYPES):
        return (
            f"Invalid data_filters value for '{key}': type '{type(value).__name__}' "
            "is not allowed. Only str, int, float, bool, or lists of those types "
            "are permitted."
        )

    if isinstance(value, str) and _is_injection_string(value):
        return (
            f"Invalid data_filters value for '{key}': string '{value}' looks like "
            "a potential injection pattern. String values must not start with '$'."
        )

    return None


def _validate_data_filters(data_filters: dict) -> str | None:
    """Return error message if any data_filters key or value is invalid, else None.

    Keys must match _DATA_FILTER_KEY_RE and must not collide with
    _RESERVED_KWARGS.  Values must be simple primitives (str, int, float,
    bool) or flat lists of those primitives.  Nested dicts, None values,
    and strings resembling MongoDB operators (starting with '$') are rejected.
    """
    for key in data_filters:
        if key in _RESERVED_KWARGS:
            return (
                f"Reserved keyword '{key}' cannot be used in data_filters. "
                f"Use the dedicated parameter instead."
            )
        if not _DATA_FILTER_KEY_RE.match(key):
            return (
                f"Invalid data_filters key '{key}'. "
                "Keys must match pattern: data__<field>(__<operator>)* "
                "where operator is one of: gte, lte, gt, lt, contains, exact, value"
            )

    # Validate values (prevents API injection via nested objects or operators)
    for key, value in data_filters.items():
        err = _validate_filter_value(key, value)
        if err:
            return err

    return None


# ============================================================================
# HTTP error helper
# ============================================================================


def _handle_http_error(exc: Exception, entity_type: str, entity_id: str) -> str:
    """Map bravado HTTPError to structured error response with sanitization.

    Sanitizes the exception message to redact sensitive information including
    bearer tokens, URLs, API keys, and query parameters before returning the error.
    """
    status = getattr(exc, "status_code", None)
    if status == 403:
        return _error_response(
            "Permission denied. Check your API key has access to this project."
        )
    if status == 404:
        return _error_response(f"{entity_type.capitalize()} not found: {entity_id}")
    if status == 429:
        return _error_response("Rate limit exceeded. Please wait before retrying.")
    # Sanitize the exception message to redact sensitive information
    sanitized_exc_str = sanitize_message(str(exc))
    return _error_response(f"API error (HTTP {status}): {sanitized_exc_str}")


# ============================================================================
# Tool implementations
# ============================================================================


@contribs_error_handler("project")
async def contribs_search_projects(
    title: str | None = None,
    description: str | None = None,
    max_results: int = 10,
) -> str:
    """
    Search for MPContribs projects by title or description.

    Args:
        title: Filter projects by title substring match
        description: Filter projects by description substring match
        max_results: Maximum number of results to return (default: 10, max: 100)

    Returns:
        JSON with matching projects including name, title, description, authors, urls
    """
    err, api_key = _check_contribs_prerequisites()
    if err:
        return err

    validation_err = _validate_max_results(max_results)
    if validation_err:
        return _error_response(validation_err)

    def _query():
        client = _get_contribs_client(api_key)
        kwargs = {
            "_limit": max_results,
            "_fields": [
                "name", "title", "description", "authors", "urls",
            ],
        }
        if title is not None:
            kwargs["title__contains"] = title
        if description is not None:
            kwargs["description__icontains"] = description

        result = client.projects.queryProjects(**kwargs).result()
        projects = result.get("data", [])

        formatted = []
        for p in projects:
            formatted.append({
                "name": p.get("name", ""),
                "title": p.get("title", ""),
                "description": p.get("description", ""),
                "authors": p.get("authors", ""),
                "urls": p.get("urls", []),
            })

        return json.dumps({
            "count": len(formatted),
            "projects": formatted,
        }, indent=2)

    return await asyncio.wait_for(
        asyncio.to_thread(_query), timeout=API_TIMEOUT
    )


@contribs_error_handler("project")
async def contribs_get_project(
    project_name: str,
) -> str:
    """
    Get metadata for a specific MPContribs project.

    Args:
        project_name: The project name (3-31 alphanumeric or underscore characters)

    Returns:
        JSON with project metadata including columns, authors, references
    """
    err, api_key = _check_contribs_prerequisites()
    if err:
        return err

    validation_err = _validate_project_name(project_name)
    if validation_err:
        return _error_response(validation_err)

    def _query():
        client = _get_contribs_client(api_key)
        project = client.get_project(project_name)

        return json.dumps({
            "name": project.get("name", ""),
            "title": project.get("title", ""),
            "description": project.get("description", ""),
            "authors": project.get("authors", ""),
            "columns": project.get("columns", {}),
            "references": project.get("references", []),
        }, indent=2)

    return await asyncio.wait_for(
        asyncio.to_thread(_query), timeout=API_TIMEOUT
    )


@contribs_error_handler("contribution")
async def contribs_search_contributions(
    project: str,
    identifier: str | None = None,
    formula: str | None = None,
    data_filters: dict | None = None,
    page: int = 1,
    per_page: int = 10,
) -> str:
    """
    Query contributions within a project with filters and pagination.

    Args:
        project: Project name (required)
        identifier: Filter by MP material ID (e.g., "mp-149")
        formula: Filter by chemical formula
        data_filters: Dict of fully qualified filter keys using Django-style operators.
            Example: {"data__band_gap__value__gte": 1.0, "data__band_gap__value__lte": 3.0}
            Supported operators: __gte, __lte, __gt, __lt, __contains, __exact
        page: Page number (default: 1)
        per_page: Results per page (default: 10, max: 100)

    Returns:
        JSON with contributions and pagination metadata
    """
    err, api_key = _check_contribs_prerequisites()
    if err:
        return err

    validation_err = _validate_project_name(project)
    if validation_err:
        return _error_response(validation_err)

    if identifier is not None:
        validation_err = _validate_material_id(identifier)
        if validation_err:
            return _error_response(validation_err)

    validation_err = _validate_page(page)
    if validation_err:
        return _error_response(validation_err)

    validation_err = _validate_per_page(per_page)
    if validation_err:
        return _error_response(validation_err)

    # Validate data_filters keys
    if data_filters:
        validation_err = _validate_data_filters(data_filters)
        if validation_err:
            return _error_response(validation_err, error_category="validation_error")

    def _query():
        client = _get_contribs_client(api_key)
        kwargs = {
            "project": project,
            "_limit": per_page,
            "_skip": (page - 1) * per_page,
        }
        if identifier:
            kwargs["identifier"] = identifier
        if formula:
            kwargs["formula__contains"] = formula
        if data_filters:
            kwargs.update(data_filters)

        result = client.contributions.queryContributions(
            _fields=[
                "id", "identifier", "formula", "data", "structures", "tables",
            ],
            _sort="-id",
            **kwargs,
        ).result()

        contributions = result.get("data", [])
        total_count = result.get("total_count", 0)
        has_more = ((page - 1) * per_page + per_page) < total_count

        formatted = []
        for c in contributions:
            formatted.append({
                "id": c.get("id", ""),
                "identifier": c.get("identifier", ""),
                "formula": c.get("formula", ""),
                "data": c.get("data", {}),
                "structures": c.get("structures", []),
                "tables": c.get("tables", []),
            })

        return json.dumps({
            "total_count": total_count,
            "has_more": has_more,
            "page": page,
            "per_page": per_page,
            "contributions": formatted,
        }, indent=2)

    return await asyncio.wait_for(
        asyncio.to_thread(_query), timeout=API_TIMEOUT
    )


@contribs_error_handler("contribution")
async def contribs_get_contribution(
    contribution_id: str,
) -> str:
    """
    Get a single contribution by its ObjectId.

    Args:
        contribution_id: 24-character hex ObjectId

    Returns:
        JSON with contribution data including identifier, data, and linked entity IDs
    """
    err, api_key = _check_contribs_prerequisites()
    if err:
        return err

    validation_err = _validate_object_id(contribution_id, "contribution")
    if validation_err:
        return _error_response(validation_err)

    def _query():
        client = _get_contribs_client(api_key)
        contrib = client.get_contribution(contribution_id)

        return json.dumps({
            "id": contrib.get("id", ""),
            "identifier": contrib.get("identifier", ""),
            "project": contrib.get("project", ""),
            "data": contrib.get("data", {}),
            "structures": contrib.get("structures", []),
            "tables": contrib.get("tables", []),
            "attachments": contrib.get("attachments", []),
        }, indent=2)

    return await asyncio.wait_for(
        asyncio.to_thread(_query), timeout=API_TIMEOUT
    )


@contribs_error_handler("table")
async def contribs_get_table(
    table_id: str,
    max_rows: int = 100,
) -> str:
    """
    Retrieve a table by its ObjectId as JSON.

    Args:
        table_id: 24-character hex ObjectId
        max_rows: Maximum number of rows to return (default: 100, -1 for all rows,
                  capped at MAX_ROWS_ABSOLUTE for memory safety)

    Returns:
        JSON with table name, columns, data rows, and row count
    """
    err, api_key = _check_contribs_prerequisites()
    if err:
        return err

    validation_err = _validate_object_id(table_id, "table")
    if validation_err:
        return _error_response(validation_err)

    if max_rows != -1 and max_rows < 1:
        return _error_response("max_rows must be -1 (all rows) or >= 1")

    # Enforce absolute memory limit: cap max_rows regardless of user input
    rows_to_fetch = max_rows
    if rows_to_fetch == -1:
        rows_to_fetch = MAX_ROWS_ABSOLUTE
    elif rows_to_fetch > MAX_ROWS_ABSOLUTE:
        rows_to_fetch = MAX_ROWS_ABSOLUTE

    def _query():
        client = _get_contribs_client(api_key)
        df = client.get_table(table_id)

        columns = df.columns.tolist()
        total_rows = len(df)

        def _sanitize_value(v):
            """Replace NaN/Infinity with None for JSON serialization."""
            if isinstance(v, float) and (math.isnan(v) or math.isinf(v)):
                return None
            return v

        # Use the capped rows_to_fetch value instead of max_rows
        if total_rows <= rows_to_fetch:
            data = [[_sanitize_value(v) for v in row] for row in df.values.tolist()]
            truncated = False
        else:
            data = [[_sanitize_value(v) for v in row] for row in df.head(rows_to_fetch).values.tolist()]
            truncated = True

        return json.dumps({
            "id": table_id,
            "name": getattr(df, "name", table_id),
            "columns": columns,
            "data": data,
            "total_rows": total_rows,
            "truncated": truncated,
        }, indent=2)

    return await asyncio.wait_for(
        asyncio.to_thread(_query), timeout=API_TIMEOUT
    )


@contribs_error_handler("structure")
async def contribs_get_structure(
    structure_id: str,
    output_format: str = "cif",
) -> str:
    """
    Retrieve a crystal structure from MPContribs by its ObjectId.

    Args:
        structure_id: 24-character hex ObjectId
        output_format: Output format - "cif" or "json" (default: "cif").
            Note: "poscar" is not supported for MPContribs structures.

    Returns:
        Crystal structure in the requested format
    """
    err, api_key = _check_contribs_prerequisites()
    if err:
        return err

    validation_err = _validate_object_id(structure_id, "structure")
    if validation_err:
        return _error_response(validation_err)

    if output_format not in ("cif", "json"):
        return _error_response(
            f"Unknown format: {output_format}. Use 'cif' or 'json'"
        )

    def _query():
        from pymatgen.io.cif import CifWriter

        client = _get_contribs_client(api_key)
        structure = client.get_structure(structure_id)

        if output_format == "cif":
            return CifWriter(structure).__str__()
        else:
            return structure.to_json()

    return await asyncio.wait_for(
        asyncio.to_thread(_query), timeout=API_TIMEOUT
    )


@contribs_error_handler("attachment")
async def contribs_get_attachment(
    attachment_id: str,
) -> str:
    """
    Retrieve attachment metadata (not content) by its ObjectId.

    Args:
        attachment_id: 24-character hex ObjectId

    Returns:
        JSON with attachment metadata: filename, mime type, size
    """
    err, api_key = _check_contribs_prerequisites()
    if err:
        return err

    validation_err = _validate_object_id(attachment_id, "attachment")
    if validation_err:
        return _error_response(validation_err)

    def _query():
        client = _get_contribs_client(api_key)
        result = client.attachments.getAttachmentById(
            pk=attachment_id,
            _fields=["id", "name", "mime", "content"],
        ).result()

        content_raw = result.get("content", "")

        return json.dumps({
            "id": result.get("id", attachment_id),
            "filename": result.get("name", ""),
            "mime_type": result.get("mime", ""),
            # The MPContribs API returns content as a string whose encoding
            # depends on the attachment MIME type (often base64, but not
            # guaranteed).  We pass it through as-is.
            "content": content_raw if content_raw else None,
        }, indent=2)

    return await asyncio.wait_for(
        asyncio.to_thread(_query), timeout=API_TIMEOUT
    )


@contribs_error_handler("project")
async def contribs_get_project_stats(
    project_name: str,
) -> str:
    """
    Get contribution totals and summary statistics for a project.

    Args:
        project_name: The project name

    Returns:
        JSON with project name, total contributions, and total pages
    """
    err, api_key = _check_contribs_prerequisites()
    if err:
        return err

    validation_err = _validate_project_name(project_name)
    if validation_err:
        return _error_response(validation_err)

    def _query():
        client = _get_contribs_client(api_key)
        total_count, total_pages = client.get_totals(
            query={"project": project_name}
        )

        return json.dumps({
            "project": project_name,
            "total_contributions": total_count,
            "total_pages": total_pages,
        }, indent=2)

    return await asyncio.wait_for(
        asyncio.to_thread(_query), timeout=API_TIMEOUT
    )


# ============================================================================
# Registration
# ============================================================================


def register_contribs_tools(mcp: FastMCP) -> None:
    """Register all MPContribs tools on the given FastMCP instance."""
    mcp.add_tool(contribs_search_projects, annotations=TOOL_ANNOTATIONS)
    mcp.add_tool(contribs_get_project, annotations=TOOL_ANNOTATIONS)
    mcp.add_tool(contribs_search_contributions, annotations=TOOL_ANNOTATIONS)
    mcp.add_tool(contribs_get_contribution, annotations=TOOL_ANNOTATIONS)
    mcp.add_tool(contribs_get_table, annotations=TOOL_ANNOTATIONS)
    mcp.add_tool(contribs_get_structure, annotations=TOOL_ANNOTATIONS)
    mcp.add_tool(contribs_get_attachment, annotations=TOOL_ANNOTATIONS)
    mcp.add_tool(contribs_get_project_stats, annotations=TOOL_ANNOTATIONS)
