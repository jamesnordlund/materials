"""Tests for _validation.py -- validators and helper functions."""

import json
import unittest
from types import SimpleNamespace

from mcp_materials._validation import (
    _error_response,
    _validate_chemsys,
    _validate_elements,
    _validate_fields,
    _validate_formula,
    _validate_material_id,
    _validate_max_results,
    _validate_sort_dir,
)
from mcp_materials.mp_tools import _extract_crystal_system


class TestValidation(unittest.TestCase):
    def test_valid_material_id(self):
        self.assertIsNone(_validate_material_id("mp-149"))
        self.assertIsNone(_validate_material_id("mvc-12345"))

    def test_invalid_material_id_empty(self):
        self.assertIsNotNone(_validate_material_id(""))

    def test_invalid_material_id_bad_format(self):
        self.assertIsNotNone(_validate_material_id("foo-bar"))
        self.assertIsNotNone(_validate_material_id("mp149"))
        self.assertIsNotNone(_validate_material_id("mp-"))

    def test_max_results_valid(self):
        self.assertIsNone(_validate_max_results(1))
        self.assertIsNone(_validate_max_results(50))
        self.assertIsNone(_validate_max_results(100))

    def test_max_results_too_low(self):
        err = _validate_max_results(0)
        self.assertIn("at least 1", err)

    def test_max_results_too_high(self):
        err = _validate_max_results(101)
        self.assertIn("at most 100", err)

    def test_max_results_negative(self):
        err = _validate_max_results(-5)
        self.assertIn("at least 1", err)

    def test_valid_formula(self):
        self.assertIsNone(_validate_formula("Si"))
        self.assertIsNone(_validate_formula("Fe2O3"))
        self.assertIsNone(_validate_formula("LiFePO4"))
        self.assertIsNone(_validate_formula("Ca(OH)2"))

    def test_invalid_formula_empty(self):
        self.assertIsNotNone(_validate_formula(""))

    def test_invalid_formula_lowercase_start(self):
        self.assertIsNotNone(_validate_formula("si"))

    def test_valid_elements(self):
        self.assertIsNone(_validate_elements(["Li", "Fe", "O"]))
        self.assertIsNone(_validate_elements(["C"]))

    def test_invalid_elements_empty(self):
        self.assertIsNotNone(_validate_elements([]))

    def test_invalid_element_symbol(self):
        self.assertIsNotNone(_validate_elements(["Li", "notvalid"]))
        self.assertIsNotNone(_validate_elements([""]))


class TestValidateChemsys(unittest.TestCase):
    def test_valid_chemsys(self):
        self.assertIsNone(_validate_chemsys("Li-Fe-O"))

    def test_valid_chemsys_single_element(self):
        self.assertIsNone(_validate_chemsys("Li"))

    def test_valid_chemsys_two_elements(self):
        self.assertIsNone(_validate_chemsys("Li-O"))

    def test_invalid_chemsys_lowercase(self):
        err = _validate_chemsys("li-fe-o")
        self.assertIsNotNone(err)
        self.assertIn("chemsys", err.lower())

    def test_invalid_chemsys_trailing_dash(self):
        err = _validate_chemsys("Li-")
        self.assertIsNotNone(err)

    def test_invalid_chemsys_leading_dash(self):
        err = _validate_chemsys("-Fe")
        self.assertIsNotNone(err)

    def test_invalid_chemsys_empty(self):
        err = _validate_chemsys("")
        self.assertIsNotNone(err)


class TestValidateFields(unittest.TestCase):
    _AVAILABLE = frozenset({"material_id", "formula_pretty", "band_gap", "density"})

    def test_valid_fields(self):
        self.assertIsNone(_validate_fields(["material_id", "band_gap"], self._AVAILABLE))

    def test_invalid_fields(self):
        err = _validate_fields(["material_id", "bogus_field"], self._AVAILABLE)
        self.assertIsNotNone(err)
        self.assertIn("bogus_field", err)

    def test_all_invalid_fields(self):
        err = _validate_fields(["unknown1", "unknown2"], self._AVAILABLE)
        self.assertIsNotNone(err)
        self.assertIn("unknown1", err)
        self.assertIn("unknown2", err)

    def test_empty_fields_valid(self):
        # An empty list has no invalid entries
        self.assertIsNone(_validate_fields([], self._AVAILABLE))


class TestValidateSortDir(unittest.TestCase):
    def test_valid_asc(self):
        self.assertIsNone(_validate_sort_dir("asc"))

    def test_valid_desc(self):
        self.assertIsNone(_validate_sort_dir("desc"))

    def test_invalid_sort_dir(self):
        err = _validate_sort_dir("ascending")
        self.assertIsNotNone(err)
        self.assertIn("ascending", err)

    def test_invalid_sort_dir_empty(self):
        err = _validate_sort_dir("")
        self.assertIsNotNone(err)


class TestHelpers(unittest.TestCase):
    def test_error_response_simple(self):
        result = json.loads(_error_response("boom"))
        self.assertEqual(result["error"], "boom")

    def test_error_response_extra(self):
        result = json.loads(_error_response("fail", code=42))
        self.assertEqual(result["error"], "fail")
        self.assertEqual(result["code"], 42)

    def test_extract_crystal_system_none_symmetry(self):
        self.assertIsNone(_extract_crystal_system(None))

    def test_extract_crystal_system_plain_string(self):
        sym = SimpleNamespace(crystal_system="cubic")
        self.assertEqual(_extract_crystal_system(sym), "cubic")

    def test_extract_crystal_system_enum_value(self):
        enum_like = SimpleNamespace(value="hexagonal")
        sym = SimpleNamespace(crystal_system=enum_like)
        self.assertEqual(_extract_crystal_system(sym), "hexagonal")

    def test_extract_crystal_system_no_attr(self):
        sym = SimpleNamespace()
        self.assertIsNone(_extract_crystal_system(sym))


if __name__ == "__main__":
    unittest.main()
