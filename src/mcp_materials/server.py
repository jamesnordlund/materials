"""
MCP Server for Materials Science Databases

Provides AI agents with access to:
- Materials Project API (crystal structures, properties, phase diagrams)
- Composition analysis and validation
- Property lookups and comparisons

December 2025 - Built with the latest MCP Python SDK
"""

import os
import json
from typing import Any

from mcp.server.fastmcp import FastMCP

# Initialize the MCP server
mcp = FastMCP("materials-science")

# ============================================================================
# Configuration
# ============================================================================

def get_mp_api_key() -> str | None:
    """Get Materials Project API key from environment."""
    return os.environ.get("MP_API_KEY")


def check_api_key() -> tuple[bool, str]:
    """Check if API key is configured."""
    key = get_mp_api_key()
    if not key:
        return False, "MP_API_KEY environment variable not set. Get your key at https://materialsproject.org/api"
    return True, key


# ============================================================================
# Tools: Materials Project API
# ============================================================================

@mcp.tool()
def search_materials(
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
    has_key, key_or_error = check_api_key()
    if not has_key:
        return json.dumps({"error": key_or_error})

    try:
        from mp_api.client import MPRester

        with MPRester(key_or_error) as mpr:
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
                crystal_system = None
                if doc.symmetry and doc.symmetry.crystal_system:
                    crystal_system = str(doc.symmetry.crystal_system.value) if hasattr(doc.symmetry.crystal_system, 'value') else str(doc.symmetry.crystal_system)
                results.append({
                    "material_id": str(doc.material_id),
                    "formula": doc.formula_pretty,
                    "energy_above_hull_eV": doc.energy_above_hull,
                    "band_gap_eV": doc.band_gap,
                    "formation_energy_eV_atom": doc.formation_energy_per_atom,
                    "density_g_cm3": doc.density,
                    "crystal_system": crystal_system,
                    "space_group": doc.symmetry.symbol if doc.symmetry else None,
                    "is_stable": doc.is_stable,
                })

            return json.dumps({
                "count": len(results),
                "materials": results,
            }, indent=2)

    except ImportError:
        return json.dumps({"error": "mp-api package not installed. Run: pip install mp-api"})
    except Exception as e:
        return json.dumps({"error": str(e)})


@mcp.tool()
def get_structure(
    material_id: str,
    format: str = "cif",
) -> str:
    """
    Get the crystal structure for a material from Materials Project.

    Args:
        material_id: Materials Project ID (e.g., "mp-149" for Silicon)
        format: Output format - "cif", "poscar", or "json" (default: "cif")

    Returns:
        Crystal structure in the requested format
    """
    has_key, key_or_error = check_api_key()
    if not has_key:
        return json.dumps({"error": key_or_error})

    try:
        from mp_api.client import MPRester

        with MPRester(key_or_error) as mpr:
            structure = mpr.get_structure_by_material_id(material_id)

            if format.lower() == "cif":
                from pymatgen.io.cif import CifWriter
                return CifWriter(structure).__str__()
            elif format.lower() == "poscar":
                from pymatgen.io.vasp import Poscar
                return Poscar(structure).get_str()
            elif format.lower() == "json":
                return structure.to_json()
            else:
                return json.dumps({"error": f"Unknown format: {format}. Use 'cif', 'poscar', or 'json'"})

    except ImportError:
        return json.dumps({"error": "mp-api or pymatgen not installed"})
    except Exception as e:
        return json.dumps({"error": str(e)})


@mcp.tool()
def get_properties(
    material_id: str,
) -> str:
    """
    Get detailed properties for a specific material from Materials Project.

    Args:
        material_id: Materials Project ID (e.g., "mp-149" for Silicon)

    Returns:
        JSON with comprehensive material properties
    """
    has_key, key_or_error = check_api_key()
    if not has_key:
        return json.dumps({"error": key_or_error})

    try:
        from mp_api.client import MPRester

        with MPRester(key_or_error) as mpr:
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
                "crystal_system": str(doc.symmetry.crystal_system.value) if doc.symmetry and hasattr(doc.symmetry.crystal_system, 'value') else (str(doc.symmetry.crystal_system) if doc.symmetry else None),
                "space_group_symbol": doc.symmetry.symbol if doc.symmetry else None,
                "space_group_number": doc.symmetry.number if doc.symmetry else None,
                "point_group": doc.symmetry.point_group if doc.symmetry else None,

                # Provenance
                "database_ids": doc.database_IDs if hasattr(doc, 'database_IDs') else None,
            }

            return json.dumps(properties, indent=2)

    except Exception as e:
        return json.dumps({"error": str(e)})


@mcp.tool()
def compare_materials(
    material_ids: list[str],
) -> str:
    """
    Compare properties of multiple materials side by side.

    Args:
        material_ids: List of Materials Project IDs (e.g., ["mp-149", "mp-66"])

    Returns:
        JSON table comparing key properties across materials
    """
    has_key, key_or_error = check_api_key()
    if not has_key:
        return json.dumps({"error": key_or_error})

    try:
        from mp_api.client import MPRester

        comparison = []

        with MPRester(key_or_error) as mpr:
            for mid in material_ids:
                try:
                    doc = mpr.materials.summary.get_data_by_id(mid)
                    crystal_system = None
                    if doc.symmetry and doc.symmetry.crystal_system:
                        crystal_system = str(doc.symmetry.crystal_system.value) if hasattr(doc.symmetry.crystal_system, 'value') else str(doc.symmetry.crystal_system)
                    comparison.append({
                        "material_id": str(doc.material_id),
                        "formula": doc.formula_pretty,
                        "band_gap_eV": doc.band_gap,
                        "formation_energy_eV": doc.formation_energy_per_atom,
                        "energy_above_hull_eV": doc.energy_above_hull,
                        "density_g_cm3": doc.density,
                        "is_stable": doc.is_stable,
                        "is_metal": doc.is_metal,
                        "crystal_system": crystal_system,
                    })
                except Exception as e:
                    comparison.append({
                        "material_id": mid,
                        "error": str(e),
                    })

        return json.dumps({
            "count": len(comparison),
            "comparison": comparison,
        }, indent=2)

    except Exception as e:
        return json.dumps({"error": str(e)})


@mcp.tool()
def search_by_elements(
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
    has_key, key_or_error = check_api_key()
    if not has_key:
        return json.dumps({"error": key_or_error})

    try:
        from mp_api.client import MPRester

        with MPRester(key_or_error) as mpr:
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

    except Exception as e:
        return json.dumps({"error": str(e)})


@mcp.tool()
def search_by_band_gap(
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
    has_key, key_or_error = check_api_key()
    if not has_key:
        return json.dumps({"error": key_or_error})

    try:
        from mp_api.client import MPRester

        with MPRester(key_or_error) as mpr:
            search_kwargs: dict[str, Any] = {
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
                "chunk_size": max_results * 2,  # Get extra in case we filter
            }

            if direct_gap_only:
                search_kwargs["is_gap_direct"] = True

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

    except Exception as e:
        return json.dumps({"error": str(e)})


@mcp.tool()
def get_similar_structures(
    material_id: str,
    max_results: int = 5,
) -> str:
    """
    Find materials with similar crystal structures.

    Args:
        material_id: Materials Project ID to find similar structures for
        max_results: Maximum number of similar structures (default: 5)

    Returns:
        JSON with structurally similar materials
    """
    has_key, key_or_error = check_api_key()
    if not has_key:
        return json.dumps({"error": key_or_error})

    try:
        from mp_api.client import MPRester

        with MPRester(key_or_error) as mpr:
            # Get the reference material
            ref_doc = mpr.materials.summary.get_data_by_id(material_id)
            space_group = ref_doc.symmetry.number if ref_doc.symmetry else None

            if not space_group:
                return json.dumps({"error": "Could not determine space group for reference material"})

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
                    "space_group": ref_doc.symmetry.symbol if ref_doc.symmetry else None,
                },
                "similar_structures": results,
            }, indent=2)

    except Exception as e:
        return json.dumps({"error": str(e)})


@mcp.tool()
def get_phase_diagram(
    elements: list[str],
) -> str:
    """
    Get phase diagram data for a chemical system.

    Args:
        elements: List of elements defining the system (e.g., ["Li", "Fe", "O"] for Li-Fe-O system)

    Returns:
        JSON with phase diagram entries including stable phases, formation energies, and decomposition products
    """
    has_key, key_or_error = check_api_key()
    if not has_key:
        return json.dumps({"error": key_or_error})

    try:
        from mp_api.client import MPRester
        from pymatgen.analysis.phase_diagram import PhaseDiagram

        with MPRester(key_or_error) as mpr:
            # Get all entries in the chemical system
            chemsys = "-".join(sorted(elements))
            entries = mpr.get_entries_in_chemsys(elements)

            if not entries:
                return json.dumps({
                    "error": f"No entries found for chemical system: {chemsys}",
                    "chemical_system": chemsys,
                })

            # Build phase diagram
            pd = PhaseDiagram(entries)

            # Get stable entries
            stable_entries = []
            for entry in pd.stable_entries:
                stable_entries.append({
                    "material_id": str(entry.entry_id) if hasattr(entry, 'entry_id') else None,
                    "formula": entry.composition.reduced_formula,
                    "energy_per_atom_eV": entry.energy_per_atom,
                    "formation_energy_per_atom_eV": pd.get_form_energy_per_atom(entry),
                })

            # Get unstable entries with decomposition info
            unstable_entries = []
            for entry in pd.unstable_entries:
                decomp, e_above_hull = pd.get_decomp_and_e_above_hull(entry)
                decomp_products = [p.composition.reduced_formula for p in decomp.keys()]
                unstable_entries.append({
                    "material_id": str(entry.entry_id) if hasattr(entry, 'entry_id') else None,
                    "formula": entry.composition.reduced_formula,
                    "energy_above_hull_eV": e_above_hull,
                    "decomposes_to": decomp_products,
                })

            return json.dumps({
                "chemical_system": chemsys,
                "num_elements": len(elements),
                "total_entries": len(entries),
                "stable_phases": {
                    "count": len(stable_entries),
                    "entries": stable_entries,
                },
                "unstable_phases": {
                    "count": len(unstable_entries),
                    "entries": unstable_entries[:20],  # Limit to first 20
                },
            }, indent=2)

    except ImportError:
        return json.dumps({"error": "mp-api or pymatgen not installed"})
    except Exception as e:
        return json.dumps({"error": str(e)})


@mcp.tool()
def get_elastic_properties(
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
    has_key, key_or_error = check_api_key()
    if not has_key:
        return json.dumps({"error": key_or_error})

    try:
        from mp_api.client import MPRester

        with MPRester(key_or_error) as mpr:
            # Get elasticity data
            docs = mpr.materials.elasticity.search(
                material_ids=[material_id],
            )

            if not docs:
                return json.dumps({
                    "material_id": material_id,
                    "error": "No elastic data available for this material",
                    "note": "Elastic properties are only computed for a subset of materials",
                })

            doc = docs[0]

            # Extract elastic properties
            properties = {
                "material_id": material_id,
                "formula": doc.formula_pretty if hasattr(doc, 'formula_pretty') else None,

                # Voigt-Reuss-Hill averages (most commonly used)
                "bulk_modulus_vrh_GPa": doc.bulk_modulus.vrh if doc.bulk_modulus else None,
                "shear_modulus_vrh_GPa": doc.shear_modulus.vrh if doc.shear_modulus else None,
                "youngs_modulus_GPa": doc.young_modulus if hasattr(doc, 'young_modulus') else None,
                "poisson_ratio": doc.homogeneous_poisson if hasattr(doc, 'homogeneous_poisson') else None,

                # Voigt bounds (upper)
                "bulk_modulus_voigt_GPa": doc.bulk_modulus.voigt if doc.bulk_modulus else None,
                "shear_modulus_voigt_GPa": doc.shear_modulus.voigt if doc.shear_modulus else None,

                # Reuss bounds (lower)
                "bulk_modulus_reuss_GPa": doc.bulk_modulus.reuss if doc.bulk_modulus else None,
                "shear_modulus_reuss_GPa": doc.shear_modulus.reuss if doc.shear_modulus else None,

                # Derived properties
                "universal_anisotropy": doc.universal_anisotropy if hasattr(doc, 'universal_anisotropy') else None,
                "debye_temperature_K": doc.debye_temperature if hasattr(doc, 'debye_temperature') else None,

                # Classification - convert enum to string
                "state": str(doc.state.value) if hasattr(doc, 'state') and hasattr(doc.state, 'value') else (str(doc.state) if hasattr(doc, 'state') else None),
            }

            # Add elastic tensor if available (6x6 Voigt notation)
            if hasattr(doc, 'elastic_tensor') and doc.elastic_tensor:
                tensor = doc.elastic_tensor
                if hasattr(tensor, 'ieee_format'):
                    properties["elastic_tensor_GPa"] = tensor.ieee_format
                elif hasattr(tensor, 'raw'):
                    properties["elastic_tensor_GPa"] = tensor.raw

            return json.dumps(properties, indent=2)

    except Exception as e:
        return json.dumps({"error": str(e)})


@mcp.tool()
def search_by_elastic_properties(
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

    Returns:
        JSON with materials matching the elastic property criteria
    """
    has_key, key_or_error = check_api_key()
    if not has_key:
        return json.dumps({"error": key_or_error})

    try:
        from mp_api.client import MPRester

        with MPRester(key_or_error) as mpr:
            search_kwargs: dict[str, Any] = {
                "num_chunks": 1,
                "chunk_size": max_results * 2,
            }

            # Add bulk modulus filter
            if min_bulk_modulus is not None or max_bulk_modulus is not None:
                bulk_range = (
                    min_bulk_modulus if min_bulk_modulus else 0,
                    max_bulk_modulus if max_bulk_modulus else 1000,
                )
                search_kwargs["bulk_modulus"] = bulk_range

            # Add shear modulus filter
            if min_shear_modulus is not None or max_shear_modulus is not None:
                shear_range = (
                    min_shear_modulus if min_shear_modulus else 0,
                    max_shear_modulus if max_shear_modulus else 1000,
                )
                search_kwargs["shear_modulus"] = shear_range

            docs = mpr.materials.elasticity.search(**search_kwargs)

            results = []
            for doc in docs[:max_results]:
                results.append({
                    "material_id": str(doc.material_id),
                    "formula": doc.formula_pretty if hasattr(doc, 'formula_pretty') else None,
                    "bulk_modulus_GPa": doc.bulk_modulus.vrh if doc.bulk_modulus else None,
                    "shear_modulus_GPa": doc.shear_modulus.vrh if doc.shear_modulus else None,
                    "universal_anisotropy": doc.universal_anisotropy if hasattr(doc, 'universal_anisotropy') else None,
                })

            return json.dumps({
                "query": {
                    "bulk_modulus_range_GPa": [min_bulk_modulus, max_bulk_modulus],
                    "shear_modulus_range_GPa": [min_shear_modulus, max_shear_modulus],
                },
                "count": len(results),
                "materials": results,
            }, indent=2)

    except Exception as e:
        return json.dumps({"error": str(e)})


# ============================================================================
# Resources: Reference Data
# ============================================================================

@mcp.resource("materials://periodic-table")
def get_periodic_table() -> str:
    """Get periodic table data as a resource."""
    periodic_table = {
        "H": {"name": "Hydrogen", "atomic_number": 1, "mass": 1.008},
        "He": {"name": "Helium", "atomic_number": 2, "mass": 4.003},
        "Li": {"name": "Lithium", "atomic_number": 3, "mass": 6.941},
        "Be": {"name": "Beryllium", "atomic_number": 4, "mass": 9.012},
        "B": {"name": "Boron", "atomic_number": 5, "mass": 10.81},
        "C": {"name": "Carbon", "atomic_number": 6, "mass": 12.01},
        "N": {"name": "Nitrogen", "atomic_number": 7, "mass": 14.01},
        "O": {"name": "Oxygen", "atomic_number": 8, "mass": 16.00},
        "F": {"name": "Fluorine", "atomic_number": 9, "mass": 19.00},
        "Ne": {"name": "Neon", "atomic_number": 10, "mass": 20.18},
        # ... abbreviated for size, full table in production
        "Fe": {"name": "Iron", "atomic_number": 26, "mass": 55.845},
        "Co": {"name": "Cobalt", "atomic_number": 27, "mass": 58.933},
        "Ni": {"name": "Nickel", "atomic_number": 28, "mass": 58.693},
        "Cu": {"name": "Copper", "atomic_number": 29, "mass": 63.546},
        "Zn": {"name": "Zinc", "atomic_number": 30, "mass": 65.38},
        "Si": {"name": "Silicon", "atomic_number": 14, "mass": 28.086},
        "Ti": {"name": "Titanium", "atomic_number": 22, "mass": 47.867},
        "Al": {"name": "Aluminum", "atomic_number": 13, "mass": 26.982},
    }
    return json.dumps(periodic_table, indent=2)


@mcp.resource("materials://crystal-systems")
def get_crystal_systems() -> str:
    """Get crystal system reference data."""
    systems = {
        "triclinic": {
            "symmetry": "lowest",
            "constraints": "a ≠ b ≠ c, α ≠ β ≠ γ ≠ 90°",
            "example_materials": ["kyanite"],
        },
        "monoclinic": {
            "symmetry": "low",
            "constraints": "a ≠ b ≠ c, α = γ = 90° ≠ β",
            "example_materials": ["gypsum", "orthoclase"],
        },
        "orthorhombic": {
            "symmetry": "medium",
            "constraints": "a ≠ b ≠ c, α = β = γ = 90°",
            "example_materials": ["olivine", "aragonite"],
        },
        "tetragonal": {
            "symmetry": "medium-high",
            "constraints": "a = b ≠ c, α = β = γ = 90°",
            "example_materials": ["rutile TiO2", "zircon"],
        },
        "trigonal": {
            "symmetry": "medium-high",
            "constraints": "a = b = c, α = β = γ ≠ 90°",
            "example_materials": ["quartz", "calcite"],
        },
        "hexagonal": {
            "symmetry": "high",
            "constraints": "a = b ≠ c, α = β = 90°, γ = 120°",
            "example_materials": ["graphite", "beryl"],
        },
        "cubic": {
            "symmetry": "highest",
            "constraints": "a = b = c, α = β = γ = 90°",
            "example_materials": ["diamond", "NaCl", "silicon"],
        },
    }
    return json.dumps(systems, indent=2)


# ============================================================================
# Prompts: Common Workflows
# ============================================================================

@mcp.prompt()
def analyze_material(material_id: str) -> str:
    """Generate a prompt for comprehensive material analysis."""
    return f"""Analyze the material with ID {material_id} from the Materials Project database.

Please:
1. First, use the get_properties tool to retrieve all properties for {material_id}
2. Summarize the key characteristics (composition, structure, stability)
3. Discuss the electronic properties (band gap, metallic/insulating)
4. Assess thermodynamic stability based on energy above hull
5. Suggest potential applications based on the properties
6. Recommend similar materials to compare using get_similar_structures

Provide a comprehensive analysis suitable for a materials scientist."""


@mcp.prompt()
def find_battery_materials(target_ion: str = "Li") -> str:
    """Generate a prompt for finding battery electrode materials."""
    return f"""Search for potential {target_ion}-ion battery electrode materials.

Requirements:
1. Search for materials containing {target_ion} using search_by_elements
2. Filter for stable materials (energy_above_hull < 0.05 eV)
3. Look for materials with layered or spinel structures
4. Compare band gaps - semiconductors may be better electrodes
5. Rank by formation energy (more negative = more stable)

Use the available tools to find and compare candidates.
Present your findings as a ranked list with justifications."""


@mcp.prompt()
def compare_alloy_compositions(base_elements: str = "Fe,Cr,Ni") -> str:
    """Generate a prompt for comparing alloy compositions."""
    elements = [e.strip() for e in base_elements.split(",")]
    return f"""Compare materials in the {'-'.join(elements)} alloy system.

Tasks:
1. Use search_by_elements with {elements} to find relevant phases
2. Get detailed properties for the most stable compositions
3. Compare crystal structures and symmetries
4. Analyze formation energies to predict stable compositions
5. Identify any magnetic materials in this system

Generate a comparison table and provide recommendations for alloy design."""


# ============================================================================
# Main Entry Point
# ============================================================================

def main():
    """Run the MCP server."""
    mcp.run()


if __name__ == "__main__":
    main()
