"""
Tests for server.py -- configuration, resources, prompts, entry point.

Tool-level tests are in test_mp_tools.py and test_contribs_tools.py.
Validation tests are in test_validation.py.
"""

import json
import os
import unittest
from unittest.mock import patch

# =============================================================================
# Server Configuration Tests
# =============================================================================


class TestServerConfiguration:
    """Tests for MCP server setup and configuration."""

    def test_server_name(self):
        """Verify server has correct name."""
        from mcp_materials.server import get_shared_server
        server = get_shared_server()
        assert server.name == "calc-mat-sci"

    def test_server_imports_without_error(self):
        """Verify server module imports cleanly."""
        from mcp_materials import server
        assert server is not None

    def test_server_lazy_loading(self):
        """Verify __getattr__ lazy loading works."""
        from mcp_materials import server
        # This triggers __getattr__("mcp")
        assert server.mcp is not None
        assert server.mcp.name == "calc-mat-sci"


# =============================================================================
# API Key Configuration Tests
# =============================================================================


class TestAPIKeyHandling:
    """Tests for API key configuration (via _prereqs)."""

    def test_get_mp_api_key_returns_env_var(self):
        """Verify API key is read from environment."""
        from mcp_materials._prereqs import get_mp_api_key

        with patch.dict(os.environ, {"MP_API_KEY": "test_key_123"}):
            assert get_mp_api_key() == "test_key_123"

    def test_get_mp_api_key_returns_none_when_missing(self):
        """Verify None returned when API key not set."""
        from mcp_materials._prereqs import get_mp_api_key

        with patch.dict(os.environ, {}, clear=True):
            os.environ.pop("MP_API_KEY", None)
            os.environ.pop("PMG_MAPI_KEY", None)
            assert get_mp_api_key() is None


# =============================================================================
# Resource Tests
# =============================================================================


class TestPeriodicTableResource:
    """Tests for periodic table resource."""

    def test_returns_valid_json(self):
        from mcp_materials.server import get_periodic_table
        result = get_periodic_table()
        data = json.loads(result)
        assert isinstance(data, dict)
        assert "H" in data
        assert "Fe" in data

    def test_element_structure(self):
        from mcp_materials.server import get_periodic_table
        data = json.loads(get_periodic_table())
        assert data["H"]["name"] == "Hydrogen"
        assert data["Fe"]["atomic_number"] == 26


class TestCrystalSystemsResource:
    """Tests for crystal systems resource."""

    def test_returns_valid_json(self):
        from mcp_materials.server import get_crystal_systems
        result = get_crystal_systems()
        data = json.loads(result)
        assert len(data) == 7
        assert "cubic" in data
        assert data["cubic"]["symmetry"] == "highest"


# =============================================================================
# Prompt Tests
# =============================================================================


class TestPromptFunctions:
    """Tests for specialized prompt functions."""

    def test_catalyst_feasibility_study(self):
        from mcp_materials.server import catalyst_feasibility_study
        result = catalyst_feasibility_study("mp-1234")
        assert isinstance(result, str)
        assert "mp-1234" in result
        assert "Technical Memo" in result
        assert "kinetic barriers" in result

    def test_hydrogen_storage_screening(self):
        from mcp_materials.server import hydrogen_storage_screening
        result = hydrogen_storage_screening("Li")
        assert isinstance(result, str)
        assert "Li" in result
        assert "gravimetric capacity" in result

    def test_sorbent_selection_workflow(self):
        from mcp_materials.server import sorbent_selection_workflow
        result = sorbent_selection_workflow("Mg,O,C")
        assert isinstance(result, str)
        assert "Mg-O-C" in result  # joined with hyphen
        assert "TGA testing" in result


# =============================================================================
# Integration Tests
# =============================================================================


class TestServerToolRegistration(unittest.TestCase):
    """Verify all expected tools are registered on the FastMCP instance."""

    def test_total_tool_count(self):
        """23 tools expected: 10 MP + 3 Provenance + 1 Search + 1 Property + 8 Contribs."""
        from mcp_materials.server import get_shared_server
        server = get_shared_server()

        # NOTE: This accesses FastMCP private internals (_tool_manager._tools).
        # There is no public API to enumerate registered tools as of FastMCP 0.x.
        # If FastMCP changes its internal layout, this test will need updating.
        tool_count = len(server._tool_manager._tools)
        self.assertEqual(tool_count, 23)

    def test_cmi_resources_registered(self):
        """Verify resources use the new CMI namespace."""
        from mcp_materials.server import get_shared_server
        server = get_shared_server()
        
        # NOTE: This accesses FastMCP private internals (_resource_manager._resources).
        # There is no public API to enumerate registered resources as of FastMCP 0.x.
        # If FastMCP changes its internal layout, this test will need updating.
        resource_uris = list(server._resource_manager._resources.keys())
        
        self.assertIn("cmi://ref/periodic-table", resource_uris)
        self.assertIn("cmi://ref/crystal-systems", resource_uris)


# =============================================================================
# Startup Logging Tests
# =============================================================================


class TestStartupLogging(unittest.TestCase):
    """Server emits INFO log at startup."""

    def test_startup_info_log(self):
        import logging

        from mcp_materials.server import compose_server

        # Re-compose to trigger logging
        with self.assertLogs("mcp_materials.server", level=logging.INFO) as cm:
            compose_server()

        # Find the startup log message
        info_messages = [m for m in cm.output if "CMI Server Initialized" in m]
        self.assertTrue(
            len(info_messages) >= 1,
            f"Expected INFO log 'CMI Server Initialized', got: {cm.output}",
        )


if __name__ == "__main__":
    unittest.main()