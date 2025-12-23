"""
Comprehensive tests for MCP Materials Server.

Tests cover:
- Server configuration and initialization
- Resource functions (periodic table, crystal systems)
- Tool function signatures and basic validation
- API key handling
"""

import json
import os
from unittest.mock import patch


# =============================================================================
# Server Configuration Tests
# =============================================================================

class TestServerConfiguration:
    """Tests for MCP server setup and configuration."""

    def test_server_name(self):
        """Verify server has correct name."""
        from mcp_materials.server import mcp
        assert mcp.name == "materials-science"

    def test_server_imports_without_error(self):
        """Verify server module imports cleanly."""
        from mcp_materials import server
        assert server is not None

    def test_mcp_instance_exists(self):
        """Verify FastMCP instance is created."""
        from mcp_materials.server import mcp
        assert mcp is not None


# =============================================================================
# API Key Configuration Tests
# =============================================================================

class TestAPIKeyHandling:
    """Tests for API key configuration."""

    def test_get_mp_api_key_returns_env_var(self):
        """Verify API key is read from environment."""
        from mcp_materials.server import get_mp_api_key

        with patch.dict(os.environ, {"MP_API_KEY": "test_key_123"}):
            assert get_mp_api_key() == "test_key_123"

    def test_get_mp_api_key_returns_none_when_missing(self):
        """Verify None returned when API key not set."""
        from mcp_materials.server import get_mp_api_key

        with patch.dict(os.environ, {}, clear=True):
            # Remove MP_API_KEY if it exists
            os.environ.pop("MP_API_KEY", None)
            assert get_mp_api_key() is None

    def test_check_api_key_returns_error_when_missing(self):
        """Verify error message when API key not configured."""
        from mcp_materials.server import check_api_key

        with patch.dict(os.environ, {}, clear=True):
            os.environ.pop("MP_API_KEY", None)
            has_key, message = check_api_key()
            assert has_key is False
            assert "MP_API_KEY" in message
            assert "materialsproject.org" in message

    def test_check_api_key_returns_key_when_set(self):
        """Verify key returned when configured."""
        from mcp_materials.server import check_api_key

        with patch.dict(os.environ, {"MP_API_KEY": "my_api_key"}):
            has_key, key = check_api_key()
            assert has_key is True
            assert key == "my_api_key"


# =============================================================================
# Resource Tests
# =============================================================================

class TestPeriodicTableResource:
    """Tests for periodic table resource."""

    def test_returns_valid_json(self):
        """Verify periodic table returns valid JSON."""
        from mcp_materials.server import get_periodic_table

        result = get_periodic_table()
        data = json.loads(result)
        assert isinstance(data, dict)

    def test_contains_common_elements(self):
        """Verify common elements are present."""
        from mcp_materials.server import get_periodic_table

        data = json.loads(get_periodic_table())

        # Check essential elements
        assert "H" in data   # Hydrogen
        assert "C" in data   # Carbon
        assert "O" in data   # Oxygen
        assert "Fe" in data  # Iron
        assert "Si" in data  # Silicon
        assert "Li" in data  # Lithium

    def test_element_has_required_fields(self):
        """Verify element entries have required fields."""
        from mcp_materials.server import get_periodic_table

        data = json.loads(get_periodic_table())

        # Check hydrogen has all required fields
        hydrogen = data["H"]
        assert "name" in hydrogen
        assert "atomic_number" in hydrogen
        assert "mass" in hydrogen

        assert hydrogen["name"] == "Hydrogen"
        assert hydrogen["atomic_number"] == 1
        assert hydrogen["mass"] == 1.008

    def test_element_atomic_numbers_are_correct(self):
        """Verify atomic numbers are accurate."""
        from mcp_materials.server import get_periodic_table

        data = json.loads(get_periodic_table())

        assert data["He"]["atomic_number"] == 2
        assert data["C"]["atomic_number"] == 6
        assert data["Fe"]["atomic_number"] == 26
        assert data["Si"]["atomic_number"] == 14


class TestCrystalSystemsResource:
    """Tests for crystal systems resource."""

    def test_returns_valid_json(self):
        """Verify crystal systems returns valid JSON."""
        from mcp_materials.server import get_crystal_systems

        result = get_crystal_systems()
        data = json.loads(result)
        assert isinstance(data, dict)

    def test_has_seven_crystal_systems(self):
        """Verify all 7 crystal systems are defined."""
        from mcp_materials.server import get_crystal_systems

        data = json.loads(get_crystal_systems())
        assert len(data) == 7

    def test_contains_all_crystal_systems(self):
        """Verify all crystal system names are present."""
        from mcp_materials.server import get_crystal_systems

        data = json.loads(get_crystal_systems())

        expected_systems = [
            "triclinic",
            "monoclinic",
            "orthorhombic",
            "tetragonal",
            "trigonal",
            "hexagonal",
            "cubic",
        ]

        for system in expected_systems:
            assert system in data, f"Missing crystal system: {system}"

    def test_crystal_system_has_required_fields(self):
        """Verify crystal system entries have required fields."""
        from mcp_materials.server import get_crystal_systems

        data = json.loads(get_crystal_systems())

        # Check cubic system (most symmetric)
        cubic = data["cubic"]
        assert "symmetry" in cubic
        assert "constraints" in cubic
        assert "example_materials" in cubic

        assert cubic["symmetry"] == "highest"
        assert "diamond" in cubic["example_materials"]

    def test_symmetry_ordering(self):
        """Verify symmetry labels follow expected ordering."""
        from mcp_materials.server import get_crystal_systems

        data = json.loads(get_crystal_systems())

        assert data["triclinic"]["symmetry"] == "lowest"
        assert data["cubic"]["symmetry"] == "highest"


# =============================================================================
# Tool Function Tests
# =============================================================================

class TestToolFunctions:
    """Tests for tool function availability and signatures."""

    def test_search_materials_is_callable(self):
        """Verify search_materials function exists and is callable."""
        from mcp_materials.server import search_materials
        assert callable(search_materials)

    def test_get_structure_is_callable(self):
        """Verify get_structure function exists and is callable."""
        from mcp_materials.server import get_structure
        assert callable(get_structure)

    def test_get_properties_is_callable(self):
        """Verify get_properties function exists and is callable."""
        from mcp_materials.server import get_properties
        assert callable(get_properties)

    def test_compare_materials_is_callable(self):
        """Verify compare_materials function exists and is callable."""
        from mcp_materials.server import compare_materials
        assert callable(compare_materials)

    def test_search_by_elements_is_callable(self):
        """Verify search_by_elements function exists and is callable."""
        from mcp_materials.server import search_by_elements
        assert callable(search_by_elements)

    def test_search_by_band_gap_is_callable(self):
        """Verify search_by_band_gap function exists and is callable."""
        from mcp_materials.server import search_by_band_gap
        assert callable(search_by_band_gap)

    def test_get_similar_structures_is_callable(self):
        """Verify get_similar_structures function exists and is callable."""
        from mcp_materials.server import get_similar_structures
        assert callable(get_similar_structures)

    def test_get_phase_diagram_is_callable(self):
        """Verify get_phase_diagram function exists and is callable."""
        from mcp_materials.server import get_phase_diagram
        assert callable(get_phase_diagram)

    def test_get_elastic_properties_is_callable(self):
        """Verify get_elastic_properties function exists and is callable."""
        from mcp_materials.server import get_elastic_properties
        assert callable(get_elastic_properties)

    def test_search_by_elastic_properties_is_callable(self):
        """Verify search_by_elastic_properties function exists and is callable."""
        from mcp_materials.server import search_by_elastic_properties
        assert callable(search_by_elastic_properties)


class TestToolsWithoutAPIKey:
    """Tests for tool behavior when API key is missing."""

    def test_search_materials_returns_error_without_key(self):
        """Verify search_materials returns error when API key missing."""
        from mcp_materials.server import search_materials

        with patch.dict(os.environ, {}, clear=True):
            os.environ.pop("MP_API_KEY", None)
            result = json.loads(search_materials("Si"))
            assert "error" in result
            assert "MP_API_KEY" in result["error"]

    def test_get_properties_returns_error_without_key(self):
        """Verify get_properties returns error when API key missing."""
        from mcp_materials.server import get_properties

        with patch.dict(os.environ, {}, clear=True):
            os.environ.pop("MP_API_KEY", None)
            result = json.loads(get_properties("mp-149"))
            assert "error" in result

    def test_get_elastic_properties_returns_error_without_key(self):
        """Verify get_elastic_properties returns error when API key missing."""
        from mcp_materials.server import get_elastic_properties

        with patch.dict(os.environ, {}, clear=True):
            os.environ.pop("MP_API_KEY", None)
            result = json.loads(get_elastic_properties("mp-149"))
            assert "error" in result

    def test_get_phase_diagram_returns_error_without_key(self):
        """Verify get_phase_diagram returns error when API key missing."""
        from mcp_materials.server import get_phase_diagram

        with patch.dict(os.environ, {}, clear=True):
            os.environ.pop("MP_API_KEY", None)
            result = json.loads(get_phase_diagram(["Li", "O"]))
            assert "error" in result


# =============================================================================
# Prompt Tests
# =============================================================================

class TestPromptFunctions:
    """Tests for prompt function availability."""

    def test_analyze_material_prompt_is_callable(self):
        """Verify analyze_material prompt exists."""
        from mcp_materials.server import analyze_material
        assert callable(analyze_material)

    def test_find_battery_materials_prompt_is_callable(self):
        """Verify find_battery_materials prompt exists."""
        from mcp_materials.server import find_battery_materials
        assert callable(find_battery_materials)

    def test_compare_alloy_compositions_prompt_is_callable(self):
        """Verify compare_alloy_compositions prompt exists."""
        from mcp_materials.server import compare_alloy_compositions
        assert callable(compare_alloy_compositions)

    def test_analyze_material_returns_string(self):
        """Verify analyze_material returns a prompt string."""
        from mcp_materials.server import analyze_material

        result = analyze_material("mp-149")
        assert isinstance(result, str)
        assert "mp-149" in result
        assert "get_properties" in result

    def test_find_battery_materials_returns_string(self):
        """Verify find_battery_materials returns a prompt string."""
        from mcp_materials.server import find_battery_materials

        result = find_battery_materials("Na")
        assert isinstance(result, str)
        assert "Na" in result
        assert "battery" in result.lower()

    def test_compare_alloy_compositions_returns_string(self):
        """Verify compare_alloy_compositions returns a prompt string."""
        from mcp_materials.server import compare_alloy_compositions

        result = compare_alloy_compositions("Fe,Ni,Co")
        assert isinstance(result, str)
        assert "Fe" in result
        assert "Ni" in result


# =============================================================================
# Main Entry Point Tests
# =============================================================================

class TestMainEntryPoint:
    """Tests for main entry point."""

    def test_main_function_exists(self):
        """Verify main function exists."""
        from mcp_materials.server import main
        assert callable(main)
