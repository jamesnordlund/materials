"""Unit tests for the _utils.py shared utility module."""

import json
import os
import tempfile
import unittest

from tests.unit._utils import load_module


class TestUtils(unittest.TestCase):
    """Tests for functions in _utils.py."""

    @classmethod
    def setUpClass(cls):
        cls.mod = load_module(
            "_utils",
            "skills/simulation-workflow/post-processing/scripts/_utils.py",
        )

    def test_get_field_shape_rectangular(self):
        """Rectangular 2D array -> [2, 2]."""
        result = self.mod.get_field_shape([[1, 2], [3, 4]])
        self.assertEqual(result, [2, 2])

    def test_get_field_shape_3d(self):
        """3D array -> [2, 2, 2]."""
        field = [[[1, 2], [3, 4]], [[5, 6], [7, 8]]]
        result = self.mod.get_field_shape(field)
        self.assertEqual(result, [2, 2, 2])

    def test_get_field_shape_1d(self):
        """1D array -> [3]."""
        result = self.mod.get_field_shape([1, 2, 3])
        self.assertEqual(result, [3])

    def test_get_field_shape_empty(self):
        """Empty array -> [0]."""
        result = self.mod.get_field_shape([])
        self.assertEqual(result, [0])

    def test_get_field_shape_ragged(self):
        """Ragged array has -1 sentinel."""
        result = self.mod.get_field_shape([[1, 2], [3]])
        self.assertIn(-1, result)

    def test_flatten_field_1d(self):
        """1D list flattens to floats."""
        result = self.mod.flatten_field([1, 2, 3])
        self.assertEqual(result, [1.0, 2.0, 3.0])

    def test_flatten_field_2d(self):
        """2D list flattens to row-major floats."""
        result = self.mod.flatten_field([[1, 2], [3, 4]])
        self.assertEqual(result, [1.0, 2.0, 3.0, 4.0])

    def test_flatten_field_3d(self):
        """3D list flattens recursively."""
        result = self.mod.flatten_field([[[1], [2]], [[3], [4]]])
        self.assertEqual(result, [1.0, 2.0, 3.0, 4.0])

    def test_load_json_file(self):
        """load_json_file parses a JSON file."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as tmp:
            json.dump({"key": "value", "number": 42}, tmp)
            tmp_path = tmp.name
        try:
            data = self.mod.load_json_file(tmp_path)
            self.assertEqual(data["key"], "value")
            self.assertEqual(data["number"], 42)
        finally:
            os.unlink(tmp_path)

    def test_load_csv_file(self):
        """load_csv_file returns column-based dict."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as tmp:
            tmp.write("x,y\n1.0,2.0\n3.0,4.0\n")
            tmp_path = tmp.name
        try:
            data = self.mod.load_csv_file(tmp_path)
            self.assertEqual(data["x"], [1.0, 3.0])
            self.assertEqual(data["y"], [2.0, 4.0])
        finally:
            os.unlink(tmp_path)

    def test_get_field_data_direct(self):
        """Direct top-level key access."""
        data = {"phi": [1, 2, 3]}
        result = self.mod.get_field_data(data, "phi")
        self.assertEqual(result, [1, 2, 3])

    def test_get_field_data_nested_fields(self):
        """Access via nested fields dict."""
        data = {"fields": {"phi": [4, 5, 6]}}
        result = self.mod.get_field_data(data, "phi")
        self.assertEqual(result, [4, 5, 6])

    def test_get_field_data_nested_fields_values(self):
        """Access via nested fields with values sub-key."""
        data = {"fields": {"phi": {"values": [7, 8, 9]}}}
        result = self.mod.get_field_data(data, "phi")
        self.assertEqual(result, [7, 8, 9])

    def test_get_field_data_nested_data(self):
        """Access via _data dict."""
        data = {"_data": {"phi": [10, 11]}}
        result = self.mod.get_field_data(data, "phi")
        self.assertEqual(result, [10, 11])

    def test_get_field_data_missing(self):
        """Missing field returns None."""
        data = {"other": [1]}
        result = self.mod.get_field_data(data, "phi")
        self.assertIsNone(result)

    def test_ragged_array_handling(self):
        """Test REQ-F01: Ragged array handling in flatten_field and get_field_shape.

        Ragged arrays (arrays with inconsistent dimensions) should be handled gracefully.
        get_field_shape should detect raggedness and flatten_field should still flatten.
        """
        # Ragged 2D array: rows have different lengths
        ragged = [[1, 2, 3], [4, 5], [6]]

        # get_field_shape should detect raggedness (returns -1 sentinel)
        shape = self.mod.get_field_shape(ragged)
        self.assertIn(-1, shape)

        # flatten_field should still work on ragged arrays
        flattened = self.mod.flatten_field(ragged)
        self.assertEqual(flattened, [1.0, 2.0, 3.0, 4.0, 5.0, 6.0])

        # Test with deeply nested ragged structure
        ragged_3d = [[[1, 2], [3]], [[4]]]
        flattened_3d = self.mod.flatten_field(ragged_3d)
        self.assertEqual(flattened_3d, [1.0, 2.0, 3.0, 4.0])


if __name__ == "__main__":
    unittest.main()
