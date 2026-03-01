"""Materials Project advanced summary search tool.

Provides ``mp_summary_search_advanced``, registered via
``register_mp_search_tools(server)``.
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
    _validate_fields,
    _validate_formula,
    _validate_max_results,
    _validate_sort_dir,
)

if HAS_MP_API:
    from mp_api.client import MPRester

# Timeout in seconds for upstream API calls via asyncio.to_thread.
API_TIMEOUT: float = 60.0

_TIMEOUT_MSG = (
    "Request timed out after {timeout} seconds. "
    "The upstream API may be slow or unresponsive. Please try again later."
)

# Module-level cache reference, set by register_mp_search_tools().
_cache: InMemoryCache | None = None

logger = logging.getLogger(__name__)

# Snapshot of commonly available summary fields.  This can be refreshed from
# ``MPRester().materials.summary.available_fields`` in record mode.
_KNOWN_SUMMARY_FIELDS: frozenset[str] = frozenset({
    "material_id",
    "formula_pretty",
    "formula_anonymous",
    "chemsys",
    "nelements",
    "elements",
    "nsites",
    "volume",
    "density",
    "density_atomic",
    "symmetry",
    "crystal_system",
    "space_group",
    # Thermodynamic
    "energy_above_hull",
    "formation_energy_per_atom",
    "energy_per_atom",
    "is_stable",
    "equilibrium_reaction_energy_per_atom",
    "decomposes_to",
    # Electronic
    "band_gap",
    "cbm",
    "vbm",
    "efermi",
    "is_gap_direct",
    "is_metal",
    # Magnetic
    "is_magnetic",
    "ordering",
    "total_magnetization",
    "total_magnetization_normalized_vol",
    "total_magnetization_normalized_formula_units",
    # Structural
    "structure",
    # Provenance
    "database_IDs",
    "deprecated",
    "theoretical",
    "last_updated",
    "task_ids",
})

# Maps raw MP field names to unit-suffixed output key names (R-OUT-002).
_UNIT_FIELD_MAP: dict[str, str] = {
    "energy_above_hull": "energy_above_hull_eV",
    "formation_energy_per_atom": "formation_energy_eV_atom",
    "energy_per_atom": "energy_per_atom_eV",
    "equilibrium_reaction_energy_per_atom": "equilibrium_reaction_energy_eV_atom",
    "band_gap": "band_gap_eV",
    "cbm": "cbm_eV",
    "vbm": "vbm_eV",
    "efermi": "efermi_eV",
    "density": "density_g_cm3",
    "density_atomic": "density_atomic_A3",
    "volume": "volume_A3",
    "total_magnetization": "total_magnetization_muB",
    "total_magnetization_normalized_vol": "total_magnetization_normalized_vol_muB_A3",
}


def _output_key(field: str) -> str:
    """Return the unit-suffixed output key for a field, or the field itself."""
    return _UNIT_FIELD_MAP.get(field, field)


def _extract_crystal_system(symmetry: object) -> str | None:
    """Extract crystal system string from a symmetry object."""
    if symmetry is None:
        return None
    cs = getattr(symmetry, "crystal_system", None)
    if cs is None:
        return None
    return str(cs.value) if hasattr(cs, "value") else str(cs)


# ============================================================================
# Tool implementation
# ============================================================================


async def mp_summary_search_advanced(
    must_include_elements: list[str] | None = None,
    must_exclude_elements: list[str] | None = None,
    formula: str | None = None,
    chemsys: str | None = None,
    band_gap_min: float | None = None,
    band_gap_max: float | None = None,
    energy_above_hull_max: float | None = None,
    is_stable: bool | None = None,
    is_metal: bool | None = None,
    fields: list[str] | None = None,
    sort_by: str | None = None,
    sort_dir: str = "asc",
    max_results: int = 50,
) -> str:
    """Advanced search across the Materials Project summary endpoint.

    Args:
        must_include_elements: Elements that must be present (e.g., ["Li", "Fe", "O"])
        must_exclude_elements: Elements to exclude
        formula: Chemical formula filter
        chemsys: Chemical system (e.g., "Li-Fe-O")
        band_gap_min: Minimum band gap in eV
        band_gap_max: Maximum band gap in eV
        energy_above_hull_max: Maximum energy above hull in eV/atom
        is_stable: Filter for stable materials only
        is_metal: Filter for metals or non-metals
        fields: List of fields to return (validated against available_fields)
        sort_by: Field name to sort by
        sort_dir: Sort direction, "asc" or "desc" (default: "asc")
        max_results: Maximum results (1-100, default: 50)

    Returns:
        JSON with matching materials in standardized output format.
    """
    err, key = _check_prerequisites()
    if err:
        return err

    # -- Require at least one search parameter --------------------------------
    has_filter = any(
        p is not None
        for p in (
            must_include_elements,
            must_exclude_elements,
            formula,
            chemsys,
            band_gap_min,
            band_gap_max,
            energy_above_hull_max,
            is_stable,
            is_metal,
        )
    )
    if not has_filter:
        return _error_response(
            "At least one search parameter must be provided.",
            error_category="validation_error",
        )

    # -- Input validation -----------------------------------------------------
    if must_include_elements is not None:
        ve = _validate_elements(must_include_elements)
        if ve:
            return _error_response(ve, error_category="validation_error")

    if must_exclude_elements is not None:
        ve = _validate_elements(must_exclude_elements)
        if ve:
            return _error_response(ve, error_category="validation_error")

    if formula is not None:
        ve = _validate_formula(formula)
        if ve:
            return _error_response(ve, error_category="validation_error")

    if chemsys is not None:
        ve = _validate_chemsys(chemsys)
        if ve:
            return _error_response(ve, error_category="validation_error")

    ve = _validate_max_results(max_results)
    if ve:
        return _error_response(ve, error_category="validation_error")

    ve = _validate_sort_dir(sort_dir)
    if ve:
        return _error_response(ve, error_category="validation_error")

    if fields is not None:
        ve = _validate_fields(fields, _KNOWN_SUMMARY_FIELDS)
        if ve:
            return _error_response(ve, error_category="validation_error")

    if sort_by is not None and sort_by not in _KNOWN_SUMMARY_FIELDS:
        return _error_response(
            f"Unknown sort_by field '{sort_by}'.",
            error_category="validation_error",
        )

    # -- Cache lookup ---------------------------------------------------------
    # Fetch db_version first so it's included in the cache key.
    db_version, db_version_error = await get_db_version(key)  # type: ignore[arg-type]

    cache_k = _cache_key(
        "mp_summary_search_advanced",
        db_version,
        must_include_elements=must_include_elements,
        must_exclude_elements=must_exclude_elements,
        formula=formula,
        chemsys=chemsys,
        band_gap_min=band_gap_min,
        band_gap_max=band_gap_max,
        energy_above_hull_max=energy_above_hull_max,
        is_stable=is_stable,
        is_metal=is_metal,
        fields=fields,
        sort_by=sort_by,
        sort_dir=sort_dir,
        max_results=max_results,
    )
    if _cache is not None:
        cached = _cache.get(cache_k)
        if cached is not None:
            logger.debug("cache hit: %s", cache_k)
            return cached

    # -- Build query ----------------------------------------------------------
    _default_fields = [
        "material_id",
        "formula_pretty",
        "energy_above_hull",
        "band_gap",
        "density",
        "volume",
        "nsites",
        "symmetry",
        "is_stable",
        "is_metal",
    ]

    requested_fields = fields if fields else _default_fields

    # Always include material_id for identification.
    api_fields = list(requested_fields)
    if "material_id" not in api_fields:
        api_fields.append("material_id")
    # Map virtual fields to real API fields.
    if "crystal_system" in api_fields:
        api_fields.remove("crystal_system")
        if "symmetry" not in api_fields:
            api_fields.append("symmetry")
    if "space_group" in api_fields:
        api_fields.remove("space_group")
        if "symmetry" not in api_fields:
            api_fields.append("symmetry")

    search_kwargs: dict = {
        "fields": api_fields,
        "num_chunks": 1,
        "chunk_size": max_results,
    }

    if must_include_elements is not None:
        search_kwargs["elements"] = must_include_elements
    if must_exclude_elements is not None:
        search_kwargs["exclude_elements"] = must_exclude_elements
    if formula is not None:
        search_kwargs["formula"] = formula
    if chemsys is not None:
        search_kwargs["chemsys"] = chemsys
    if band_gap_min is not None or band_gap_max is not None:
        search_kwargs["band_gap"] = (
            band_gap_min if band_gap_min is not None else 0,
            band_gap_max if band_gap_max is not None else 1e6,
        )
    if energy_above_hull_max is not None:
        search_kwargs["energy_above_hull"] = (0, energy_above_hull_max)
    if is_stable is not None:
        search_kwargs["is_stable"] = is_stable
    if is_metal is not None:
        search_kwargs["is_metal"] = is_metal

    t0 = time.monotonic()

    def _query() -> list[dict]:
        with MPRester(key) as mpr:
            docs = mpr.materials.summary.search(**search_kwargs)

        results: list[dict] = []
        for doc in docs[:max_results]:
            record: dict = {}
            for field in requested_fields:
                # Virtual fields derived from symmetry.
                if field == "crystal_system":
                    record["crystal_system"] = _extract_crystal_system(
                        getattr(doc, "symmetry", None)
                    )
                    continue
                if field == "space_group":
                    sym = getattr(doc, "symmetry", None)
                    record["space_group"] = sym.symbol if sym else None
                    continue

                value = getattr(doc, field, None)

                # Stringify material_id and task_ids.
                if field == "material_id" and value is not None:
                    value = str(value)
                if field == "task_ids" and isinstance(value, list):
                    value = [str(tid) for tid in value]

                # Convert datetime objects to ISO strings.
                if field == "last_updated" and hasattr(value, "isoformat"):
                    value = value.isoformat()

                record[_output_key(field)] = value
            results.append(record)

        # Apply sorting if requested.
        if sort_by is not None:
            out_key = _output_key(sort_by)
            reverse = sort_dir == "desc"
            results.sort(
                key=lambda r: (r.get(out_key) is None, r.get(out_key)),
                reverse=reverse,
            )

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
    if must_include_elements is not None:
        query_echo["must_include_elements"] = must_include_elements
    if must_exclude_elements is not None:
        query_echo["must_exclude_elements"] = must_exclude_elements
    if formula is not None:
        query_echo["formula"] = formula
    if chemsys is not None:
        query_echo["chemsys"] = chemsys
    if band_gap_min is not None:
        query_echo["band_gap_min"] = band_gap_min
    if band_gap_max is not None:
        query_echo["band_gap_max"] = band_gap_max
    if energy_above_hull_max is not None:
        query_echo["energy_above_hull_max"] = energy_above_hull_max
    if is_stable is not None:
        query_echo["is_stable"] = is_stable
    if is_metal is not None:
        query_echo["is_metal"] = is_metal
    if fields is not None:
        query_echo["fields"] = fields
    if sort_by is not None:
        query_echo["sort_by"] = sort_by
    query_echo["sort_dir"] = sort_dir
    query_echo["max_results"] = max_results

    result = _build_response(
        tool_name="mp_summary_search_advanced",
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


def register_mp_search_tools(
    server: FastMCP,
    *,
    cache: InMemoryCache | None = None,
) -> None:
    """Register search tools on the given FastMCP instance."""
    global _cache  # noqa: PLW0603
    _cache = cache
    server.add_tool(mp_summary_search_advanced, annotations=TOOL_ANNOTATIONS)
