import unittest

from tests.unit._utils import load_module


class TestNonlinearConvergenceAnalyzer(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.mod = load_module(
            "convergence_analyzer",
            "skills/core-numerical/nonlinear-solvers/scripts/convergence_analyzer.py",
        )

    def test_converged_quadratic(self):
        """Test detection of quadratic convergence."""
        # Simulate quadratic convergence: residual squares each iteration
        residuals = [1.0, 0.1, 0.01, 0.0001, 1e-8, 1e-16]
        result = self.mod.analyze_convergence(residuals, tolerance=1e-10)
        self.assertTrue(result["converged"])
        self.assertEqual(result["iterations"], 6)

    def test_linear_convergence(self):
        """Test detection of linear convergence."""
        # Linear convergence with rate ~0.5
        residuals = [1.0, 0.5, 0.25, 0.125, 0.0625, 0.03125]
        result = self.mod.analyze_convergence(residuals, tolerance=1e-10)
        self.assertFalse(result["converged"])
        self.assertEqual(result["convergence_type"], "linear")
        self.assertIsNotNone(result["estimated_rate"])
        self.assertAlmostEqual(result["estimated_rate"], 0.5, places=2)

    def test_stagnation_detection(self):
        """Test detection of stagnation."""
        # Last 3 residuals must have < 1% relative change to trigger stagnation
        residuals = [1.0, 0.5, 0.3, 0.1, 0.1, 0.1]
        result = self.mod.analyze_convergence(residuals, tolerance=1e-10)
        self.assertEqual(result["convergence_type"], "stagnated")
        self.assertFalse(result["converged"])

    def test_divergence_detection(self):
        """Test detection of divergence."""
        residuals = [1.0, 2.0, 5.0, 15.0]
        result = self.mod.analyze_convergence(residuals, tolerance=1e-10)
        self.assertEqual(result["convergence_type"], "diverged")
        self.assertFalse(result["converged"])
        self.assertIn("diverging", result["diagnosis"].lower())

    def test_single_residual(self):
        """Test handling of single residual."""
        residuals = [0.001]
        result = self.mod.analyze_convergence(residuals, tolerance=1e-10)
        self.assertEqual(result["convergence_type"], "unknown")
        self.assertEqual(result["iterations"], 1)

    def test_converged_at_tolerance(self):
        """Test that convergence is detected when tolerance is met."""
        residuals = [1.0, 0.1, 0.01, 1e-11]
        result = self.mod.analyze_convergence(residuals, tolerance=1e-10)
        self.assertTrue(result["converged"])
        self.assertEqual(result["final_residual"], 1e-11)

    def test_sublinear_detection(self):
        """Test detection of sublinear convergence."""
        # Very slow convergence: rate > 0.9
        residuals = [1.0, 0.95, 0.91, 0.87, 0.84, 0.81, 0.78, 0.76]
        result = self.mod.analyze_convergence(residuals, tolerance=1e-10)
        self.assertEqual(result["convergence_type"], "sublinear")

    def test_empty_residuals_raises(self):
        """Test that empty residuals raises ValueError."""
        with self.assertRaises(ValueError):
            self.mod.analyze_convergence([], tolerance=1e-10)

    def test_negative_residual_raises(self):
        """Test that negative residual raises ValueError."""
        with self.assertRaises(ValueError):
            self.mod.analyze_convergence([1.0, -0.5, 0.1], tolerance=1e-10)

    def test_invalid_tolerance_raises(self):
        """Test that non-positive tolerance raises ValueError."""
        with self.assertRaises(ValueError):
            self.mod.analyze_convergence([1.0, 0.5], tolerance=0)
        with self.assertRaises(ValueError):
            self.mod.analyze_convergence([1.0, 0.5], tolerance=-1e-10)

    def test_convergence_detection_residuals_below_one(self):
        """Test REQ-B03: Convergence order detection with residuals < 1."""
        # Quadratic convergence with residuals < 1
        # r_k = 0.1 * r_{k-1}^2, starting from r_0 = 0.1
        residuals = [0.1, 0.001, 1e-6, 1e-12, 1e-24]
        result = self.mod.analyze_convergence(residuals, tolerance=1e-15)
        self.assertTrue(result["converged"])
        # Should detect quadratic convergence
        self.assertIn(result["convergence_type"], ["quadratic", "superlinear"])

    def test_convergence_detection_residuals_above_one(self):
        """Test REQ-B03: Convergence order detection with residuals > 1."""
        # Quadratic convergence with residuals > 1 initially
        # If r_k = r_{k-1}^2 / C (with appropriate scaling), we can have quadratic
        # convergence even when starting from r > 1
        residuals = [10.0, 1.0, 0.01, 1e-6, 1e-14]
        result = self.mod.analyze_convergence(residuals, tolerance=1e-10)
        self.assertTrue(result["converged"])
        # The ratio-of-logs approach should correctly detect the convergence pattern

    def test_convergence_detection_residuals_crossing_one(self):
        """Test REQ-B03: Convergence order detection when residuals cross 1.

        This tests that the formula handles the case where log(r_k) changes sign.
        The ratio-of-logs approach: log(r_{k+1}/r_k) / log(r_k/r_{k-1})
        should work correctly even when residuals cross 1.
        """
        # Residuals that cross 1: starts above, crosses through 1, continues below
        residuals = [5.0, 2.5, 1.0, 0.2, 0.01, 1e-4, 1e-8]
        result = self.mod.analyze_convergence(residuals, tolerance=1e-6)
        self.assertTrue(result["converged"])
        # Should successfully analyze without errors due to log sign changes


if __name__ == "__main__":
    unittest.main()
