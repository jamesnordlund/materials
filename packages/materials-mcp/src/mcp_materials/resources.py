"""Reference resources for the Materials MCP server."""

from __future__ import annotations

import json

try:
    from pymatgen.core.periodic_table import Element
except ImportError as _exc:
    raise ImportError(
        "pymatgen is required for reference resources. "
        "Install it with: pip install pymatgen"
    ) from _exc


def get_periodic_table() -> str:
    """Get periodic table data as a resource."""
    periodic_table = {}
    for el in Element:
        periodic_table[el.symbol] = {
            "name": el.long_name,
            "atomic_number": el.Z,
            "mass": float(el.atomic_mass),
        }
    return json.dumps(periodic_table, indent=2)


def get_crystal_systems() -> str:
    """Get crystal system reference data."""
    systems = {
        "cubic": {
            "symmetry": "highest",
            "constraints": "a = b = c, \u03b1 = \u03b2 = \u03b3 = 90\u00b0",
            "example_materials": ["diamond", "fluorite", "gold", "NaCl", "pyrite"],
        },
        "hexagonal": {
            "symmetry": "high",
            "constraints": "a = b \u2260 c, \u03b1 = \u03b2 = 90\u00b0, \u03b3 = 120\u00b0",
            "example_materials": ["apatite", "beryl", "graphite", "zincite"],
        },
        "monoclinic": {
            "symmetry": "low",
            "constraints": "a \u2260 b \u2260 c, \u03b1 = \u03b3 = 90\u00b0 \u2260 \u03b2",
            "example_materials": ["azurite", "gypsum", "muscovite", "orthoclase"],
        },
        "orthorhombic": {
            "symmetry": "medium",
            "constraints": "a \u2260 b \u2260 c, \u03b1 = \u03b2 = \u03b3 = 90\u00b0",
            "example_materials": ["aragonite", "olivine", "sulfur", "topaz"],
        },
        "tetragonal": {
            "symmetry": "medium-high",
            "constraints": "a = b \u2260 c, \u03b1 = \u03b2 = \u03b3 = 90\u00b0",
            "example_materials": ["anatase", "cassiterite", "rutile", "zircon"],
        },
        "triclinic": {
            "symmetry": "lowest",
            "constraints": (
                "a \u2260 b \u2260 c, \u03b1 \u2260 \u03b2 \u2260 \u03b3 \u2260 90\u00b0"
            ),
            "example_materials": ["albite", "kyanite", "microcline", "turquoise"],
        },
        "trigonal": {
            "symmetry": "medium-high",
            "constraints": "a = b = c, \u03b1 = \u03b2 = \u03b3 \u2260 90\u00b0",
            "example_materials": ["calcite", "hematite", "quartz", "ruby"],
        },
    }
    return json.dumps(systems, indent=2)
