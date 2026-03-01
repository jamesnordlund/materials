"""Materials Project provenance tool functions.

Provides ``mp_get_database_version``, ``mp_provenance_get``, and
``mp_tasks_get``, registered via ``register_mp_provenance_tools(mcp)``.
"""

from __future__ import annotations

import asyncio
import logging
import time
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from mcp.server.fastmcp import FastMCP

    from mcp_materials._cache import InMemoryCache

from mcp_materials._cache import _cache_key
from mcp_materials._db_version import get_db_version
from mcp_materials._output import _build_response
from mcp_materials._prereqs import HAS_MP_API, _check_prerequisites
from mcp_materials._sanitize import sanitize_message
from mcp_materials._validation import (
    TOOL_ANNOTATIONS,
    _error_response,
    _validate_material_id,
)

if HAS_MP_API:
    from mp_api.client import MPRester

# Timeout in seconds for upstream API calls via asyncio.to_thread.
API_TIMEOUT: float = 60.0

_TIMEOUT_MSG = (
    "Request timed out after {timeout} seconds. "
    "The upstream API may be slow or unresponsive. Please try again later."
)

# Module-level cache reference, set by register_mp_provenance_tools().
_cache: InMemoryCache | None = None

logger = logging.getLogger(__name__)


# ============================================================================
# Tool implementations
# ============================================================================


async def mp_get_database_version() -> str:
    """Return the current Materials Project database version.

    Returns:
        JSON with db_version, tool_name, and query_time_ms in metadata.
    """
    err, key = _check_prerequisites()
    if err:
        return err

    # Cache lookup (db_version=None since this tool *fetches* the version).
    cache_k = _cache_key("mp_get_database_version", None)
    if _cache is not None:
        cached = _cache.get(cache_k)
        if cached is not None:
            logger.debug("cache hit: %s", cache_k)
            return cached

    t0 = time.monotonic()
    try:
        db_version, db_version_error = await get_db_version(key)  # type: ignore[arg-type]
    except TimeoutError:
        return _error_response(
            _TIMEOUT_MSG.format(timeout=API_TIMEOUT),
            error_category="timeout_error",
        )
    except Exception as e:
        return _error_response(sanitize_message(str(e)), error_category="api_error")

    elapsed_ms = (time.monotonic() - t0) * 1000.0

    result = _build_response(
        tool_name="mp_get_database_version",
        query={},
        records=[{"db_version": db_version}],
        db_version=db_version,
        db_version_error=db_version_error,
        query_time_ms=elapsed_ms,
    )
    if _cache is not None:
        _cache.put(cache_k, result)
        logger.debug("cache miss: %s", cache_k)
    return result


async def mp_provenance_get(
    material_id: str,
    fields: list[str] | None = None,
) -> str:
    """Get provenance metadata for a material.

    Args:
        material_id: MP ID (format: mp-XXXXX or mvc-XXXXX)
        fields: Optional list of fields to return. Defaults to all provenance fields.

    Returns:
        JSON with provenance data including task_ids, builder metadata, database version.
    """
    err, key = _check_prerequisites()
    if err:
        return err

    validation_err = _validate_material_id(material_id)
    if validation_err:
        return _error_response(validation_err, error_category="validation_error")

    t0 = time.monotonic()

    # Fetch db_version in parallel intent; errors are non-fatal (R-ERR-006).
    db_version, db_version_error = await get_db_version(key)  # type: ignore[arg-type]

    # Cache lookup.
    cache_k = _cache_key(
        "mp_provenance_get",
        db_version,
        material_id=material_id,
        fields=fields,
    )
    if _cache is not None:
        cached = _cache.get(cache_k)
        if cached is not None:
            logger.debug("cache hit: %s", cache_k)
            return cached

    _default_fields = [
        "material_id",
        "task_ids",
        "last_updated",
        "created_at",
        "history",
        "authors",
        "remarks",
    ]

    requested_fields = fields if fields else _default_fields

    def _query():
        with MPRester(key) as mpr:
            doc = mpr.materials.provenance.get_data_by_id(
                material_id,
                fields=requested_fields,
            )
            if doc is None:
                return None

            record: dict = {}
            for field in requested_fields:
                value = getattr(doc, field, None)
                if value is not None:
                    record[field] = value
                else:
                    record[field] = None

            # Ensure material_id is always a string.
            if "material_id" in record and record["material_id"] is not None:
                record["material_id"] = str(record["material_id"])

            # Convert task_ids list items to strings.
            if "task_ids" in record and isinstance(record["task_ids"], list):
                record["task_ids"] = [str(tid) for tid in record["task_ids"]]

            # Convert datetime objects to ISO strings.
            for dt_field in ("last_updated", "created_at"):
                if dt_field in record and hasattr(record[dt_field], "isoformat"):
                    record[dt_field] = record[dt_field].isoformat()

            return record

    try:
        record = await asyncio.wait_for(
            asyncio.to_thread(_query), timeout=API_TIMEOUT
        )
    except TimeoutError:
        return _error_response(
            _TIMEOUT_MSG.format(timeout=API_TIMEOUT),
            error_category="timeout_error",
        )
    except Exception as e:
        return _error_response(sanitize_message(str(e)), error_category="api_error")

    if record is None:
        return _error_response(
            f"No provenance data found for {material_id}",
            error_category="not_found",
        )

    elapsed_ms = (time.monotonic() - t0) * 1000.0

    result = _build_response(
        tool_name="mp_provenance_get",
        query={"material_id": material_id},
        records=[record],
        db_version=db_version,
        db_version_error=db_version_error,
        query_time_ms=elapsed_ms,
    )
    if _cache is not None:
        _cache.put(cache_k, result)
        logger.debug("cache miss: %s", cache_k)
    return result


async def mp_tasks_get(
    material_id: str,
    fields: list[str] | None = None,
) -> str:
    """Get task-level provenance data for a material.

    Args:
        material_id: MP ID (format: mp-XXXXX or mvc-XXXXX)
        fields: Optional list of fields to return from task documents.

    Returns:
        JSON with task-level data: calculation IDs, input parameters, task types.
    """
    err, key = _check_prerequisites()
    if err:
        return err

    validation_err = _validate_material_id(material_id)
    if validation_err:
        return _error_response(validation_err, error_category="validation_error")

    t0 = time.monotonic()

    # Fetch db_version; errors are non-fatal (R-ERR-006).
    db_version, db_version_error = await get_db_version(key)  # type: ignore[arg-type]

    # Cache lookup.
    cache_k = _cache_key(
        "mp_tasks_get",
        db_version,
        material_id=material_id,
        fields=fields,
    )
    if _cache is not None:
        cached = _cache.get(cache_k)
        if cached is not None:
            logger.debug("cache hit: %s", cache_k)
            return cached

    _default_fields = [
        "task_id",
        "task_type",
        "last_updated",
        "input_parameters",
        "run_type",
    ]

    requested_fields = fields if fields else _default_fields

    def _query():
        with MPRester(key) as mpr:
            docs = mpr.tasks.search(
                material_ids=[material_id],
                fields=requested_fields,
            )
            if not docs:
                return []

            records: list[dict] = []
            for doc in docs:
                record: dict = {}
                for field in requested_fields:
                    value = getattr(doc, field, None)
                    if value is not None:
                        record[field] = value
                    else:
                        record[field] = None

                # Ensure task_id is always a string.
                if "task_id" in record and record["task_id"] is not None:
                    record["task_id"] = str(record["task_id"])

                # Convert datetime objects to ISO strings.
                if "last_updated" in record and hasattr(
                    record["last_updated"], "isoformat"
                ):
                    record["last_updated"] = record["last_updated"].isoformat()

                records.append(record)
            return records

    try:
        records = await asyncio.wait_for(
            asyncio.to_thread(_query), timeout=API_TIMEOUT
        )
    except TimeoutError:
        return _error_response(
            _TIMEOUT_MSG.format(timeout=API_TIMEOUT),
            error_category="timeout_error",
        )
    except Exception as e:
        return _error_response(sanitize_message(str(e)), error_category="api_error")

    elapsed_ms = (time.monotonic() - t0) * 1000.0

    result = _build_response(
        tool_name="mp_tasks_get",
        query={"material_id": material_id},
        records=records,
        db_version=db_version,
        db_version_error=db_version_error,
        query_time_ms=elapsed_ms,
    )
    if _cache is not None:
        _cache.put(cache_k, result)
        logger.debug("cache miss: %s", cache_k)
    return result


# ============================================================================
# Registration
# ============================================================================


def register_mp_provenance_tools(
    server: FastMCP,
    *,
    cache: InMemoryCache | None = None,
) -> None:
    """Register provenance tools on the given FastMCP instance."""
    global _cache  # noqa: PLW0603
    _cache = cache
    server.add_tool(mp_get_database_version, annotations=TOOL_ANNOTATIONS)
    server.add_tool(mp_provenance_get, annotations=TOOL_ANNOTATIONS)
    server.add_tool(mp_tasks_get, annotations=TOOL_ANNOTATIONS)
