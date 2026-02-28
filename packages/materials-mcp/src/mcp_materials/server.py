"""
Computational Materials Interface (CMI) - MCP Server

A specialized node for materials informatics, bridging:
1. The Materials Project (Thermodynamics, Electronic Structure)
2. MPContribs (Experimental & Community Data)

Designed for high-throughput screening and automated reasoning workflows.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Final

if TYPE_CHECKING:
    from mcp.server.fastmcp import FastMCP

from mcp_materials._prereqs import (
    HAS_MP_API,
    HAS_MPCONTRIBS,
)
from mcp_materials.contribs_tools import register_contribs_tools
from mcp_materials.mp_tools import register_mp_tools
from mcp_materials.resources import get_crystal_systems, get_periodic_table

# Configure structured logging
logger = logging.getLogger("mcp_materials.server")

# Constants
SERVER_NAME: Final[str] = "calc-mat-sci"
REF_NAMESPACE: Final[str] = "cmi://ref"

# Singleton holder
_server_instance: FastMCP | None = None


# ============================================================================
# Prompt Engineering: Specialized Workflows
# ============================================================================


def catalyst_feasibility_study(material_id: str) -> str:
    """Generate a technical brief for evaluating a catalyst candidate."""
    return (
        f"Conduct a feasibility study on material {material_id}"
        " for synthetic fuel catalysis (e.g., CO2RR or HER).\n"
        "\n"
        "Required Output Format: Technical Memo\n"
        "\n"
        "Steps:\n"
        "1. Properties: Retrieve electronic structure (band gap, DOS)"
        " and thermodynamics using 'get_properties'.\n"
        "2. Stability: Assess formation energy and hull distance."
        " Is it synthesizable?\n"
        "3. Benchmarking: Compare with known catalysts"
        " using 'get_similar_structures'.\n"
        "4. Conclusion: Rate the potential (High/Medium/Low)"
        " for industrial scalability.\n"
        "\n"
        "Focus on kinetic barriers and surface stability."
    )


def hydrogen_storage_screening(target_element: str = "Mg") -> str:
    """Generate a screening protocol for hydride storage materials."""
    return (
        "Execute a screening workflow for hydrogen storage"
        f" candidates containing {target_element}.\n"
        "\n"
        "Procedure:\n"
        "1. Broad Search: Use 'search_by_elements' to find"
        f" hydrides/frameworks with {target_element}.\n"
        "2. Filter: Isolate entries with energy_above_hull < 0.1 eV"
        " (metastable allowed).\n"
        "3. Mechanics: Check 'get_elastic_properties'"
        " - avoid brittle phases if possible.\n"
        "4. Capacity: Rank remaining candidates by theoretical"
        " gravimetric capacity.\n"
        "\n"
        "Report the top 3 candidates with their critical"
        " failure modes."
    )


def sorbent_selection_workflow(base_system: str = "Ca,O,Si") -> str:
    """Generate a workflow for selecting carbon capture sorbents."""
    elements = [e.strip() for e in base_system.split(",")]
    system = "-".join(elements)
    return (
        "Design a material selection process for Carbon Capture"
        f" within the {system} system.\n"
        "\n"
        "Analysis Vector:\n"
        "1. Phase Stability: Map the phase diagram using"
        " 'get_phase_diagram'. Identify stable carbonates.\n"
        "2. Thermodynamics: Calculate reaction enthalpy for"
        " CO2 uptake based on 'get_properties'.\n"
        "3. Competition: Check for competing phases that might"
        " poison the sorbent.\n"
        "4. Recommendation: Propose a specific composition"
        " for TGA testing.\n"
        "\n"
        "Provide a detailed thermodynamic justification."
    )


# ============================================================================
# Composition Root
# ============================================================================


def compose_server() -> FastMCP:
    """
    Assemble the FastMCP server instance.

    Registers:
    - Core Materials Project Tools
    - MPContribs Community Tools
    - Reference Resources
    - Domain-Specific Prompts
    """
    from mcp.server.fastmcp import FastMCP

    server = FastMCP(SERVER_NAME)

    # 1. Register Toolsets
    register_mp_tools(server)
    register_contribs_tools(server)

    # 2. Bind Resources (using CMI namespace)
    server.resource(f"{REF_NAMESPACE}/periodic-table")(get_periodic_table)
    server.resource(f"{REF_NAMESPACE}/crystal-systems")(get_crystal_systems)

    # 3. Bind Prompts
    server.prompt()(catalyst_feasibility_study)
    server.prompt()(hydrogen_storage_screening)
    server.prompt()(sorbent_selection_workflow)

    # Diagnostic Logging
    logger.info(
        "CMI Server Initialized: [MP_API=%s] [MP_CONTRIBS=%s]",
        "Active" if HAS_MP_API else "Missing",
        "Active" if HAS_MPCONTRIBS else "Missing",
    )

    return server


def get_shared_server() -> FastMCP:
    """Retrieve or initialize the global server instance."""
    global _server_instance  # noqa: PLW0603
    if _server_instance is None:
        _server_instance = compose_server()
    return _server_instance


def __getattr__(name: str):
    """Lazy-load the server instance."""
    if name == "mcp":
        return get_shared_server()
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


# Public API
__all__ = [
    "compose_server",
    "get_shared_server",
    "main",
    # Prompts are exported for testing/direct usage if needed
    "catalyst_feasibility_study",
    "hydrogen_storage_screening",
    "sorbent_selection_workflow",
]


# ============================================================================
# Entry Point
# ============================================================================


def main():
    """Start the CMI server."""
    get_shared_server().run()


if __name__ == "__main__":
    main()