import unittest

from tests.unit._utils import load_module


class TestOptimizerSelector(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.mod = load_module(
            "optimizer_selector",
            "skills/simulation-workflow/parameter-optimization/scripts/optimizer_selector.py",
        )

    def test_low_dim_low_budget_bayesian(self):
        """Test low dimension + low budget recommends Bayesian."""
        result = self.mod.select_optimizer(3, 40, "low", False)
        self.assertIn("Bayesian", result["recommended"][0])

    def test_low_dim_high_budget_bayesian(self):
        """Test low dimension + high budget still works."""
        result = self.mod.select_optimizer(4, 80, "low", False)
        self.assertIn("Bayesian", result["recommended"][0])

    def test_medium_dim_cmaes(self):
        """Test medium dimension recommends CMA-ES."""
        result = self.mod.select_optimizer(10, 200, "low", False)
        self.assertIn("CMA-ES", result["recommended"][0])

    def test_high_dim_random(self):
        """Test high dimension recommends Random Search."""
        result = self.mod.select_optimizer(30, 200, "medium", False)
        self.assertIn("Random", result["recommended"][0])

    def test_bo_threshold_is_10(self):
        """Test REQ-B13: BO dimension threshold is 10.

        Per Frazier (2018) and standard BO literature, Bayesian Optimization
        is recommended for dimensions up to 10-20. The threshold should be 10,
        not 5 as originally implemented.
        """
        # Dimension 10 should still recommend BO
        result = self.mod.select_optimizer(10, 100, "low", False)
        self.assertIn("Bayesian", result["recommended"][0])

    def test_boundary_dim_10(self):
        """Test boundary at dim=10 (upper limit for BO per Frazier 2018)."""
        result = self.mod.select_optimizer(10, 100, "low", False)
        self.assertIn("Bayesian", result["recommended"][0])

    def test_boundary_dim_11(self):
        """Test boundary at dim=11 (should be CMA-ES)."""
        result = self.mod.select_optimizer(11, 100, "low", False)
        self.assertIn("CMA-ES", result["recommended"][0])

    def test_boundary_dim_20(self):
        """Test boundary at dim=20."""
        result = self.mod.select_optimizer(20, 300, "low", False)
        self.assertIn("CMA-ES", result["recommended"][0])

    def test_boundary_dim_21(self):
        """Test boundary at dim=21 (should be Random)."""
        result = self.mod.select_optimizer(21, 300, "low", False)
        self.assertIn("Random", result["recommended"][0])

    def test_high_noise_note(self):
        """Test high noise adds appropriate note."""
        result = self.mod.select_optimizer(3, 40, "high", False)
        self.assertTrue(any("noise" in note.lower() for note in result["notes"]))

    def test_medium_noise_no_note(self):
        """Test medium noise doesn't add noise note."""
        result = self.mod.select_optimizer(3, 40, "medium", False)
        noise_notes = [n for n in result["notes"] if "noise" in n.lower()]
        self.assertEqual(len(noise_notes), 0)

    def test_constraints_note(self):
        """Test constraints adds appropriate note."""
        result = self.mod.select_optimizer(3, 40, "low", True)
        self.assertTrue(any("constrain" in note.lower() for note in result["notes"]))

    def test_no_constraints_no_note(self):
        """Test no constraints doesn't add constraint note."""
        result = self.mod.select_optimizer(3, 40, "low", False)
        constraint_notes = [n for n in result["notes"] if "constrain" in n.lower()]
        self.assertEqual(len(constraint_notes), 0)

    def test_expected_evals_small_budget(self):
        """Test expected_evals respects budget."""
        result = self.mod.select_optimizer(3, 10, "low", False)
        self.assertLessEqual(result["expected_evals"], 10)

    def test_expected_evals_large_budget(self):
        """Test expected_evals has reasonable upper bound."""
        result = self.mod.select_optimizer(5, 1000, "low", False)
        self.assertLessEqual(result["expected_evals"], 1000)

    def test_invalid_dim_zero(self):
        """Test zero dimension raises ValueError."""
        with self.assertRaises(ValueError) as ctx:
            self.mod.select_optimizer(0, 40, "low", False)
        self.assertIn("dim must be positive", str(ctx.exception))

    def test_invalid_dim_negative(self):
        """Test negative dimension raises ValueError."""
        with self.assertRaises(ValueError):
            self.mod.select_optimizer(-1, 40, "low", False)

    def test_invalid_budget_zero(self):
        """Test zero budget raises ValueError."""
        with self.assertRaises(ValueError) as ctx:
            self.mod.select_optimizer(3, 0, "low", False)
        self.assertIn("budget must be positive", str(ctx.exception))

    def test_invalid_noise(self):
        """Test invalid noise level raises ValueError."""
        with self.assertRaises(ValueError) as ctx:
            self.mod.select_optimizer(3, 40, "very_high", False)
        self.assertIn("noise must be", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()
