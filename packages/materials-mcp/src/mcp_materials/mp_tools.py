"""Materials Project tool functions (10 tools).

Each function is a plain ``async def`` registered via ``register_mp_tools(mcp)``.
"""

from __future__ import annotations

import asyncio
import json
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from mcp.server.fastmcp import FastMCP

from mcp_materials._prereqs import HAS_MP_API, _check_prerequisites
from mcp_materials._sanitize import sanitize_message
from mcp_materials._validation import (
    TOOL_ANNOTATIONS,
    _error_response,
    _validate_elements,
    _validate_formula,
    _validate_material_id,
    _validate_max_results,
)

if HAS_MP_API:
    from mp_api.client import MPRester
    from pymatgen.analysis.phase_diagram import PhaseDiagram
    from pymatgen.io.cif import CifWriter
    from pymatgen.io.vasp import Poscar

# Timeout in seconds for upstream API calls via asyncio.to_thread.
API_TIMEOUT: float = 60.0

_TIMEOUT_MSG = (
    "Request timed out after {timeout} seconds. "
    "The upstream API may be slow or unresponsive. Please try again later."
)


# ============================================================================
# Private helpers
# ============================================================================


def _extract_crystal_system(symmetry) -> str | None:
    """Extract crystal system string from a symmetry object.

    Handles both enum-style (with .value) and plain string attributes.
    Returns None if symmetry or crystal_system is unavailable.
    """
    if symmetry is None:
        return None
    cs = getattr(symmetry, "crystal_system", None)
    if cs is None:
        return None
    return str(cs.value) if hasattr(cs, "value") else str(cs)


# ============================================================================
# Tool implementations
# ============================================================================


async def search_materials(
    formula: str,
    max_results: int = 10,
) -> str:
    """
    Search for materials by chemical formula in the Materials Project database.

    Args:
        formula: Chemical formula (e.g., "Fe2O3", "LiFePO4", "Si")
        max_results: Maximum number of results to return (default: 10)

    Returns:
        JSON with matching materials including material_id, formula, and key properties
    """
    err, key = _check_prerequisites()
    if err:
        return err

    validation_err = _validate_formula(formula)
    if validation_err:
        return _error_response(validation_err)

    validation_err = _validate_max_results(max_results)
    if validation_err:
        return _error_response(validation_err)

    def _query():
        with MPRester(key) as mpr:
            docs = mpr.materials.summary.search(
                formula=formula,
                fields=[
                    "material_id",
                    "formula_pretty",
                    "energy_above_hull",
                    "band_gap",
                    "formation_energy_per_atom",
                    "density",
                    "symmetry",
                    "is_stable",
                ],
                num_chunks=1,
                chunk_size=max_results,
            )

            results = []
            for doc in docs[:max_results]:
                results.append({
                    "material_id": str(doc.material_id),
                    "formula": doc.formula_pretty,
                    "energy_above_hull_eV": doc.energy_above_hull,
                    "band_gap_eV": doc.band_gap,
                    "formation_energy_eV_atom": doc.formation_energy_per_atom,
                    "density_g_cm3": doc.density,
                    "crystal_system": _extract_crystal_system(doc.symmetry),
                    "space_group": doc.symmetry.symbol if doc.symmetry else None,
                    "is_stable": doc.is_stable,
                })

            return json.dumps({
                "count": len(results),
                "materials": results,
            }, indent=2)

    try:
        return await asyncio.wait_for(
            asyncio.to_thread(_query), timeout=API_TIMEOUT
        )
    except (TimeoutError, asyncio.TimeoutError):
        return _error_response(_TIMEOUT_MSG.format(timeout=API_TIMEOUT))
    except Exception as e:
        return _error_response(str(e))


async def get_structure(
    material_id: str,
    output_format: str = "cif",
) -> str:
    """
    Get the crystal structure for a material from Materials Project.

    Args:
        material_id: Materials Project ID (e.g., "mp-149" for Silicon)
        output_format: Output format - "cif", "poscar", or "json" (default: "cif")

    Returns:
        Crystal structure in the requested format
    """
    err, key = _check_prerequisites()
    if err:
        return err

    validation_err = _validate_material_id(material_id)
    if validation_err:
        return _error_response(validation_err)

    valid_formats = {"cif", "poscar", "json"}
    if output_format.lower() not in valid_formats:
        return _error_response(
            f"Unknown format: {output_format}. Use 'cif', 'poscar', or 'json'",
            error_category="validation_error",
        )

    def _query():
        with MPRester(key) as mpr:
            structure = mpr.get_structure_by_material_id(material_id)

            fmt = output_format.lower()
            if fmt == "cif":
                return CifWriter(structure).__str__()
            elif fmt == "poscar":
                return Poscar(structure).get_str()
            else:
                return structure.to_json()

    try:
        return await asyncio.wait_for(
            asyncio.to_thread(_query), timeout=API_TIMEOUT
        )
    except (TimeoutError, asyncio.TimeoutError):
        return _error_response(_TIMEOUT_MSG.format(timeout=API_TIMEOUT))
    except Exception as e:
        return _error_response(str(e))


async def get_properties(
    material_id: str,
) -> str:
    """
    Get detailed properties for a specific material from Materials Project.

    Args:
        material_id: Materials Project ID (e.g., "mp-149" for Silicon)

    Returns:
        JSON with comprehensive material properties
    """
    err, key = _check_prerequisites()
    if err:
        return err

    validation_err = _validate_material_id(material_id)
    if validation_err:
        return _error_response(validation_err)

    def _query():
        with MPRester(key) as mpr:
            doc = mpr.materials.summary.get_data_by_id(material_id)

            properties = {
                "material_id": str(doc.material_id),
                "formula": doc.formula_pretty,
                "elements": [str(el) for el in doc.elements],
                "nelements": doc.nelements,
                "nsites": doc.nsites,
                "volume": doc.volume,
                "density": doc.density,

                # Thermodynamic properties
                "formation_energy_per_atom": doc.formation_energy_per_atom,
                "energy_above_hull": doc.energy_above_hull,
                "is_stable": doc.is_stable,

                # Electronic properties
                "band_gap": doc.band_gap,
                "is_metal": doc.is_metal,
                "is_magnetic": doc.is_magnetic,
                "total_magnetization": doc.total_magnetization,

                # Symmetry
                "crystal_system": _extract_crystal_system(doc.symmetry),
                "space_group_symbol": doc.symmetry.symbol if doc.symmetry else None,
                "space_group_number": doc.symmetry.number if doc.symmetry else None,
                "point_group": doc.symmetry.point_group if doc.symmetry else None,

                # Provenance
                "database_ids": (
                    doc.database_IDs if hasattr(doc, "database_IDs") else None
                ),
            }

            return json.dumps(properties, indent=2)

    try:
        return await asyncio.wait_for(
            asyncio.to_thread(_query), timeout=API_TIMEOUT
        )
    except (TimeoutError, asyncio.TimeoutError):
        return _error_response(_TIMEOUT_MSG.format(timeout=API_TIMEOUT))
    except Exception as e:
        return _error_response(str(e))


async def compare_materials(
    material_ids: list[str],
) -> str:
    """
    Compare properties of multiple materials side by side.

    Args:
        material_ids: List of Materials Project IDs (e.g., ["mp-149", "mp-66"])

    Returns:
        JSON table comparing key properties across materials
    """
    err, key = _check_prerequisites()
    if err:
        return err

    if not material_ids:
        return _error_response(
            "material_ids list must not be empty",
            error_category="validation_error",
        )

    for mid in material_ids:
        validation_err = _validate_material_id(mid)
        if validation_err:
            return _error_response(validation_err)

    if len(material_ids) > 20:
        return _error_response(
            f"Too many material IDs ({len(material_ids)}). Maximum is 20.",
            error_category="validation_error",
        )

    def _query():
        comparison = []

        with MPRester(key) as mpr:
            for mid in material_ids:
                try:
                    doc = mpr.materials.summary.get_data_by_id(mid)
                    comparison.append({
                        "material_id": str(doc.material_id),
                        "formula": doc.formula_pretty,
                        "band_gap_eV": doc.band_gap,
                        "formation_energy_eV": doc.formation_energy_per_atom,
                        "energy_above_hull_eV": doc.energy_above_hull,
                        "density_g_cm3": doc.density,
                        "is_stable": doc.is_stable,
                        "is_metal": doc.is_metal,
                        "crystal_system": _extract_crystal_system(doc.symmetry),
                    })
                except Exception as e:
                    comparison.append({
                        "material_id": mid,
                        "error": sanitize_message(str(e)),
                    })

        return json.dumps({
            "count": len(comparison),
            "comparison": comparison,
        }, indent=2)

    try:
        return await asyncio.wait_for(
            asyncio.to_thread(_query), timeout=API_TIMEOUT
        )
    except (TimeoutError, asyncio.TimeoutError):
        return _error_response(_TIMEOUT_MSG.format(timeout=API_TIMEOUT))
    except Exception as e:
        return _error_response(str(e))


async def search_by_elements(
    elements: list[str],
    exclude_elements: list[str] | None = None,
    max_results: int = 10,
) -> str:
    """
    Search for materials containing specific elements.

    Args:
        elements: List of elements that must be present (e.g., ["Li", "Fe", "O"])
        exclude_elements: Optional list of elements to exclude
        max_results: Maximum number of results (default: 10)

    Returns:
        JSON with matching materials
    """
    err, key = _check_prerequisites()
    if err:
        return err

    validation_err = _validate_elements(elements)
    if validation_err:
        return _error_response(validation_err)

    if exclude_elements:
        validation_err = _validate_elements(exclude_elements)
        if validation_err:
            return _error_response(validation_err)

    validation_err = _validate_max_results(max_results)
    if validation_err:
        return _error_response(validation_err)

    def _query():
        with MPRester(key) as mpr:
            docs = mpr.materials.summary.search(
                elements=elements,
                exclude_elements=exclude_elements or [],
                fields=[
                    "material_id",
                    "formula_pretty",
                    "energy_above_hull",
                    "band_gap",
                    "is_stable",
                ],
                num_chunks=1,
                chunk_size=max_results,
            )

            results = []
            for doc in docs[:max_results]:
                results.append({
                    "material_id": str(doc.material_id),
                    "formula": doc.formula_pretty,
                    "energy_above_hull_eV": doc.energy_above_hull,
                    "band_gap_eV": doc.band_gap,
                    "is_stable": doc.is_stable,
                })

            return json.dumps({
                "query": {
                    "must_include": elements,
                    "must_exclude": exclude_elements,
                },
                "count": len(results),
                "materials": results,
            }, indent=2)

    try:
        return await asyncio.wait_for(
            asyncio.to_thread(_query), timeout=API_TIMEOUT
        )
    except (TimeoutError, asyncio.TimeoutError):
        return _error_response(_TIMEOUT_MSG.format(timeout=API_TIMEOUT))
    except Exception as e:
        return _error_response(str(e))


async def search_by_band_gap(
    min_gap: float = 0.0,
    max_gap: float = 10.0,
    direct_gap_only: bool = False,
    max_results: int = 10,
) -> str:
    """
    Search for materials by band gap range.

    Args:
        min_gap: Minimum band gap in eV (default: 0)
        max_gap: Maximum band gap in eV (default: 10)
        direct_gap_only: Only return materials with direct band gaps
        max_results: Maximum number of results (default: 10)

    Returns:
        JSON with materials in the specified band gap range
    """
    err, key = _check_prerequisites()
    if err:
        return err

    validation_err = _validate_max_results(max_results)
    if validation_err:
        return _error_response(validation_err)

    if min_gap > max_gap:
        return _error_response(
            f"min_gap ({min_gap}) must be <= max_gap ({max_gap})",
            error_category="validation_error",
        )

    def _query():
        search_kwargs: dict = {
            "band_gap": (min_gap, max_gap),
            "fields": [
                "material_id",
                "formula_pretty",
                "band_gap",
                "is_gap_direct",
                "energy_above_hull",
                "is_stable",
            ],
            "num_chunks": 1,
            "chunk_size": max_results,
        }

        if direct_gap_only:
            search_kwargs["is_gap_direct"] = True

        with MPRester(key) as mpr:
            docs = mpr.materials.summary.search(**search_kwargs)

        results = []
        for doc in docs:
            if len(results) >= max_results:
                break
            results.append({
                "material_id": str(doc.material_id),
                "formula": doc.formula_pretty,
                "band_gap_eV": doc.band_gap,
                "is_direct_gap": doc.is_gap_direct,
                "energy_above_hull_eV": doc.energy_above_hull,
                "is_stable": doc.is_stable,
            })

        return json.dumps({
            "query": {
                "band_gap_range_eV": [min_gap, max_gap],
                "direct_gap_only": direct_gap_only,
            },
            "count": len(results),
            "materials": results,
        }, indent=2)

    try:
        return await asyncio.wait_for(
            asyncio.to_thread(_query), timeout=API_TIMEOUT
        )
    except (TimeoutError, asyncio.TimeoutError):
        return _error_response(_TIMEOUT_MSG.format(timeout=API_TIMEOUT))
    except Exception as e:
        return _error_response(str(e))


async def get_similar_structures(
    material_id: str,
    max_results: int = 5,
) -> str:
    """
    Find materials with the same space group number as the given material.

    Args:
        material_id: Materials Project ID to find similar structures for
        max_results: Maximum number of similar structures (default: 5)

    Returns:
        JSON with materials sharing the same space group
    """
    err, key = _check_prerequisites()
    if err:
        return err

    validation_err = _validate_material_id(material_id)
    if validation_err:
        return _error_response(validation_err)

    validation_err = _validate_max_results(max_results)
    if validation_err:
        return _error_response(validation_err)

    def _query():
        with MPRester(key) as mpr:
            # Get the reference material
            ref_doc = mpr.materials.summary.get_data_by_id(material_id)
            space_group = ref_doc.symmetry.number if ref_doc.symmetry else None

            if not space_group:
                return _error_response(
                    "Could not determine space group for reference material"
                )

            # Search for materials with same space group
            docs = mpr.materials.summary.search(
                spacegroup_number=space_group,
                fields=[
                    "material_id",
                    "formula_pretty",
                    "symmetry",
                    "nsites",
                    "volume",
                ],
                num_chunks=1,
                chunk_size=max_results + 1,  # +1 to exclude self
            )

            results = []
            for doc in docs:
                if str(doc.material_id) == material_id:
                    continue
                if len(results) >= max_results:
                    break
                results.append({
                    "material_id": str(doc.material_id),
                    "formula": doc.formula_pretty,
                    "space_group": doc.symmetry.symbol if doc.symmetry else None,
                    "nsites": doc.nsites,
                    "volume_A3": doc.volume,
                })

            return json.dumps({
                "reference": {
                    "material_id": material_id,
                    "formula": ref_doc.formula_pretty,
                    "space_group": (
                        ref_doc.symmetry.symbol if ref_doc.symmetry else None
                    ),
                },
                "similar_structures": results,
            }, indent=2)

    try:
        return await asyncio.wait_for(
            asyncio.to_thread(_query), timeout=API_TIMEOUT
        )
    except (TimeoutError, asyncio.TimeoutError):
        return _error_response(_TIMEOUT_MSG.format(timeout=API_TIMEOUT))
    except Exception as e:
        return _error_response(str(e))


async def get_phase_diagram(
    elements: list[str],
) -> str:
    """
    Get phase diagram data for a chemical system.

    Args:
        elements: List of elements defining the system (e.g., ["Li", "Fe", "O"])

    Returns:
        JSON with phase diagram entries including stable phases, formation energies,
        and decomposition products
    """
    err, key = _check_prerequisites()
    if err:
        return err

    validation_err = _validate_elements(elements)
    if validation_err:
        return _error_response(validation_err)

    def _query():
        with MPRester(key) as mpr:
            # Get all entries in the chemical system
            chemsys = "-".join(sorted(elements))
            entries = mpr.get_entries_in_chemsys(elements)

            if not entries:
                return _error_response(
                    f"No entries found for chemical system: {chemsys}",
                    chemical_system=chemsys,
                )

            # Build phase diagram
            pd = PhaseDiagram(entries)

            # Get stable entries
            stable_entries = []
            for entry in pd.stable_entries:
                stable_entries.append({
                    "material_id": (
                        str(entry.entry_id) if hasattr(entry, "entry_id") else None
                    ),
                    "formula": entry.composition.reduced_formula,
                    "energy_per_atom_eV": entry.energy_per_atom,
                    "formation_energy_per_atom_eV": pd.get_form_energy_per_atom(entry),
                })

            # Get unstable entries with decomposition info
            unstable_entries = []
            for entry in pd.unstable_entries:
                decomp, e_above_hull = pd.get_decomp_and_e_above_hull(entry)
                decomp_products = [
                    p.composition.reduced_formula for p in decomp
                ]
                unstable_entries.append({
                    "material_id": (
                        str(entry.entry_id) if hasattr(entry, "entry_id") else None
                    ),
                    "formula": entry.composition.reduced_formula,
                    "energy_above_hull_eV": e_above_hull,
                    "decomposes_to": decomp_products,
                })

            total_unstable = len(unstable_entries)
            truncated_unstable = unstable_entries[:20]
            unstable_result = {
                "count": total_unstable,
                "entries": truncated_unstable,
            }
            if total_unstable > 20:
                unstable_result["note"] = (
                    f"Showing 20 of {total_unstable} unstable entries. "
                    "Results truncated for readability."
                )

            return json.dumps({
                "chemical_system": chemsys,
                "num_elements": len(elements),
                "total_entries": len(entries),
                "stable_phases": {
                    "count": len(stable_entries),
                    "entries": stable_entries,
                },
                "unstable_phases": unstable_result,
            }, indent=2)

    try:
        return await asyncio.wait_for(
            asyncio.to_thread(_query), timeout=API_TIMEOUT
        )
    except (TimeoutError, asyncio.TimeoutError):
        return _error_response(_TIMEOUT_MSG.format(timeout=API_TIMEOUT))
    except Exception as e:
        return _error_response(str(e))


async def get_elastic_properties(
    material_id: str,
) -> str:
    """
    Get elastic and mechanical properties for a material.

    Args:
        material_id: Materials Project ID (e.g., "mp-149" for Silicon)

    Returns:
        JSON with elastic properties including bulk modulus, shear modulus,
        Young's modulus, Poisson's ratio, and elastic tensor
    """
    err, key = _check_prerequisites()
    if err:
        return err

    validation_err = _validate_material_id(material_id)
    if validation_err:
        return _error_response(validation_err)

    def _query():
        with MPRester(key) as mpr:
            # Get elasticity data
            docs = mpr.materials.elasticity.search(
                material_ids=[material_id],
            )

            if not docs:
                return _error_response(
                    "No elastic data available for this material",
                    material_id=material_id,
                    note="Elastic properties are only computed for a subset of materials",
                )

            doc = docs[0]

            # Extract elastic properties
            properties = {
                "material_id": material_id,
                "formula": (
                    doc.formula_pretty if hasattr(doc, "formula_pretty") else None
                ),

                # Voigt-Reuss-Hill averages (most commonly used)
                "bulk_modulus_vrh_GPa": (
                    doc.bulk_modulus.vrh if doc.bulk_modulus else None
                ),
                "shear_modulus_vrh_GPa": (
                    doc.shear_modulus.vrh if doc.shear_modulus else None
                ),
                "youngs_modulus_GPa": (
                    doc.young_modulus if hasattr(doc, "young_modulus") else None
                ),
                "poisson_ratio": (
                    doc.homogeneous_poisson
                    if hasattr(doc, "homogeneous_poisson")
                    else None
                ),

                # Voigt bounds (upper)
                "bulk_modulus_voigt_GPa": (
                    doc.bulk_modulus.voigt if doc.bulk_modulus else None
                ),
                "shear_modulus_voigt_GPa": (
                    doc.shear_modulus.voigt if doc.shear_modulus else None
                ),

                # Reuss bounds (lower)
                "bulk_modulus_reuss_GPa": (
                    doc.bulk_modulus.reuss if doc.bulk_modulus else None
                ),
                "shear_modulus_reuss_GPa": (
                    doc.shear_modulus.reuss if doc.shear_modulus else None
                ),

                # Derived properties
                "universal_anisotropy": (
                    doc.universal_anisotropy
                    if hasattr(doc, "universal_anisotropy")
                    else None
                ),
                "debye_temperature_K": (
                    doc.debye_temperature
                    if hasattr(doc, "debye_temperature")
                    else None
                ),

                # Classification - convert enum to string
                "state": (
                    str(doc.state.value)
                    if hasattr(doc, "state") and hasattr(doc.state, "value")
                    else (str(doc.state) if hasattr(doc, "state") else None)
                ),
            }

            # Add elastic tensor if available (6x6 Voigt notation)
            if hasattr(doc, "elastic_tensor") and doc.elastic_tensor:
                tensor = doc.elastic_tensor
                if hasattr(tensor, "ieee_format"):
                    properties["elastic_tensor_GPa"] = tensor.ieee_format
                elif hasattr(tensor, "raw"):
                    properties["elastic_tensor_GPa"] = tensor.raw

            return json.dumps(properties, indent=2)

    try:
        return await asyncio.wait_for(
            asyncio.to_thread(_query), timeout=API_TIMEOUT
        )
    except (TimeoutError, asyncio.TimeoutError):
        return _error_response(_TIMEOUT_MSG.format(timeout=API_TIMEOUT))
    except Exception as e:
        return _error_response(str(e))


async def search_by_elastic_properties(
    min_bulk_modulus: float | None = None,
    max_bulk_modulus: float | None = None,
    min_shear_modulus: float | None = None,
    max_shear_modulus: float | None = None,
    max_results: int = 10,
) -> str:
    """
    Search for materials by elastic/mechanical properties.

    Args:
        min_bulk_modulus: Minimum bulk modulus in GPa
        max_bulk_modulus: Maximum bulk modulus in GPa
        min_shear_modulus: Minimum shear modulus in GPa
        max_shear_modulus: Maximum shear modulus in GPa
        max_results: Maximum number of results (default: 10)

    Note:
        When no upper bound is specified for bulk or shear modulus, a ceiling
        of 1000 GPa is used as the default upper limit.

    Returns:
        JSON with materials matching the elastic property criteria
    """
    err, key = _check_prerequisites()
    if err:
        return err

    validation_err = _validate_max_results(max_results)
    if validation_err:
        return _error_response(validation_err)

    def _query():
        search_kwargs: dict = {
            "num_chunks": 1,
            "chunk_size": max_results * 2,
        }

        # Add bulk modulus filter
        if min_bulk_modulus is not None or max_bulk_modulus is not None:
            bulk_range = (
                min_bulk_modulus if min_bulk_modulus is not None else 0,
                max_bulk_modulus if max_bulk_modulus is not None else 1000,
            )
            search_kwargs["bulk_modulus"] = bulk_range

        # Add shear modulus filter
        if min_shear_modulus is not None or max_shear_modulus is not None:
            shear_range = (
                min_shear_modulus if min_shear_modulus is not None else 0,
                max_shear_modulus if max_shear_modulus is not None else 1000,
            )
            search_kwargs["shear_modulus"] = shear_range

        with MPRester(key) as mpr:
            docs = mpr.materials.elasticity.search(**search_kwargs)

        results = []
        for doc in docs[:max_results]:
            results.append({
                "material_id": str(doc.material_id),
                "formula": (
                    doc.formula_pretty if hasattr(doc, "formula_pretty") else None
                ),
                "bulk_modulus_GPa": (
                    doc.bulk_modulus.vrh if doc.bulk_modulus else None
                ),
                "shear_modulus_GPa": (
                    doc.shear_modulus.vrh if doc.shear_modulus else None
                ),
                "universal_anisotropy": (
                    doc.universal_anisotropy
                    if hasattr(doc, "universal_anisotropy")
                    else None
                ),
            })

        return json.dumps({
            "query": {
                "bulk_modulus_range_GPa": [min_bulk_modulus, max_bulk_modulus],
                "shear_modulus_range_GPa": [min_shear_modulus, max_shear_modulus],
            },
            "count": len(results),
            "materials": results,
        }, indent=2)

    try:
        return await asyncio.wait_for(
            asyncio.to_thread(_query), timeout=API_TIMEOUT
        )
    except (TimeoutError, asyncio.TimeoutError):
        return _error_response(_TIMEOUT_MSG.format(timeout=API_TIMEOUT))
    except Exception as e:
        return _error_response(str(e))


# ============================================================================
# Registration
# ============================================================================


def register_mp_tools(mcp: FastMCP) -> None:
    """Register all Materials Project tools on the given FastMCP instance."""
    mcp.add_tool(search_materials, annotations=TOOL_ANNOTATIONS)
    mcp.add_tool(get_structure, annotations=TOOL_ANNOTATIONS)
    mcp.add_tool(get_properties, annotations=TOOL_ANNOTATIONS)
    mcp.add_tool(compare_materials, annotations=TOOL_ANNOTATIONS)
    mcp.add_tool(search_by_elements, annotations=TOOL_ANNOTATIONS)
    mcp.add_tool(search_by_band_gap, annotations=TOOL_ANNOTATIONS)
    mcp.add_tool(get_similar_structures, annotations=TOOL_ANNOTATIONS)
    mcp.add_tool(get_phase_diagram, annotations=TOOL_ANNOTATIONS)
    mcp.add_tool(get_elastic_properties, annotations=TOOL_ANNOTATIONS)
    mcp.add_tool(search_by_elastic_properties, annotations=TOOL_ANNOTATIONS)
