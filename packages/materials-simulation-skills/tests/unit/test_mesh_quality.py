import unittest

from tests.unit._utils import load_module


class TestMeshQuality(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.mod = load_module(
            "mesh_quality",
            "skills/core-numerical/mesh-generation/scripts/mesh_quality.py",
        )

    def test_quality_metrics(self):
        result = self.mod.compute_quality(1.0, 1.0, 2.0)
        self.assertAlmostEqual(result["aspect_ratio"], 2.0, places=6)
        self.assertTrue(result["skewness"] > 0)

    def test_invalid_inputs(self):
        with self.assertRaises(ValueError):
            self.mod.compute_quality(0.0, 1.0, 1.0)

    def test_skewness_axis_aligned_hex_cube(self):
        """Test REQ-B01: Skewness of axis-aligned hex cell (cube) should be 0."""
        result = self.mod.compute_quality(1.0, 1.0, 1.0)
        self.assertAlmostEqual(result["skewness"], 0.0, places=6)
        self.assertAlmostEqual(result["aspect_ratio"], 1.0, places=6)

    def test_skewness_known_skewed_cell(self):
        """Test REQ-B01: Mean-deviation skewness for extreme aspect ratio.

        For (10, 1, 1): mean = 4, skewness = 1 - 1/4 = 0.75.
        """
        result = self.mod.compute_quality(10.0, 1.0, 1.0)
        self.assertAlmostEqual(result["skewness"], 0.75, places=6)
        self.assertAlmostEqual(result["aspect_ratio"], 10.0, places=6)

    def test_skewness_moderate_stretch(self):
        """Test REQ-B01: Mean-deviation skewness for moderate stretch.

        For (2, 1, 1): mean = 4/3, skewness = 1 - 1/(4/3) = 0.25.
        """
        result = self.mod.compute_quality(2.0, 1.0, 1.0)
        self.assertAlmostEqual(result["skewness"], 0.25, places=6)
        self.assertAlmostEqual(result["aspect_ratio"], 2.0, places=6)

    def test_skewness_differs_from_anisotropy(self):
        """Skewness and anisotropy_index must be distinct metrics."""
        result = self.mod.compute_quality(10.0, 1.0, 1.0)
        self.assertNotAlmostEqual(
            result["skewness"], result["anisotropy_index"], places=6,
            msg="skewness and anisotropy_index should use different formulas",
        )

    def test_skewness_symmetric_stretch(self):
        """Two dimensions stretched equally: skewness reflects mean deviation."""
        # (1, 5, 5): mean = 11/3, min = 1, skewness = 1 - 3/11
        result = self.mod.compute_quality(1.0, 5.0, 5.0)
        expected = 1.0 - (1.0 / (11.0 / 3.0))
        self.assertAlmostEqual(result["skewness"], expected, places=6)
        # anisotropy: 1 - 1/5 = 0.8, which is different
        self.assertAlmostEqual(result["anisotropy_index"], 0.8, places=6)


if __name__ == "__main__":
    unittest.main()
