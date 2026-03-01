"""Tests for mp_provenance_tools.py -- provenance, tasks, and database version tools.

Fixture-based unit tests that mock MPRester and get_db_version to avoid
network calls.  Follows existing patterns in test_mp_tools.py.

Traces: R-MCP-001, R-MCP-002, R-MCP-021, R-TEST-002, R-TEST-003, R-SEC-015,
        R-OUT-001, R-ERR-001
"""

from __future__ import annotations

import asyncio
import json
import pathlib
import unittest
from datetime import datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

from mcp_materials.mp_provenance_tools import (
    mp_get_database_version,
    mp_provenance_get,
    mp_tasks_get,
)

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


def _make_provenance_doc(fixture: dict) -> SimpleNamespace:
    """Build a SimpleNamespace that mimics the mp-api provenance doc object.

    Datetime strings in the fixture are converted to real datetime objects
    so the production code's `hasattr(val, 'isoformat')` path is exercised.
    """
    doc = SimpleNamespace(**fixture)
    # Convert ISO strings to datetime objects (matching real API behaviour).
    for dt_field in ("last_updated", "created_at"):
        val = getattr(doc, dt_field, None)
        if isinstance(val, str):
            setattr(doc, dt_field, datetime.fromisoformat(val))
    return doc


def _make_task_doc(fixture: dict) -> SimpleNamespace:
    """Build a SimpleNamespace that mimics an mp-api task document.

    Converts ``last_updated`` ISO strings to real datetime objects so the
    production code's ``hasattr(val, 'isoformat')`` path is exercised.
    """
    doc = SimpleNamespace(**fixture)
    val = getattr(doc, "last_updated", None)
    if isinstance(val, str):
        doc.last_updated = datetime.fromisoformat(val)
    return doc


# ============================================================================
# mp_get_database_version tests
# ============================================================================


class TestMpGetDatabaseVersion(unittest.TestCase):
    """Tests for ``mp_get_database_version``."""

    @patch("mcp_materials.mp_provenance_tools.get_db_version", new_callable=AsyncMock)
    def test_returns_db_version_key(self, mock_get_db_version):
        """Result JSON contains a db_version key with the expected value."""
        version = _load_fixture("database_version.json")
        mock_get_db_version.return_value = (version, None)

        result = json.loads(asyncio.run(mp_get_database_version()))

        self.assertIn("records", result)
        self.assertEqual(len(result["records"]), 1)
        self.assertEqual(result["records"][0]["db_version"], "2026.2.1")

    @patch("mcp_materials.mp_provenance_tools.get_db_version", new_callable=AsyncMock)
    def test_output_schema_r_out_001(self, mock_get_db_version):
        """Response conforms to R-OUT-001: metadata, query, count, records, errors."""
        version = _load_fixture("database_version.json")
        mock_get_db_version.return_value = (version, None)

        result = json.loads(asyncio.run(mp_get_database_version()))

        # Top-level keys mandated by R-OUT-001.
        for key in ("metadata", "query", "count", "records", "errors"):
            self.assertIn(key, result, f"Missing top-level key: {key}")

        # Metadata sub-keys.
        metadata = result["metadata"]
        self.assertIn("db_version", metadata)
        self.assertIn("tool_name", metadata)
        self.assertIn("query_time_ms", metadata)
        self.assertEqual(metadata["tool_name"], "mp_get_database_version")
        self.assertEqual(metadata["db_version"], "2026.2.1")

        # Type checks.
        self.assertIsInstance(result["count"], int)
        self.assertIsInstance(result["records"], list)
        self.assertIsInstance(result["errors"], list)

    @patch("mcp_materials.mp_provenance_tools.get_db_version", new_callable=AsyncMock)
    def test_timeout_returns_timeout_error(self, mock_get_db_version):
        """TimeoutError yields error_category 'timeout_error' (R-ERR-001)."""
        mock_get_db_version.side_effect = TimeoutError("timed out")

        result = json.loads(asyncio.run(mp_get_database_version()))

        self.assertIn("error", result)
        self.assertEqual(result["error_category"], "timeout_error")
        self.assertIn("timed out", result["error"].lower())

    @patch("mcp_materials.mp_provenance_tools.get_db_version", new_callable=AsyncMock)
    def test_db_version_error_non_fatal(self, mock_get_db_version):
        """When get_db_version returns an error string, it appears in errors list."""
        mock_get_db_version.return_value = (None, "upstream unavailable")

        result = json.loads(asyncio.run(mp_get_database_version()))

        # Should still succeed (non-fatal per R-ERR-006).
        self.assertIn("records", result)
        self.assertIsNone(result["metadata"]["db_version"])
        self.assertTrue(len(result["errors"]) > 0)


# ============================================================================
# mp_provenance_get tests
# ============================================================================


class TestMpProvenanceGet(unittest.TestCase):
    """Tests for ``mp_provenance_get``."""

    @patch("mcp_materials.mp_provenance_tools.MPRester")
    @patch("mcp_materials.mp_provenance_tools.get_db_version", new_callable=AsyncMock)
    def test_returns_provenance_fields(self, mock_get_db_version, MockMPRester):
        """Valid call returns provenance fields from fixture."""
        fixture = _load_fixture("provenance_mp149.json")
        mock_get_db_version.return_value = ("2026.2.1", None)

        doc = _make_provenance_doc(fixture)
        ctx = MagicMock()
        mpr = MagicMock()
        ctx.__enter__ = MagicMock(return_value=mpr)
        ctx.__exit__ = MagicMock(return_value=False)
        MockMPRester.return_value = ctx
        mpr.materials.provenance.get_data_by_id.return_value = doc

        result = json.loads(asyncio.run(mp_provenance_get("mp-149")))

        self.assertIn("records", result)
        self.assertEqual(result["count"], 1)
        record = result["records"][0]
        self.assertEqual(record["material_id"], "mp-149")
        self.assertIn("task_ids", record)
        self.assertIsInstance(record["task_ids"], list)
        self.assertIn("last_updated", record)
        self.assertIn("created_at", record)
        self.assertIn("history", record)
        self.assertIn("authors", record)
        self.assertIn("remarks", record)

    @patch("mcp_materials.mp_provenance_tools.MPRester")
    @patch("mcp_materials.mp_provenance_tools.get_db_version", new_callable=AsyncMock)
    def test_task_ids_are_strings(self, mock_get_db_version, MockMPRester):
        """task_ids list items are converted to strings."""
        fixture = _load_fixture("provenance_mp149.json")
        mock_get_db_version.return_value = ("2026.2.1", None)

        doc = _make_provenance_doc(fixture)
        ctx = MagicMock()
        mpr = MagicMock()
        ctx.__enter__ = MagicMock(return_value=mpr)
        ctx.__exit__ = MagicMock(return_value=False)
        MockMPRester.return_value = ctx
        mpr.materials.provenance.get_data_by_id.return_value = doc

        result = json.loads(asyncio.run(mp_provenance_get("mp-149")))
        record = result["records"][0]

        for tid in record["task_ids"]:
            self.assertIsInstance(tid, str)

    @patch("mcp_materials.mp_provenance_tools.MPRester")
    @patch("mcp_materials.mp_provenance_tools.get_db_version", new_callable=AsyncMock)
    def test_datetime_fields_are_iso_strings(self, mock_get_db_version, MockMPRester):
        """Datetime fields are serialised to ISO-8601 strings."""
        fixture = _load_fixture("provenance_mp149.json")
        mock_get_db_version.return_value = ("2026.2.1", None)

        doc = _make_provenance_doc(fixture)
        ctx = MagicMock()
        mpr = MagicMock()
        ctx.__enter__ = MagicMock(return_value=mpr)
        ctx.__exit__ = MagicMock(return_value=False)
        MockMPRester.return_value = ctx
        mpr.materials.provenance.get_data_by_id.return_value = doc

        result = json.loads(asyncio.run(mp_provenance_get("mp-149")))
        record = result["records"][0]

        # Verify the datetime fields round-trip as parseable ISO strings.
        for dt_field in ("last_updated", "created_at"):
            val = record[dt_field]
            self.assertIsInstance(val, str)
            datetime.fromisoformat(val)  # should not raise

    @patch("mcp_materials.mp_provenance_tools.MPRester")
    @patch("mcp_materials.mp_provenance_tools.get_db_version", new_callable=AsyncMock)
    def test_output_schema_r_out_001(self, mock_get_db_version, MockMPRester):
        """Response conforms to R-OUT-001 schema structure."""
        fixture = _load_fixture("provenance_mp149.json")
        mock_get_db_version.return_value = ("2026.2.1", None)

        doc = _make_provenance_doc(fixture)
        ctx = MagicMock()
        mpr = MagicMock()
        ctx.__enter__ = MagicMock(return_value=mpr)
        ctx.__exit__ = MagicMock(return_value=False)
        MockMPRester.return_value = ctx
        mpr.materials.provenance.get_data_by_id.return_value = doc

        result = json.loads(asyncio.run(mp_provenance_get("mp-149")))

        # R-OUT-001 mandated top-level keys.
        for key in ("metadata", "query", "count", "records", "errors"):
            self.assertIn(key, result, f"Missing top-level key: {key}")

        metadata = result["metadata"]
        self.assertIn("db_version", metadata)
        self.assertIn("tool_name", metadata)
        self.assertIn("query_time_ms", metadata)
        self.assertEqual(metadata["tool_name"], "mp_provenance_get")

        # Query echo.
        self.assertEqual(result["query"]["material_id"], "mp-149")

        self.assertIsInstance(result["count"], int)
        self.assertIsInstance(result["records"], list)
        self.assertIsInstance(result["errors"], list)

    def test_invalid_material_id_returns_validation_error(self):
        """Invalid material_id returns error_category 'validation_error'."""
        result = json.loads(asyncio.run(mp_provenance_get("bad-id-999")))

        self.assertIn("error", result)
        self.assertEqual(result["error_category"], "validation_error")
        self.assertIn("Invalid material_id", result["error"])

    def test_empty_material_id_returns_validation_error(self):
        """Empty material_id returns error_category 'validation_error'."""
        result = json.loads(asyncio.run(mp_provenance_get("")))

        self.assertIn("error", result)
        self.assertEqual(result["error_category"], "validation_error")

    @patch("mcp_materials.mp_provenance_tools.MPRester")
    @patch("mcp_materials.mp_provenance_tools.get_db_version", new_callable=AsyncMock)
    def test_not_found_returns_not_found_error(self, mock_get_db_version, MockMPRester):
        """When the API returns None, error_category is 'not_found'."""
        mock_get_db_version.return_value = ("2026.2.1", None)

        ctx = MagicMock()
        mpr = MagicMock()
        ctx.__enter__ = MagicMock(return_value=mpr)
        ctx.__exit__ = MagicMock(return_value=False)
        MockMPRester.return_value = ctx
        mpr.materials.provenance.get_data_by_id.return_value = None

        result = json.loads(asyncio.run(mp_provenance_get("mp-999999")))

        self.assertIn("error", result)
        self.assertEqual(result["error_category"], "not_found")

    @patch("mcp_materials.mp_provenance_tools.get_db_version", new_callable=AsyncMock)
    @patch("mcp_materials.mp_provenance_tools.asyncio.wait_for")
    def test_timeout_returns_timeout_error(self, mock_wait_for, mock_get_db_version):
        """TimeoutError from asyncio.wait_for yields 'timeout_error' (R-ERR-001)."""
        mock_get_db_version.return_value = ("2026.2.1", None)
        mock_wait_for.side_effect = TimeoutError("timed out")

        result = json.loads(asyncio.run(mp_provenance_get("mp-149")))

        self.assertIn("error", result)
        self.assertEqual(result["error_category"], "timeout_error")
        self.assertIn("timed out", result["error"].lower())


# ============================================================================
# mp_tasks_get tests
# ============================================================================


class TestMpTasksGet(unittest.TestCase):
    """Tests for ``mp_tasks_get`` (TASK-024).

    Traces: R-MCP-021, R-OUT-001, R-TEST-002, R-TEST-003
    """

    def _mock_mprester(self, MockMPRester, docs):
        """Wire up MockMPRester context manager to return *docs* from search."""
        ctx = MagicMock()
        mpr = MagicMock()
        ctx.__enter__ = MagicMock(return_value=mpr)
        ctx.__exit__ = MagicMock(return_value=False)
        MockMPRester.return_value = ctx
        mpr.tasks.search.return_value = docs
        return mpr

    @patch("mcp_materials.mp_provenance_tools.MPRester")
    @patch("mcp_materials.mp_provenance_tools.get_db_version", new_callable=AsyncMock)
    def test_returns_task_records_with_expected_fields(
        self, mock_get_db_version, MockMPRester
    ):
        """mp_tasks_get('mp-149') returns task records with expected fields."""
        fixture = _load_fixture("tasks_mp149.json")
        mock_get_db_version.return_value = ("2026.2.1", None)

        docs = [_make_task_doc(entry) for entry in fixture]
        self._mock_mprester(MockMPRester, docs)

        result = json.loads(asyncio.run(mp_tasks_get("mp-149")))

        self.assertIn("records", result)
        self.assertEqual(result["count"], len(fixture))

        for record in result["records"]:
            self.assertIn("task_id", record)
            self.assertIsInstance(record["task_id"], str)
            self.assertIn("task_type", record)
            self.assertIn("last_updated", record)
            self.assertIn("input_parameters", record)
            self.assertIn("run_type", record)

    @patch("mcp_materials.mp_provenance_tools.MPRester")
    @patch("mcp_materials.mp_provenance_tools.get_db_version", new_callable=AsyncMock)
    def test_datetime_fields_are_iso_strings(
        self, mock_get_db_version, MockMPRester
    ):
        """last_updated fields are serialised to ISO-8601 strings."""
        fixture = _load_fixture("tasks_mp149.json")
        mock_get_db_version.return_value = ("2026.2.1", None)

        docs = [_make_task_doc(entry) for entry in fixture]
        self._mock_mprester(MockMPRester, docs)

        result = json.loads(asyncio.run(mp_tasks_get("mp-149")))

        for record in result["records"]:
            val = record["last_updated"]
            self.assertIsInstance(val, str)
            datetime.fromisoformat(val)  # should not raise

    def test_invalid_material_id_returns_validation_error(self):
        """Invalid material_id returns error_category 'validation_error'."""
        result = json.loads(asyncio.run(mp_tasks_get("bad-id-999")))

        self.assertIn("error", result)
        self.assertEqual(result["error_category"], "validation_error")
        self.assertIn("Invalid material_id", result["error"])

    def test_empty_material_id_returns_validation_error(self):
        """Empty material_id returns error_category 'validation_error'."""
        result = json.loads(asyncio.run(mp_tasks_get("")))

        self.assertIn("error", result)
        self.assertEqual(result["error_category"], "validation_error")

    @patch("mcp_materials.mp_provenance_tools.MPRester")
    @patch("mcp_materials.mp_provenance_tools.get_db_version", new_callable=AsyncMock)
    def test_output_schema_r_out_001(self, mock_get_db_version, MockMPRester):
        """Response conforms to R-OUT-001 schema structure."""
        fixture = _load_fixture("tasks_mp149.json")
        mock_get_db_version.return_value = ("2026.2.1", None)

        docs = [_make_task_doc(entry) for entry in fixture]
        self._mock_mprester(MockMPRester, docs)

        result = json.loads(asyncio.run(mp_tasks_get("mp-149")))

        # R-OUT-001 mandated top-level keys.
        for key in ("metadata", "query", "count", "records", "errors"):
            self.assertIn(key, result, f"Missing top-level key: {key}")

        metadata = result["metadata"]
        self.assertIn("db_version", metadata)
        self.assertIn("tool_name", metadata)
        self.assertIn("query_time_ms", metadata)
        self.assertEqual(metadata["tool_name"], "mp_tasks_get")
        self.assertEqual(metadata["db_version"], "2026.2.1")

        # Query echo.
        self.assertEqual(result["query"]["material_id"], "mp-149")

        self.assertIsInstance(result["count"], int)
        self.assertIsInstance(result["records"], list)
        self.assertIsInstance(result["errors"], list)

    @patch("mcp_materials.mp_provenance_tools.get_db_version", new_callable=AsyncMock)
    @patch("mcp_materials.mp_provenance_tools.asyncio.wait_for")
    def test_timeout_returns_timeout_error(self, mock_wait_for, mock_get_db_version):
        """TimeoutError from asyncio.wait_for yields 'timeout_error' (R-ERR-001)."""
        mock_get_db_version.return_value = ("2026.2.1", None)
        mock_wait_for.side_effect = TimeoutError("timed out")

        result = json.loads(asyncio.run(mp_tasks_get("mp-149")))

        self.assertIn("error", result)
        self.assertEqual(result["error_category"], "timeout_error")
        self.assertIn("timed out", result["error"].lower())


# ============================================================================
# Missing API key / dependency tests
# ============================================================================


class TestProvenanceToolsWithoutAPIKey(unittest.TestCase):
    """Verify graceful error when API key is missing."""

    def test_db_version_returns_error_without_key(self):
        import os
        from unittest.mock import patch as _patch

        with _patch.dict(os.environ, {}, clear=True):
            os.environ.pop("MP_API_KEY", None)
            os.environ.pop("PMG_MAPI_KEY", None)
            result = json.loads(asyncio.run(mp_get_database_version()))
            self.assertIn("error", result)
            self.assertIn("MP_API_KEY", result["error"])

    def test_provenance_get_returns_error_without_key(self):
        import os
        from unittest.mock import patch as _patch

        with _patch.dict(os.environ, {}, clear=True):
            os.environ.pop("MP_API_KEY", None)
            os.environ.pop("PMG_MAPI_KEY", None)
            result = json.loads(asyncio.run(mp_provenance_get("mp-149")))
            self.assertIn("error", result)
            self.assertIn("MP_API_KEY", result["error"])


# ============================================================================
# Tool callability tests
# ============================================================================


class TestProvenanceToolCallable(unittest.TestCase):
    """Verify tool functions are callable (basic import smoke test)."""

    def test_mp_get_database_version_is_callable(self):
        self.assertTrue(callable(mp_get_database_version))

    def test_mp_provenance_get_is_callable(self):
        self.assertTrue(callable(mp_provenance_get))

    def test_mp_tasks_get_is_callable(self):
        self.assertTrue(callable(mp_tasks_get))


if __name__ == "__main__":
    unittest.main()
