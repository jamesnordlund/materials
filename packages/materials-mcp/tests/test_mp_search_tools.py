"""Tests for mp_search_tools.py -- advanced summary search tool.

Fixture-based unit tests that mock MPRester and get_db_version to avoid
network calls.  Follows existing patterns in test_mp_provenance_tools.py.

Traces: R-MCP-003, R-MCP-007, R-MCP-008, R-OUT-001, R-OUT-002, R-OUT-004,
        R-ERR-001, R-ERR-007, R-TEST-002
"""

from __future__ import annotations

import asyncio
import json
import pathlib
import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

from mcp_materials.mp_search_tools import mp_summary_search_advanced

# ============================================================================
# Fixture loading
# ============================================================================

_FIXTURES = pathlib.Path(__file__).parent / "fixtures" / "mp"


def _load_fixture(name: str):
    """Load and return parsed JSON from the fixtures/mp/ directory."""
    return json.loads((_FIXTURES / name).read_text())


# ============================================================================
# Test helpers
# ============================================================================

_FAKE_KEY = "test-api-key-for-unit-tests"


def _make_summary_doc(fixture: dict) -> SimpleNamespace:
    """Build a SimpleNamespace that mimics an mp-api summary document.

    The ``symmetry`` sub-dict is converted to a nested SimpleNamespace whose
    ``crystal_system`` attribute exposes a ``.value`` property, matching the
    real API enum behaviour.
    """
    doc_data = dict(fixture)
    sym_raw = doc_data.pop("symmetry", None)
    doc = SimpleNamespace(**doc_data)
    if sym_raw is not None:
        cs_enum = SimpleNamespace(value=sym_raw["crystal_system"])
        sym_ns = SimpleNamespace(
            crystal_system=cs_enum,
            number=sym_raw.get("number"),
            symbol=sym_raw.get("symbol"),
        )
        doc.symmetry = sym_ns
    else:
        doc.symmetry = None
    return doc


def _load_summary_docs() -> list[SimpleNamespace]:
    """Load the summary_search_advanced fixture and convert to doc objects."""
    raw = _load_fixture("summary_search_advanced.json")
    return [_make_summary_doc(r) for r in raw]


def _configure_mprester_mock(
    mock_cls: MagicMock, docs: list[SimpleNamespace]
) -> None:
    """Configure a patched MPRester class mock as a context manager.

    After calling this, ``MPRester(key)`` returns a context manager whose
    ``__enter__`` returns a mock ``mpr`` with
    ``mpr.materials.summary.search()`` returning *docs*.
    """
    ctx = MagicMock()
    mpr = MagicMock()
    ctx.__enter__ = MagicMock(return_value=mpr)
    ctx.__exit__ = MagicMock(return_value=False)
    mock_cls.return_value = ctx
    mpr.materials.summary.search.return_value = docs


# ============================================================================
# Valid search tests
# ============================================================================


class TestValidSearch(unittest.TestCase):
    """Tests for successful mp_summary_search_advanced calls."""

    @patch("mcp_materials.mp_search_tools.MPRester")
    @patch("mcp_materials.mp_search_tools.get_db_version", new_callable=AsyncMock)
    def test_elements_filter_returns_r_out_001_schema(
        self, mock_get_db_version, MockMPRester
    ):
        """Valid search with elements filter returns R-OUT-001 schema."""
        docs = _load_summary_docs()
        mock_get_db_version.return_value = ("2026.2.1", None)
        _configure_mprester_mock(MockMPRester, docs)

        result = json.loads(
            asyncio.run(
                mp_summary_search_advanced(must_include_elements=["Si"])
            )
        )

        # R-OUT-001 mandated top-level keys.
        for key in ("metadata", "query", "count", "records", "errors"):
            self.assertIn(key, result, f"Missing top-level key: {key}")

        # Metadata sub-keys.
        metadata = result["metadata"]
        self.assertIn("db_version", metadata)
        self.assertIn("tool_name", metadata)
        self.assertIn("query_time_ms", metadata)
        self.assertEqual(metadata["tool_name"], "mp_summary_search_advanced")
        self.assertEqual(metadata["db_version"], "2026.2.1")

        # Type checks.
        self.assertIsInstance(result["count"], int)
        self.assertEqual(result["count"], 3)
        self.assertIsInstance(result["records"], list)
        self.assertIsInstance(result["errors"], list)

        # Query echo includes the elements filter.
        self.assertIn("must_include_elements", result["query"])
        self.assertEqual(result["query"]["must_include_elements"], ["Si"])

    @patch("mcp_materials.mp_search_tools.MPRester")
    @patch("mcp_materials.mp_search_tools.get_db_version", new_callable=AsyncMock)
    def test_output_includes_unit_suffixed_keys(
        self, mock_get_db_version, MockMPRester
    ):
        """Output keys use unit suffixes per R-OUT-002."""
        docs = _load_summary_docs()
        mock_get_db_version.return_value = ("2026.2.1", None)
        _configure_mprester_mock(MockMPRester, docs)

        result = json.loads(
            asyncio.run(
                mp_summary_search_advanced(must_include_elements=["Si"])
            )
        )

        record = result["records"][0]
        # Default fields include energy_above_hull, band_gap, density, volume.
        # These should be mapped to unit-suffixed keys.
        self.assertIn("energy_above_hull_eV", record)
        self.assertIn("band_gap_eV", record)
        self.assertIn("density_g_cm3", record)
        self.assertIn("volume_A3", record)

        # Raw keys without units should NOT be present.
        self.assertNotIn("energy_above_hull", record)
        self.assertNotIn("band_gap", record)
        self.assertNotIn("density", record)
        self.assertNotIn("volume", record)

    @patch("mcp_materials.mp_search_tools.MPRester")
    @patch("mcp_materials.mp_search_tools.get_db_version", new_callable=AsyncMock)
    def test_empty_result_set_returns_zero_count(
        self, mock_get_db_version, MockMPRester
    ):
        """Empty result set returns count: 0 and records: [] (not an error)."""
        mock_get_db_version.return_value = ("2026.2.1", None)
        _configure_mprester_mock(MockMPRester, [])

        result = json.loads(
            asyncio.run(
                mp_summary_search_advanced(must_include_elements=["Zr"])
            )
        )

        # Should NOT be an error response.
        self.assertNotIn("error", result)
        self.assertEqual(result["count"], 0)
        self.assertEqual(result["records"], [])

    @patch("mcp_materials.mp_search_tools.MPRester")
    @patch("mcp_materials.mp_search_tools.get_db_version", new_callable=AsyncMock)
    def test_records_contain_material_id_as_string(
        self, mock_get_db_version, MockMPRester
    ):
        """material_id values in records are converted to strings."""
        docs = _load_summary_docs()
        mock_get_db_version.return_value = ("2026.2.1", None)
        _configure_mprester_mock(MockMPRester, docs)

        result = json.loads(
            asyncio.run(
                mp_summary_search_advanced(must_include_elements=["Si"])
            )
        )

        for record in result["records"]:
            self.assertIn("material_id", record)
            self.assertIsInstance(record["material_id"], str)


# ============================================================================
# Validation error tests
# ============================================================================


class TestValidationErrors(unittest.TestCase):
    """Tests that invalid inputs return validation_error.

    All validation checks occur after _check_prerequisites (API key check).
    We mock _check_prerequisites to return success so that tests are
    self-contained and do not depend on environment variables.
    """

    @patch("mcp_materials.mp_search_tools._check_prerequisites")
    def test_invalid_field_name_returns_validation_error(self, mock_prereqs):
        """Unknown field in fields list returns validation_error."""
        mock_prereqs.return_value = (None, _FAKE_KEY)

        result = json.loads(
            asyncio.run(
                mp_summary_search_advanced(
                    must_include_elements=["Li"],
                    fields=["material_id", "nonexistent_field"],
                )
            )
        )

        self.assertIn("error", result)
        self.assertEqual(result["error_category"], "validation_error")
        self.assertIn("nonexistent_field", result["error"])

    @patch("mcp_materials.mp_search_tools._check_prerequisites")
    def test_max_results_zero_returns_validation_error(self, mock_prereqs):
        """max_results=0 returns validation_error."""
        mock_prereqs.return_value = (None, _FAKE_KEY)

        result = json.loads(
            asyncio.run(
                mp_summary_search_advanced(
                    must_include_elements=["Li"],
                    max_results=0,
                )
            )
        )

        self.assertIn("error", result)
        self.assertEqual(result["error_category"], "validation_error")
        self.assertIn("max_results", result["error"])

    @patch("mcp_materials.mp_search_tools._check_prerequisites")
    def test_max_results_over_100_returns_validation_error(self, mock_prereqs):
        """max_results=101 returns validation_error."""
        mock_prereqs.return_value = (None, _FAKE_KEY)

        result = json.loads(
            asyncio.run(
                mp_summary_search_advanced(
                    must_include_elements=["Li"],
                    max_results=101,
                )
            )
        )

        self.assertIn("error", result)
        self.assertEqual(result["error_category"], "validation_error")
        self.assertIn("max_results", result["error"])

    @patch("mcp_materials.mp_search_tools._check_prerequisites")
    def test_all_none_parameters_returns_validation_error(self, mock_prereqs):
        """No filters specified returns validation_error."""
        mock_prereqs.return_value = (None, _FAKE_KEY)

        result = json.loads(
            asyncio.run(mp_summary_search_advanced())
        )

        self.assertIn("error", result)
        self.assertEqual(result["error_category"], "validation_error")
        self.assertIn("at least one", result["error"].lower())

    @patch("mcp_materials.mp_search_tools._check_prerequisites")
    def test_invalid_sort_dir_returns_validation_error(self, mock_prereqs):
        """Invalid sort_dir returns validation_error."""
        mock_prereqs.return_value = (None, _FAKE_KEY)

        result = json.loads(
            asyncio.run(
                mp_summary_search_advanced(
                    must_include_elements=["Li"],
                    sort_dir="upward",
                )
            )
        )

        self.assertIn("error", result)
        self.assertEqual(result["error_category"], "validation_error")
        self.assertIn("sort_dir", result["error"])

    @patch("mcp_materials.mp_search_tools._check_prerequisites")
    def test_invalid_chemsys_returns_validation_error(self, mock_prereqs):
        """Invalid chemsys format returns validation_error."""
        mock_prereqs.return_value = (None, _FAKE_KEY)

        result = json.loads(
            asyncio.run(
                mp_summary_search_advanced(chemsys="not-a-chemsys!!!")
            )
        )

        self.assertIn("error", result)
        self.assertEqual(result["error_category"], "validation_error")
        self.assertIn("chemsys", result["error"].lower())


# ============================================================================
# Timeout / error tests
# ============================================================================


class TestTimeoutAndErrors(unittest.TestCase):
    """Tests for timeout and error handling."""

    @patch("mcp_materials.mp_search_tools.get_db_version", new_callable=AsyncMock)
    @patch("mcp_materials.mp_search_tools.asyncio.wait_for")
    def test_timeout_returns_timeout_error(self, mock_wait_for, mock_get_db_version):
        """TimeoutError from asyncio.wait_for yields timeout_error (R-ERR-001)."""
        mock_get_db_version.return_value = ("2026.2.1", None)
        mock_wait_for.side_effect = TimeoutError("timed out")

        result = json.loads(
            asyncio.run(
                mp_summary_search_advanced(must_include_elements=["Li"])
            )
        )

        self.assertIn("error", result)
        self.assertEqual(result["error_category"], "timeout_error")
        self.assertIn("timed out", result["error"].lower())


# ============================================================================
# Missing API key tests
# ============================================================================


class TestSearchWithoutAPIKey(unittest.TestCase):
    """Verify graceful error when API key is missing."""

    def test_search_returns_error_without_key(self):
        import os
        from unittest.mock import patch as _patch

        with _patch.dict(os.environ, {}, clear=True):
            os.environ.pop("MP_API_KEY", None)
            os.environ.pop("PMG_MAPI_KEY", None)
            result = json.loads(
                asyncio.run(
                    mp_summary_search_advanced(must_include_elements=["Li"])
                )
            )
            self.assertIn("error", result)
            self.assertIn("MP_API_KEY", result["error"])


# ============================================================================
# Callability smoke test
# ============================================================================


class TestSearchToolCallable(unittest.TestCase):
    """Verify tool function is callable (basic import smoke test)."""

    def test_mp_summary_search_advanced_is_callable(self):
        self.assertTrue(callable(mp_summary_search_advanced))


if __name__ == "__main__":
    unittest.main()
