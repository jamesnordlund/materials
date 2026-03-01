"""Tests for _output.py -- output builder and float sanitization."""

import json
import unittest

from mcp_materials._output import _build_response, _sanitize_floats


class TestSanitizeFloats(unittest.TestCase):
    """Tests for _sanitize_floats function."""

    def test_nan_replaced_with_none(self):
        """float('nan') is replaced with None."""
        result = _sanitize_floats(float("nan"))
        self.assertIsNone(result)

    def test_inf_replaced_with_none(self):
        """float('inf') is replaced with None."""
        result = _sanitize_floats(float("inf"))
        self.assertIsNone(result)

    def test_negative_inf_replaced_with_none(self):
        """float('-inf') is replaced with None."""
        result = _sanitize_floats(float("-inf"))
        self.assertIsNone(result)

    def test_nested_dict_with_nan(self):
        """NaN values in nested dicts are replaced with None."""
        data = {"a": {"b": float("nan"), "c": 1.0}, "d": float("inf")}
        result = _sanitize_floats(data)
        self.assertIsNone(result["a"]["b"])
        self.assertEqual(result["a"]["c"], 1.0)
        self.assertIsNone(result["d"])

    def test_nested_list_with_nan(self):
        """NaN values in nested lists are replaced with None."""
        data = [float("nan"), [float("inf"), 3.14], float("-inf")]
        result = _sanitize_floats(data)
        self.assertIsNone(result[0])
        self.assertIsNone(result[1][0])
        self.assertEqual(result[1][1], 3.14)
        self.assertIsNone(result[2])

    def test_mixed_nested_structures(self):
        """NaN values in mixed dict/list nesting are all replaced."""
        data = {"records": [{"value": float("nan")}, {"value": 42.0}]}
        result = _sanitize_floats(data)
        self.assertIsNone(result["records"][0]["value"])
        self.assertEqual(result["records"][1]["value"], 42.0)

    def test_normal_float_unchanged(self):
        """Normal float values are returned unchanged."""
        self.assertEqual(_sanitize_floats(3.14), 3.14)
        self.assertEqual(_sanitize_floats(0.0), 0.0)
        self.assertEqual(_sanitize_floats(-1.5), -1.5)

    def test_normal_int_unchanged(self):
        """Integer values are returned unchanged."""
        self.assertEqual(_sanitize_floats(42), 42)

    def test_string_unchanged(self):
        """String values are returned unchanged."""
        self.assertEqual(_sanitize_floats("hello"), "hello")

    def test_none_unchanged(self):
        """None values are returned unchanged."""
        self.assertIsNone(_sanitize_floats(None))

    def test_bool_unchanged(self):
        """Boolean values are returned unchanged."""
        self.assertTrue(_sanitize_floats(True))
        self.assertFalse(_sanitize_floats(False))

    def test_empty_dict(self):
        """Empty dict is returned as empty dict."""
        self.assertEqual(_sanitize_floats({}), {})

    def test_empty_list(self):
        """Empty list is returned as empty list."""
        self.assertEqual(_sanitize_floats([]), [])


class TestBuildResponse(unittest.TestCase):
    """Tests for _build_response function."""

    def test_top_level_keys(self):
        """Response contains all required top-level keys."""
        result = json.loads(
            _build_response("test_tool", {"q": "Si"}, [{"id": "mp-149"}])
        )
        expected_keys = {"metadata", "query", "count", "records", "errors"}
        self.assertEqual(set(result.keys()), expected_keys)

    def test_metadata_keys(self):
        """Metadata contains db_version, tool_name, query_time_ms."""
        result = json.loads(
            _build_response(
                "test_tool",
                {"q": "Si"},
                [],
                db_version="2024.01.01",
                query_time_ms=123.456,
            )
        )
        meta = result["metadata"]
        self.assertEqual(meta["db_version"], "2024.01.01")
        self.assertEqual(meta["tool_name"], "test_tool")
        self.assertEqual(meta["query_time_ms"], 123.5)

    def test_count_matches_records_length(self):
        """Count field matches the number of records."""
        records = [{"id": "mp-1"}, {"id": "mp-2"}, {"id": "mp-3"}]
        result = json.loads(
            _build_response("test_tool", {"q": "Fe"}, records)
        )
        self.assertEqual(result["count"], 3)
        self.assertEqual(result["count"], len(result["records"]))

    def test_empty_records(self):
        """Empty records produce count=0 and records=[]."""
        result = json.loads(
            _build_response("test_tool", {"q": "Unobtanium"}, [])
        )
        self.assertEqual(result["count"], 0)
        self.assertEqual(result["records"], [])

    def test_db_version_error_in_errors_list(self):
        """db_version_error appears in errors list."""
        result = json.loads(
            _build_response(
                "test_tool",
                {"q": "Si"},
                [],
                db_version_error="timeout fetching version",
            )
        )
        self.assertEqual(len(result["errors"]), 1)
        self.assertIn("timeout fetching version", result["errors"][0])

    def test_db_version_error_in_metadata(self):
        """db_version_error is set in metadata when provided."""
        result = json.loads(
            _build_response(
                "test_tool",
                {"q": "Si"},
                [],
                db_version_error="connection refused",
            )
        )
        self.assertEqual(
            result["metadata"]["db_version_error"], "connection refused"
        )

    def test_db_version_none_when_error(self):
        """db_version in metadata is None when there is an error."""
        result = json.loads(
            _build_response(
                "test_tool",
                {"q": "Si"},
                [],
                db_version_error="failed",
            )
        )
        self.assertIsNone(result["metadata"]["db_version"])

    def test_no_errors_when_no_version_error(self):
        """Errors list is empty when db_version_error is None."""
        result = json.loads(
            _build_response("test_tool", {"q": "Si"}, [], db_version="v1")
        )
        self.assertEqual(result["errors"], [])

    def test_note_appears_in_response(self):
        """Note key appears in response when note parameter is provided."""
        result = json.loads(
            _build_response(
                "test_tool",
                {"q": "Si"},
                [],
                note="Results truncated to 50 records.",
            )
        )
        self.assertIn("note", result)
        self.assertEqual(result["note"], "Results truncated to 50 records.")

    def test_note_absent_when_none(self):
        """Note key is absent when note parameter is None."""
        result = json.loads(
            _build_response("test_tool", {"q": "Si"}, [])
        )
        self.assertNotIn("note", result)

    def test_records_sanitized(self):
        """NaN/Inf in records are sanitized to None in output."""
        records = [{"value": float("nan"), "energy": float("inf")}]
        result = json.loads(
            _build_response("test_tool", {"q": "Si"}, records)
        )
        self.assertIsNone(result["records"][0]["value"])
        self.assertIsNone(result["records"][0]["energy"])

    def test_output_is_valid_json(self):
        """Output string is valid JSON that can be parsed."""
        raw = _build_response(
            "test_tool",
            {"q": "Si", "limit": 10},
            [{"id": "mp-149", "formula": "Si"}],
            db_version="2024.01.01",
            query_time_ms=42.0,
            note="test note",
        )
        # Should not raise
        parsed = json.loads(raw)
        self.assertIsInstance(parsed, dict)

    def test_query_preserved(self):
        """Query dict is preserved in the response."""
        query = {"elements": ["Si", "O"], "limit": 5}
        result = json.loads(
            _build_response("test_tool", query, [])
        )
        self.assertEqual(result["query"], query)

    def test_query_time_ms_rounded(self):
        """query_time_ms is rounded to one decimal place."""
        result = json.loads(
            _build_response(
                "test_tool", {}, [], query_time_ms=123.456789
            )
        )
        self.assertEqual(result["metadata"]["query_time_ms"], 123.5)


if __name__ == "__main__":
    unittest.main()
