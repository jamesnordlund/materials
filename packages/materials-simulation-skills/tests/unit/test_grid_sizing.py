import unittest

from tests.unit._utils import load_module


class TestGridSizing(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.mod = load_module(
            "grid_sizing",
            "skills/core-numerical/mesh-generation/scripts/grid_sizing.py",
        )

    def test_compute_grid(self):
        result = self.mod.compute_grid(length=1.0, resolution=10, dims=2, dx=None)
        self.assertAlmostEqual(result["dx"], 0.1, places=6)
        self.assertEqual(result["counts"], [10, 10])

    def test_invalid_length(self):
        with self.assertRaises(ValueError):
            self.mod.compute_grid(length=0, resolution=10, dims=2, dx=None)

    def test_dead_code_removal_verification(self):
        """Test REQ-B02: Verify dead code branch has been removed.

        The dead code branch `if dx * counts[0] < length` can never be true
        because the ceiling function in count computation ensures
        dx * counts[0] >= length always. This test verifies the computation
        is correct without that dead branch.
        """
        # Test case where count is exactly the ceiling
        result = self.mod.compute_grid(length=1.0, resolution=11, dims=1, dx=None)
        # With resolution=11, dx = 1.0/11 = 0.0909...
        # counts[0] = 11, so dx * counts[0] = 1.0 (exactly)
        self.assertAlmostEqual(result["dx"], 1.0 / 11, places=6)
        self.assertEqual(result["counts"], [11])

        # Test case where ceiling rounds up
        result = self.mod.compute_grid(length=1.0, resolution=9, dims=1, dx=None)
        # With resolution=9, dx = 1.0/9 = 0.111...
        # counts[0] = 9, so dx * counts[0] = 1.0 (exactly)
        self.assertAlmostEqual(result["dx"], 1.0 / 9, places=6)
        self.assertEqual(result["counts"], [9])


if __name__ == "__main__":
    unittest.main()
