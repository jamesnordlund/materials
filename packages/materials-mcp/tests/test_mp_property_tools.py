"""Tests for mp_property_tools.py -- insertion electrode search tool.

Fixture-based unit tests that mock MPRester and get_db_version to avoid
network calls.  Follows existing patterns in test_mp_provenance_tools.py.

Traces: R-MCP-010, R-OUT-001, R-OUT-002, R-ERR-001, R-TEST-002, R-TEST-003
"""

from __future__ import annotations

import asyncio
import json
import pathlib
import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from mcp_materials.mp_property_tools import mp_insertion_electrodes_search

from tests.conftest import _mock_mprester

# ============================================================================
# Fixture loading
# ============================================================================

_FIXTURES = pathlib.Path(__file__).parent / "fixtures" / "mp"


def _load_fixture(name: str) -> list[dict]:
    """Load and return parsed JSON from the fixtures/mp/ directory."""
    return json.loads((_FIXTURES / name).read_text())


def _make_electrode_doc(fixture: dict) -> SimpleNamespace:
    """Build a SimpleNamespace that mimics an mp-api InsertionElectrodeDoc.

    The production code accesses fields via ``getattr(doc, field, None)``,
    so a SimpleNamespace is sufficient.
    """
    return SimpleNamespace(**fixture)


# ============================================================================
# Valid search tests
# ============================================================================


class TestInsertionElectrodesSearchValid(unittest.TestCase):
    """Tests for valid ``mp_insertion_electrodes_search`` calls."""

    @patch("mcp_materials.mp_property_tools.get_db_version", new_callable=AsyncMock)
    @patch("mcp_materials.mp_property_tools.MPRester")
    def test_valid_search_returns_correct_schema(
        self, MockMPRester, mock_get_db_version
    ):
        """Valid search returns R-OUT-001 schema: metadata, query, count, records, errors."""
        fixtures = _load_fixture("insertion_electrodes.json")
        mock_get_db_version.return_value = ("2026.2.1", None)

        ctx, mpr = _mock_mprester()
        MockMPRester.return_value = ctx
        docs = [_make_electrode_doc(f) for f in fixtures]
        mpr.insertion_electrodes.search.return_value = docs

        result = json.loads(
            asyncio.run(mp_insertion_electrodes_search(working_ion="Li"))
        )

        # R-OUT-001 mandated top-level keys.
        for key in ("metadata", "query", "count", "records", "errors"):
            self.assertIn(key, result, f"Missing top-level key: {key}")

        # Metadata sub-keys.
        metadata = result["metadata"]
        self.assertIn("db_version", metadata)
        self.assertIn("tool_name", metadata)
        self.assertIn("query_time_ms", metadata)
        self.assertEqual(metadata["tool_name"], "mp_insertion_electrodes_search")
        self.assertEqual(metadata["db_version"], "2026.2.1")

        # Type checks.
        self.assertIsInstance(result["count"], int)
        self.assertIsInstance(result["records"], list)
        self.assertIsInstance(result["errors"], list)

        # Records should match fixture count.
        self.assertEqual(result["count"], 2)
        self.assertEqual(len(result["records"]), 2)

    @patch("mcp_materials.mp_property_tools.get_db_version", new_callable=AsyncMock)
    @patch("mcp_materials.mp_property_tools.MPRester")
    def test_unit_suffixed_keys_in_output(self, MockMPRester, mock_get_db_version):
        """Output records use unit-suffixed keys (R-OUT-002)."""
        fixtures = _load_fixture("insertion_electrodes.json")
        mock_get_db_version.return_value = ("2026.2.1", None)

        ctx, mpr = _mock_mprester()
        MockMPRester.return_value = ctx
        docs = [_make_electrode_doc(f) for f in fixtures]
        mpr.insertion_electrodes.search.return_value = docs

        result = json.loads(
            asyncio.run(mp_insertion_electrodes_search(working_ion="Li"))
        )

        record = result["records"][0]

        # Unit-suffixed keys from _ELECTRODE_UNIT_FIELD_MAP.
        expected_unit_keys = [
            "avg_voltage_V",
            "capacity_grav_mAh_g",
            "capacity_vol_mAh_cm3",
            "energy_grav_Wh_kg",
            "energy_vol_Wh_l",
            "max_delta_volume_pct",
            "stability_charge_eV",
            "stability_discharge_eV",
        ]
        for key in expected_unit_keys:
            self.assertIn(key, record, f"Missing unit-suffixed key: {key}")

        # Non-renamed fields should also be present.
        self.assertIn("battery_id", record)
        self.assertIn("working_ion", record)
        self.assertIn("formula_pretty", record)

    @patch("mcp_materials.mp_property_tools.get_db_version", new_callable=AsyncMock)
    @patch("mcp_materials.mp_property_tools.MPRester")
    def test_unit_suffixed_values_match_fixture(
        self, MockMPRester, mock_get_db_version
    ):
        """Unit-suffixed output values match the fixture source values."""
        fixtures = _load_fixture("insertion_electrodes.json")
        mock_get_db_version.return_value = ("2026.2.1", None)

        ctx, mpr = _mock_mprester()
        MockMPRester.return_value = ctx
        docs = [_make_electrode_doc(f) for f in fixtures]
        mpr.insertion_electrodes.search.return_value = docs

        result = json.loads(
            asyncio.run(mp_insertion_electrodes_search(working_ion="Li"))
        )
        record = result["records"][0]
        fixture = fixtures[0]

        self.assertEqual(record["avg_voltage_V"], fixture["average_voltage"])
        self.assertEqual(record["capacity_grav_mAh_g"], fixture["capacity_grav"])
        self.assertEqual(record["capacity_vol_mAh_cm3"], fixture["capacity_vol"])
        self.assertEqual(record["energy_grav_Wh_kg"], fixture["energy_grav"])
        self.assertEqual(record["energy_vol_Wh_l"], fixture["energy_vol"])
        self.assertEqual(record["max_delta_volume_pct"], fixture["max_delta_volume"])

    @patch("mcp_materials.mp_property_tools.get_db_version", new_callable=AsyncMock)
    @patch("mcp_materials.mp_property_tools.MPRester")
    def test_battery_id_stringified(self, MockMPRester, mock_get_db_version):
        """battery_id values are converted to strings."""
        fixtures = _load_fixture("insertion_electrodes.json")
        mock_get_db_version.return_value = ("2026.2.1", None)

        ctx, mpr = _mock_mprester()
        MockMPRester.return_value = ctx
        docs = [_make_electrode_doc(f) for f in fixtures]
        mpr.insertion_electrodes.search.return_value = docs

        result = json.loads(
            asyncio.run(mp_insertion_electrodes_search(working_ion="Li"))
        )
        for record in result["records"]:
            self.assertIsInstance(record["battery_id"], str)

    @patch("mcp_materials.mp_property_tools.get_db_version", new_callable=AsyncMock)
    @patch("mcp_materials.mp_property_tools.MPRester")
    def test_material_ids_are_string_list(self, MockMPRester, mock_get_db_version):
        """material_ids list items are converted to strings."""
        fixtures = _load_fixture("insertion_electrodes.json")
        mock_get_db_version.return_value = ("2026.2.1", None)

        ctx, mpr = _mock_mprester()
        MockMPRester.return_value = ctx
        docs = [_make_electrode_doc(f) for f in fixtures]
        mpr.insertion_electrodes.search.return_value = docs

        result = json.loads(
            asyncio.run(mp_insertion_electrodes_search(working_ion="Li"))
        )
        for record in result["records"]:
            self.assertIsInstance(record["material_ids"], list)
            for mid in record["material_ids"]:
                self.assertIsInstance(mid, str)

    @patch("mcp_materials.mp_property_tools.get_db_version", new_callable=AsyncMock)
    @patch("mcp_materials.mp_property_tools.MPRester")
    def test_query_echo_in_response(self, MockMPRester, mock_get_db_version):
        """Response includes a query echo reflecting the search parameters."""
        fixtures = _load_fixture("insertion_electrodes.json")
        mock_get_db_version.return_value = ("2026.2.1", None)

        ctx, mpr = _mock_mprester()
        MockMPRester.return_value = ctx
        docs = [_make_electrode_doc(f) for f in fixtures]
        mpr.insertion_electrodes.search.return_value = docs

        result = json.loads(
            asyncio.run(
                mp_insertion_electrodes_search(working_ion="Li", chemsys="Li-Fe-O")
            )
        )

        self.assertEqual(result["query"]["working_ion"], "Li")
        self.assertEqual(result["query"]["chemsys"], "Li-Fe-O")
        self.assertIn("max_results", result["query"])


# ============================================================================
# Empty result tests
# ============================================================================


class TestInsertionElectrodesSearchEmpty(unittest.TestCase):
    """Tests for empty result sets."""

    @patch("mcp_materials.mp_property_tools.get_db_version", new_callable=AsyncMock)
    @patch("mcp_materials.mp_property_tools.MPRester")
    def test_empty_result_returns_zero_count(self, MockMPRester, mock_get_db_version):
        """Empty API result yields count: 0 and records: []."""
        mock_get_db_version.return_value = ("2026.2.1", None)

        ctx, mpr = _mock_mprester()
        MockMPRester.return_value = ctx
        mpr.insertion_electrodes.search.return_value = []

        result = json.loads(
            asyncio.run(mp_insertion_electrodes_search(working_ion="Li"))
        )

        self.assertEqual(result["count"], 0)
        self.assertEqual(result["records"], [])
        # Should still conform to R-OUT-001.
        for key in ("metadata", "query", "count", "records", "errors"):
            self.assertIn(key, result)


# ============================================================================
# Validation error tests
# ============================================================================


class TestInsertionElectrodesSearchValidation(unittest.TestCase):
    """Tests for input validation returning validation_error."""

    def test_missing_all_params_returns_validation_error(self):
        """No working_ion, material_id, or chemsys returns validation_error."""
        result = json.loads(asyncio.run(mp_insertion_electrodes_search()))

        self.assertIn("error", result)
        self.assertEqual(result["error_category"], "validation_error")
        self.assertIn("At least one", result["error"])

    def test_invalid_material_id_returns_validation_error(self):
        """Invalid material_id format returns validation_error."""
        result = json.loads(
            asyncio.run(mp_insertion_electrodes_search(material_id="bad-id-999"))
        )

        self.assertIn("error", result)
        self.assertEqual(result["error_category"], "validation_error")
        self.assertIn("Invalid material_id", result["error"])

    def test_invalid_working_ion_returns_validation_error(self):
        """Invalid working_ion element returns validation_error."""
        result = json.loads(
            asyncio.run(mp_insertion_electrodes_search(working_ion="InvalidElement"))
        )

        self.assertIn("error", result)
        self.assertEqual(result["error_category"], "validation_error")
        self.assertIn("Invalid working_ion", result["error"])

    def test_invalid_chemsys_returns_validation_error(self):
        """Invalid chemsys format returns validation_error."""
        result = json.loads(
            asyncio.run(mp_insertion_electrodes_search(chemsys="not-valid"))
        )

        self.assertIn("error", result)
        self.assertEqual(result["error_category"], "validation_error")
        self.assertIn("Invalid chemsys", result["error"])


# ============================================================================
# Timeout and error tests
# ============================================================================


class TestInsertionElectrodesSearchErrors(unittest.TestCase):
    """Tests for timeout and API error handling."""

    @patch("mcp_materials.mp_property_tools.get_db_version", new_callable=AsyncMock)
    @patch("mcp_materials.mp_property_tools.asyncio.wait_for")
    def test_timeout_returns_timeout_error(self, mock_wait_for, mock_get_db_version):
        """TimeoutError from asyncio.wait_for yields 'timeout_error' (R-ERR-001)."""
        mock_get_db_version.return_value = ("2026.2.1", None)
        mock_wait_for.side_effect = TimeoutError("timed out")

        result = json.loads(
            asyncio.run(mp_insertion_electrodes_search(working_ion="Li"))
        )

        self.assertIn("error", result)
        self.assertEqual(result["error_category"], "timeout_error")
        self.assertIn("timed out", result["error"].lower())

    @patch("mcp_materials.mp_property_tools.get_db_version", new_callable=AsyncMock)
    @patch("mcp_materials.mp_property_tools.MPRester")
    def test_api_exception_returns_api_error(self, MockMPRester, mock_get_db_version):
        """Generic API exception yields 'api_error'."""
        mock_get_db_version.return_value = ("2026.2.1", None)

        ctx, mpr = _mock_mprester()
        MockMPRester.return_value = ctx
        mpr.insertion_electrodes.search.side_effect = RuntimeError("upstream failure")

        result = json.loads(
            asyncio.run(mp_insertion_electrodes_search(working_ion="Li"))
        )

        self.assertIn("error", result)
        self.assertEqual(result["error_category"], "api_error")

    @patch("mcp_materials.mp_property_tools.get_db_version", new_callable=AsyncMock)
    @patch("mcp_materials.mp_property_tools.MPRester")
    def test_db_version_error_non_fatal(self, MockMPRester, mock_get_db_version):
        """When get_db_version returns an error, response still succeeds (R-ERR-006)."""
        mock_get_db_version.return_value = (None, "upstream unavailable")

        ctx, mpr = _mock_mprester()
        MockMPRester.return_value = ctx
        mpr.insertion_electrodes.search.return_value = []

        result = json.loads(
            asyncio.run(mp_insertion_electrodes_search(working_ion="Li"))
        )

        # Should still return a valid response.
        self.assertIn("records", result)
        self.assertIsNone(result["metadata"]["db_version"])
        self.assertTrue(len(result["errors"]) > 0)


# ============================================================================
# Callability smoke test
# ============================================================================


class TestPropertyToolCallable(unittest.TestCase):
    """Verify tool function is callable (basic import smoke test)."""

    def test_mp_insertion_electrodes_search_is_callable(self):
        self.assertTrue(callable(mp_insertion_electrodes_search))


if __name__ == "__main__":
    unittest.main()
