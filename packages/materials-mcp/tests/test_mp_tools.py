"""Tests for mp_tools.py -- Materials Project tool functions."""

import asyncio
import json
import os
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from mcp_materials.mp_tools import (
    compare_materials,
    get_elastic_properties,
    get_phase_diagram,
    get_properties,
    get_similar_structures,
    get_structure,
    search_by_band_gap,
    search_by_elastic_properties,
    search_by_elements,
    search_materials,
)
from tests.conftest import _make_summary_doc, _mock_mprester

# =============================================================================
# Mocked Tool Tests
# =============================================================================


class TestSearchMaterialsMocked(unittest.TestCase):
    @patch("mcp_materials.mp_tools.MPRester")
    def test_valid_results(self, MockMPRester):
        ctx, mpr = _mock_mprester()
        MockMPRester.return_value = ctx
        doc = _make_summary_doc()
        mpr.materials.summary.search.return_value = [doc]

        result = json.loads(asyncio.run(search_materials("Si", max_results=5)))
        self.assertEqual(result["count"], 1)
        self.assertEqual(result["materials"][0]["material_id"], "mp-149")

    @patch("mcp_materials.mp_tools.MPRester")
    def test_max_results_limit(self, MockMPRester):
        ctx, mpr = _mock_mprester()
        MockMPRester.return_value = ctx
        docs = [_make_summary_doc(material_id=f"mp-{i}") for i in range(20)]
        mpr.materials.summary.search.return_value = docs

        result = json.loads(asyncio.run(search_materials("Si", max_results=3)))
        self.assertEqual(result["count"], 3)

    @patch("mcp_materials.mp_tools.MPRester")
    def test_none_symmetry_handled(self, MockMPRester):
        ctx, mpr = _mock_mprester()
        MockMPRester.return_value = ctx
        doc = _make_summary_doc(symmetry=None)
        mpr.materials.summary.search.return_value = [doc]

        result = json.loads(asyncio.run(search_materials("X")))
        mat = result["materials"][0]
        self.assertIsNone(mat["crystal_system"])
        self.assertIsNone(mat["space_group"])

    @patch("mcp_materials.mp_tools.MPRester")
    def test_api_exception(self, MockMPRester):
        ctx, mpr = _mock_mprester()
        MockMPRester.return_value = ctx
        mpr.materials.summary.search.side_effect = RuntimeError("API down")

        result = json.loads(asyncio.run(search_materials("Si")))
        self.assertIn("error", result)
        self.assertIn("API down", result["error"])


class TestGetPropertiesMocked(unittest.TestCase):
    @patch("mcp_materials.mp_tools.MPRester")
    def test_all_property_fields(self, MockMPRester):
        ctx, mpr = _mock_mprester()
        MockMPRester.return_value = ctx
        mpr.materials.summary.get_data_by_id.return_value = _make_summary_doc()

        result = json.loads(asyncio.run(get_properties("mp-149")))
        for key in [
            "material_id", "formula", "elements", "band_gap",
            "crystal_system", "space_group_number", "formation_energy_per_atom",
        ]:
            self.assertIn(key, result)


class TestCompareMaterialsMocked(unittest.TestCase):
    @patch("mcp_materials.mp_tools.MPRester")
    def test_two_materials(self, MockMPRester):
        ctx, mpr = _mock_mprester()
        MockMPRester.return_value = ctx
        doc1 = _make_summary_doc(material_id="mp-149", formula_pretty="Si")
        doc2 = _make_summary_doc(material_id="mp-66", formula_pretty="C")
        mpr.materials.summary.get_data_by_id.side_effect = [doc1, doc2]

        result = json.loads(asyncio.run(compare_materials(["mp-149", "mp-66"])))
        self.assertEqual(result["count"], 2)

    @patch("mcp_materials.mp_tools.MPRester")
    def test_per_material_error(self, MockMPRester):
        ctx, mpr = _mock_mprester()
        MockMPRester.return_value = ctx
        mpr.materials.summary.get_data_by_id.side_effect = RuntimeError("not found")

        result = json.loads(asyncio.run(compare_materials(["mp-999"])))
        self.assertEqual(result["count"], 1)
        self.assertIn("error", result["comparison"][0])


class TestSearchByBandGapMocked(unittest.TestCase):
    @patch("mcp_materials.mp_tools.MPRester")
    def test_range_query(self, MockMPRester):
        ctx, mpr = _mock_mprester()
        MockMPRester.return_value = ctx
        doc = _make_summary_doc(band_gap=1.5)
        mpr.materials.summary.search.return_value = [doc]

        result = json.loads(asyncio.run(search_by_band_gap(min_gap=1.0, max_gap=2.0)))
        self.assertEqual(result["count"], 1)

    @patch("mcp_materials.mp_tools.MPRester")
    def test_direct_gap_only_forwarded(self, MockMPRester):
        ctx, mpr = _mock_mprester()
        MockMPRester.return_value = ctx
        mpr.materials.summary.search.return_value = []

        asyncio.run(search_by_band_gap(direct_gap_only=True))
        kwargs = mpr.materials.summary.search.call_args[1]
        self.assertTrue(kwargs.get("is_gap_direct"))


class TestSearchByElasticPropertiesMocked(unittest.TestCase):
    @patch("mcp_materials.mp_tools.MPRester")
    def test_zero_bulk_modulus_preserved(self, MockMPRester):
        """Regression for C1: zero values must not be filtered out by truthiness check."""
        ctx, mpr = _mock_mprester()
        MockMPRester.return_value = ctx

        doc = SimpleNamespace(
            material_id="mp-1",
            formula_pretty="X",
            bulk_modulus=SimpleNamespace(vrh=0.0, voigt=0.0, reuss=0.0),
            shear_modulus=SimpleNamespace(vrh=50.0, voigt=50.0, reuss=50.0),
            universal_anisotropy=0.1,
        )
        mpr.materials.elasticity.search.return_value = [doc]

        result = json.loads(asyncio.run(search_by_elastic_properties(min_bulk_modulus=0.0)))
        self.assertEqual(result["materials"][0]["bulk_modulus_GPa"], 0.0)

    @patch("mcp_materials.mp_tools.MPRester")
    def test_zero_shear_modulus_preserved(self, MockMPRester):
        """Regression for C1: zero values must not be filtered out by truthiness check."""
        ctx, mpr = _mock_mprester()
        MockMPRester.return_value = ctx

        doc = SimpleNamespace(
            material_id="mp-2",
            formula_pretty="Y",
            bulk_modulus=SimpleNamespace(vrh=100.0, voigt=100.0, reuss=100.0),
            shear_modulus=SimpleNamespace(vrh=0.0, voigt=0.0, reuss=0.0),
            universal_anisotropy=0.0,
        )
        mpr.materials.elasticity.search.return_value = [doc]

        result = json.loads(asyncio.run(search_by_elastic_properties(min_shear_modulus=0.0)))
        self.assertEqual(result["materials"][0]["shear_modulus_GPa"], 0.0)


class TestGetSimilarStructuresMocked(unittest.TestCase):
    @patch("mcp_materials.mp_tools.MPRester")
    def test_self_exclusion(self, MockMPRester):
        ctx, mpr = _mock_mprester()
        MockMPRester.return_value = ctx
        ref_doc = _make_summary_doc(material_id="mp-149")
        other_doc = _make_summary_doc(material_id="mp-200", formula_pretty="Ge")
        mpr.materials.summary.get_data_by_id.return_value = ref_doc
        mpr.materials.summary.search.return_value = [ref_doc, other_doc]

        result = json.loads(asyncio.run(get_similar_structures("mp-149")))
        ids = [s["material_id"] for s in result["similar_structures"]]
        self.assertNotIn("mp-149", ids)
        self.assertIn("mp-200", ids)

    @patch("mcp_materials.mp_tools.MPRester")
    def test_missing_space_group(self, MockMPRester):
        ctx, mpr = _mock_mprester()
        MockMPRester.return_value = ctx
        ref_doc = _make_summary_doc(symmetry=None)
        mpr.materials.summary.get_data_by_id.return_value = ref_doc

        result = json.loads(asyncio.run(get_similar_structures("mp-149")))
        self.assertIn("error", result)


class TestGetStructureMocked(unittest.TestCase):
    @patch("mcp_materials.mp_tools.CifWriter")
    @patch("mcp_materials.mp_tools.MPRester")
    def test_cif_output(self, MockMPRester, MockCifWriter):
        from unittest.mock import MagicMock

        ctx, mpr = _mock_mprester()
        MockMPRester.return_value = ctx
        mock_structure = MagicMock()
        mpr.get_structure_by_material_id.return_value = mock_structure
        MockCifWriter.return_value.__str__ = MagicMock(
            return_value="data_cif\nloop_\n"
        )

        result = asyncio.run(get_structure("mp-149", output_format="cif"))
        self.assertIn("data_cif", result)
        MockCifWriter.assert_called_once_with(mock_structure)

    @patch("mcp_materials.mp_tools.Poscar")
    @patch("mcp_materials.mp_tools.MPRester")
    def test_poscar_output(self, MockMPRester, MockPoscar):
        from unittest.mock import MagicMock

        ctx, mpr = _mock_mprester()
        MockMPRester.return_value = ctx
        mock_structure = MagicMock()
        mpr.get_structure_by_material_id.return_value = mock_structure
        MockPoscar.return_value.get_str.return_value = "Si\n1.0\n"

        result = asyncio.run(get_structure("mp-149", output_format="poscar"))
        self.assertIn("Si", result)

    @patch("mcp_materials.mp_tools.MPRester")
    def test_json_output(self, MockMPRester):
        from unittest.mock import MagicMock

        ctx, mpr = _mock_mprester()
        MockMPRester.return_value = ctx
        mock_structure = MagicMock()
        mock_structure.to_json.return_value = '{"lattice": {}}'
        mpr.get_structure_by_material_id.return_value = mock_structure

        result = asyncio.run(get_structure("mp-149", output_format="json"))
        self.assertIn("lattice", result)

    def test_invalid_material_id(self):
        result = json.loads(asyncio.run(get_structure("bad-id")))
        self.assertIn("error", result)

    def test_invalid_format(self):
        result = json.loads(asyncio.run(get_structure("mp-149", output_format="xyz")))
        self.assertIn("error", result)


class TestGetPhaseDiagramMocked(unittest.TestCase):
    @patch("mcp_materials.mp_tools.MPRester")
    def test_phase_diagram_results(self, MockMPRester):
        ctx, mpr = _mock_mprester()
        MockMPRester.return_value = ctx

        # Create mock entries with compositions
        stable_entry = SimpleNamespace(
            entry_id="mp-149",
            composition=SimpleNamespace(reduced_formula="Si"),
            energy_per_atom=-5.0,
        )
        unstable_entry = SimpleNamespace(
            entry_id="mp-999",
            composition=SimpleNamespace(reduced_formula="SiO"),
            energy_per_atom=-4.0,
        )
        mpr.get_entries_in_chemsys.return_value = [stable_entry, unstable_entry]

        # Mock PhaseDiagram
        with patch("mcp_materials.mp_tools.PhaseDiagram") as MockPD:
            pd_instance = MockPD.return_value
            pd_instance.stable_entries = [stable_entry]
            pd_instance.unstable_entries = [unstable_entry]
            pd_instance.get_form_energy_per_atom.return_value = -0.5
            pd_instance.get_decomp_and_e_above_hull.return_value = (
                [stable_entry], 0.1
            )

            result = json.loads(
                asyncio.run(get_phase_diagram(["Si", "O"]))
            )
            self.assertEqual(result["chemical_system"], "O-Si")
            self.assertEqual(result["stable_phases"]["count"], 1)
            self.assertEqual(result["unstable_phases"]["count"], 1)

    @patch("mcp_materials.mp_tools.MPRester")
    def test_no_entries(self, MockMPRester):
        ctx, mpr = _mock_mprester()
        MockMPRester.return_value = ctx
        mpr.get_entries_in_chemsys.return_value = []

        result = json.loads(asyncio.run(get_phase_diagram(["X", "Y"])))
        self.assertIn("error", result)

    def test_invalid_elements(self):
        result = json.loads(asyncio.run(get_phase_diagram([])))
        self.assertIn("error", result)


class TestSearchByBandGapValidation(unittest.TestCase):
    def test_min_gap_greater_than_max_gap(self):
        result = json.loads(
            asyncio.run(search_by_band_gap(min_gap=5.0, max_gap=2.0))
        )
        self.assertIn("error", result)
        self.assertIn("min_gap", result["error"])


class TestGetElasticPropertiesMocked(unittest.TestCase):
    @patch("mcp_materials.mp_tools.MPRester")
    def test_elastic_fields(self, MockMPRester):
        ctx, mpr = _mock_mprester()
        MockMPRester.return_value = ctx

        doc = SimpleNamespace(
            material_id="mp-149",
            formula_pretty="Si",
            bulk_modulus=SimpleNamespace(vrh=98.0, voigt=100.0, reuss=96.0),
            shear_modulus=SimpleNamespace(vrh=66.0, voigt=68.0, reuss=64.0),
            young_modulus=160.0,
            homogeneous_poisson=0.22,
            universal_anisotropy=0.04,
            debye_temperature=640.0,
            state=SimpleNamespace(value="successful"),
        )
        mpr.materials.elasticity.search.return_value = [doc]

        result = json.loads(asyncio.run(get_elastic_properties("mp-149")))
        self.assertEqual(result["bulk_modulus_vrh_GPa"], 98.0)
        self.assertEqual(result["shear_modulus_vrh_GPa"], 66.0)

    @patch("mcp_materials.mp_tools.MPRester")
    def test_no_data_error(self, MockMPRester):
        ctx, mpr = _mock_mprester()
        MockMPRester.return_value = ctx
        mpr.materials.elasticity.search.return_value = []

        result = json.loads(asyncio.run(get_elastic_properties("mp-149")))
        self.assertIn("error", result)


# =============================================================================
# Tool Callable Tests
# =============================================================================


class TestToolFunctions(unittest.TestCase):
    def test_search_materials_is_callable(self):
        from mcp_materials.mp_tools import search_materials
        assert callable(search_materials)

    def test_get_structure_is_callable(self):
        from mcp_materials.mp_tools import get_structure
        assert callable(get_structure)

    def test_get_properties_is_callable(self):
        from mcp_materials.mp_tools import get_properties
        assert callable(get_properties)

    def test_compare_materials_is_callable(self):
        from mcp_materials.mp_tools import compare_materials
        assert callable(compare_materials)

    def test_search_by_elements_is_callable(self):
        from mcp_materials.mp_tools import search_by_elements
        assert callable(search_by_elements)

    def test_search_by_band_gap_is_callable(self):
        from mcp_materials.mp_tools import search_by_band_gap
        assert callable(search_by_band_gap)

    def test_get_similar_structures_is_callable(self):
        from mcp_materials.mp_tools import get_similar_structures
        assert callable(get_similar_structures)

    def test_get_phase_diagram_is_callable(self):
        from mcp_materials.mp_tools import get_phase_diagram
        assert callable(get_phase_diagram)

    def test_get_elastic_properties_is_callable(self):
        from mcp_materials.mp_tools import get_elastic_properties
        assert callable(get_elastic_properties)

    def test_search_by_elastic_properties_is_callable(self):
        from mcp_materials.mp_tools import search_by_elastic_properties
        assert callable(search_by_elastic_properties)


# =============================================================================
# Missing API Key / Dependency Tests
# =============================================================================


class TestToolsWithoutAPIKey(unittest.TestCase):
    def test_search_materials_returns_error_without_key(self):
        with patch.dict(os.environ, {}, clear=True):
            os.environ.pop("MP_API_KEY", None)
            os.environ.pop("PMG_MAPI_KEY", None)
            result = json.loads(asyncio.run(search_materials("Si")))
            assert "error" in result
            assert "MP_API_KEY" in result["error"]

    def test_get_properties_returns_error_without_key(self):
        with patch.dict(os.environ, {}, clear=True):
            os.environ.pop("MP_API_KEY", None)
            os.environ.pop("PMG_MAPI_KEY", None)
            result = json.loads(asyncio.run(get_properties("mp-149")))
            assert "error" in result

    def test_get_elastic_properties_returns_error_without_key(self):
        with patch.dict(os.environ, {}, clear=True):
            os.environ.pop("MP_API_KEY", None)
            os.environ.pop("PMG_MAPI_KEY", None)
            result = json.loads(asyncio.run(get_elastic_properties("mp-149")))
            assert "error" in result

    def test_get_phase_diagram_returns_error_without_key(self):
        from mcp_materials.mp_tools import get_phase_diagram

        with patch.dict(os.environ, {}, clear=True):
            os.environ.pop("MP_API_KEY", None)
            os.environ.pop("PMG_MAPI_KEY", None)
            result = json.loads(asyncio.run(get_phase_diagram(["Li", "O"])))
            assert "error" in result


class TestInputValidation(unittest.TestCase):
    """Regression for W2: tools must reject invalid inputs."""

    def test_invalid_material_id_returns_error(self):
        result = json.loads(asyncio.run(get_properties("not-a-valid-id")))
        self.assertIn("error", result)

    def test_negative_max_results(self):
        result = json.loads(asyncio.run(search_materials("Si", max_results=-1)))
        self.assertIn("error", result)

    def test_excessive_max_results(self):
        result = json.loads(asyncio.run(search_materials("Si", max_results=999)))
        self.assertIn("error", result)

    def test_invalid_formula_returns_error(self):
        result = json.loads(asyncio.run(search_materials("")))
        self.assertIn("error", result)

    def test_invalid_formula_lowercase_start(self):
        result = json.loads(asyncio.run(search_materials("si")))
        self.assertIn("error", result)

    def test_invalid_elements_returns_error(self):
        result = json.loads(asyncio.run(search_by_elements([])))
        self.assertIn("error", result)

    def test_invalid_element_symbol(self):
        result = json.loads(asyncio.run(search_by_elements(["Li", "notanelement"])))
        self.assertIn("error", result)


class TestHasMPAPIFlag(unittest.TestCase):
    """Regression for C4: clear error when mp-api is not installed."""

    @patch("mcp_materials._prereqs.HAS_MP_API", False)
    def test_error_when_mp_api_unavailable(self):
        result = json.loads(asyncio.run(search_materials("Si")))
        self.assertIn("error", result)
        self.assertIn("not installed", result["error"])


# =============================================================================
# Timeout Tests
# =============================================================================


class TestAPITimeout(unittest.TestCase):
    """asyncio.to_thread calls must be wrapped with wait_for timeout."""

    @patch("mcp_materials.mp_tools.MPRester")
    def test_search_materials_timeout(self, MockMPRester):
        """Timeout on search_materials returns a user-friendly error."""
        ctx, mpr = _mock_mprester()
        MockMPRester.return_value = ctx

        async def _hang(*a, **kw):
            await asyncio.sleep(9999)

        with patch("mcp_materials.mp_tools.asyncio.to_thread", side_effect=_hang), \
             patch("mcp_materials.mp_tools.API_TIMEOUT", 0.01):
            result = json.loads(asyncio.run(search_materials("Si")))
            self.assertIn("error", result)
            self.assertIn("timed out", result["error"].lower())

    @patch("mcp_materials.mp_tools.MPRester")
    def test_get_structure_timeout(self, MockMPRester):
        """Timeout on get_structure returns a user-friendly error."""
        ctx, mpr = _mock_mprester()
        MockMPRester.return_value = ctx

        async def _hang(*a, **kw):
            await asyncio.sleep(9999)

        with patch("mcp_materials.mp_tools.asyncio.to_thread", side_effect=_hang), \
             patch("mcp_materials.mp_tools.API_TIMEOUT", 0.01):
            result = json.loads(asyncio.run(get_structure("mp-149")))
            self.assertIn("error", result)
            self.assertIn("timed out", result["error"].lower())

    @patch("mcp_materials.mp_tools.MPRester")
    def test_get_properties_timeout(self, MockMPRester):
        """Timeout on get_properties returns a user-friendly error."""
        ctx, mpr = _mock_mprester()
        MockMPRester.return_value = ctx

        async def _hang(*a, **kw):
            await asyncio.sleep(9999)

        with patch("mcp_materials.mp_tools.asyncio.to_thread", side_effect=_hang), \
             patch("mcp_materials.mp_tools.API_TIMEOUT", 0.01):
            result = json.loads(asyncio.run(get_properties("mp-149")))
            self.assertIn("error", result)
            self.assertIn("timed out", result["error"].lower())

    def test_api_timeout_constant_exists(self):
        """API_TIMEOUT module-level constant must exist and be positive."""
        from mcp_materials.mp_tools import API_TIMEOUT

        self.assertIsInstance(API_TIMEOUT, (int, float))
        self.assertGreater(API_TIMEOUT, 0)


if __name__ == "__main__":
    unittest.main()
