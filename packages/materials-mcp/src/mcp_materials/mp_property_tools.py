"""Materials Project property search tools.

Provides ``mp_insertion_electrodes_search``, registered via
``register_mp_property_tools(server)``.
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
    _validate_chemsys,
    _validate_elements,
    _validate_material_id,
    _validate_max_results,
)

if HAS_MP_API:
    from mp_api.client import MPRester

# Timeout in seconds for upstream API calls via asyncio.to_thread.
API_TIMEOUT: float = 60.0

_TIMEOUT_MSG = (
    "Request timed out after {timeout} seconds. "
    "The upstream API may be slow or unresponsive. Please try again later."
)

# Module-level cache reference, set by register_mp_property_tools().
_cache: InMemoryCache | None = None

logger = logging.getLogger(__name__)

# Maps raw MP electrode field names to unit-suffixed output key names (R-OUT-002).
_ELECTRODE_UNIT_FIELD_MAP: dict[str, str] = {
    "average_voltage": "avg_voltage_V",
    "capacity_grav": "capacity_grav_mAh_g",
    "capacity_vol": "capacity_vol_mAh_cm3",
    "energy_grav": "energy_grav_Wh_kg",
    "energy_vol": "energy_vol_Wh_l",
    "max_delta_volume": "max_delta_volume_pct",
    "stability_charge": "stability_charge_eV",
    "stability_discharge": "stability_discharge_eV",
}


def _electrode_output_key(field: str) -> str:
    """Return the unit-suffixed output key for an electrode field."""
    return _ELECTRODE_UNIT_FIELD_MAP.get(field, field)


# Default fields to request when the caller does not specify any.
_DEFAULT_ELECTRODE_FIELDS = [
    "battery_id",
    "battery_formula",
    "framework_formula",
    "working_ion",
    "num_steps",
    "max_delta_volume",
    "average_voltage",
    "capacity_grav",
    "capacity_vol",
    "energy_grav",
    "energy_vol",
    "stability_charge",
    "stability_discharge",
    "material_ids",
    "formula_pretty",
]


# ============================================================================
# Tool implementation
# ============================================================================


async def mp_insertion_electrodes_search(
    working_ion: str | None = None,
    material_id: str | None = None,
    chemsys: str | None = None,
    fields: list[str] | None = None,
    max_results: int = 20,
) -> str:
    """Search for insertion electrode documents.

    Args:
        working_ion: Working ion element (e.g., "Li", "Na", "Mg")
        material_id: Filter by specific material ID
        chemsys: Chemical system (e.g., "Li-Mn-O")
        fields: Optional fields to return
        max_results: Maximum results (1-100, default: 20)

    Returns:
        JSON with electrode documents including voltage data,
        capacity, and framework information.
    """
    err, key = _check_prerequisites()
    if err:
        return err

    # -- Require at least one search parameter --------------------------------
    has_filter = any(p is not None for p in (working_ion, material_id, chemsys))
    if not has_filter:
        return _error_response(
            "At least one of working_ion, material_id, or chemsys must be provided.",
            error_category="validation_error",
        )

    # -- Input validation -----------------------------------------------------
    if working_ion is not None:
        ve = _validate_elements([working_ion])
        if ve:
            return _error_response(
                f"Invalid working_ion '{working_ion}'. "
                "Expected an element symbol like 'Li' or 'Na'.",
                error_category="validation_error",
            )

    if material_id is not None:
        ve = _validate_material_id(material_id)
        if ve:
            return _error_response(ve, error_category="validation_error")

    if chemsys is not None:
        ve = _validate_chemsys(chemsys)
        if ve:
            return _error_response(ve, error_category="validation_error")

    ve = _validate_max_results(max_results)
    if ve:
        return _error_response(ve, error_category="validation_error")

    # -- Build search kwargs --------------------------------------------------
    requested_fields = fields if fields else _DEFAULT_ELECTRODE_FIELDS

    search_kwargs: dict = {
        "num_chunks": 1,
        "chunk_size": max_results,
    }

    if working_ion is not None:
        search_kwargs["working_ion"] = working_ion
    if material_id is not None:
        search_kwargs["battery_id"] = material_id
    if chemsys is not None:
        search_kwargs["chemsys"] = chemsys

    # Request fields from the API.  Always include battery_id for identification.
    api_fields = list(requested_fields)
    if "battery_id" not in api_fields:
        api_fields.append("battery_id")
    search_kwargs["fields"] = api_fields

    t0 = time.monotonic()

    # Fetch db_version; errors are non-fatal (R-ERR-006).
    db_version, db_version_error = await get_db_version(key)  # type: ignore[arg-type]

    # Cache lookup.
    cache_k = _cache_key(
        "mp_insertion_electrodes_search",
        db_version,
        working_ion=working_ion,
        material_id=material_id,
        chemsys=chemsys,
        fields=fields,
        max_results=max_results,
    )
    if _cache is not None:
        cached = _cache.get(cache_k)
        if cached is not None:
            logger.debug("cache hit: %s", cache_k)
            return cached

    def _query() -> list[dict]:
        with MPRester(key) as mpr:
            docs = mpr.insertion_electrodes.search(**search_kwargs)

        results: list[dict] = []
        for doc in docs[:max_results]:
            record: dict = {}
            for field in requested_fields:
                value = getattr(doc, field, None)

                # Stringify MPID-typed values.
                if field == "battery_id" and value is not None:
                    value = str(value)
                if field == "material_ids" and isinstance(value, list):
                    value = [str(mid) for mid in value]

                record[_electrode_output_key(field)] = value
            results.append(record)

        return results

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

    # Build query echo for the response.
    query_echo: dict = {}
    if working_ion is not None:
        query_echo["working_ion"] = working_ion
    if material_id is not None:
        query_echo["material_id"] = material_id
    if chemsys is not None:
        query_echo["chemsys"] = chemsys
    if fields is not None:
        query_echo["fields"] = fields
    query_echo["max_results"] = max_results

    result = _build_response(
        tool_name="mp_insertion_electrodes_search",
        query=query_echo,
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


def register_mp_property_tools(
    server: FastMCP,
    *,
    cache: InMemoryCache | None = None,
) -> None:
    """Register property tools on the given FastMCP instance."""
    global _cache  # noqa: PLW0603
    _cache = cache
    server.add_tool(mp_insertion_electrodes_search, annotations=TOOL_ANNOTATIONS)
