import unittest

from tests.unit._utils import load_module


class TestSurrogateBuilder(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.mod = load_module(
            "surrogate_builder",
            "skills/simulation-workflow/parameter-optimization/scripts/surrogate_builder.py",
        )

    def test_surrogate_rbf(self):
        """Test surrogate with rbf model."""
        result = self.mod.build_surrogate([0.0, 1.0], [1.0, 2.0], "rbf")
        self.assertIn("metrics", result)
        self.assertEqual(result["model_type"], "rbf")

    def test_surrogate_poly(self):
        """Test surrogate with poly model."""
        result = self.mod.build_surrogate([0.0, 1.0, 2.0], [1.0, 4.0, 9.0], "poly")
        self.assertIn("metrics", result)
        self.assertEqual(result["model_type"], "poly")

    def test_population_variance_calculation(self):
        """Test population_variance is computed correctly."""
        # y = [1, 2, 3], mean = 2, variance = (1+0+1)/3 = 0.666...
        result = self.mod.build_surrogate([0.0, 1.0, 2.0], [1.0, 2.0, 3.0], "rbf")
        expected_var = (1.0 + 0.0 + 1.0) / 3
        self.assertAlmostEqual(result["metrics"]["population_variance"], expected_var, places=6)

    def test_population_variance_zero(self):
        """Test population_variance is zero for constant output."""
        result = self.mod.build_surrogate([0.0, 1.0, 2.0], [5.0, 5.0, 5.0], "rbf")
        self.assertAlmostEqual(result["metrics"]["population_variance"], 0.0, places=6)

    def test_placeholder_note(self):
        """Test production note is present."""
        result = self.mod.build_surrogate([0.0, 1.0], [1.0, 2.0], "rbf")
        self.assertTrue(any("gaussian process" in note.lower() for note in result["notes"]))

    def test_invalid_lengths(self):
        """Test mismatched x and y lengths raises ValueError."""
        with self.assertRaises(ValueError) as ctx:
            self.mod.build_surrogate([0.0], [1.0, 2.0], "rbf")
        self.assertIn("same length", str(ctx.exception))

    def test_invalid_model(self):
        """Test invalid model type raises ValueError."""
        with self.assertRaises(ValueError) as ctx:
            self.mod.build_surrogate([0.0, 1.0], [1.0, 2.0], "gp")
        self.assertIn("model must be", str(ctx.exception))

    def test_too_few_samples(self):
        """Test fewer than 2 samples raises ValueError."""
        with self.assertRaises(ValueError) as ctx:
            self.mod.build_surrogate([0.0], [1.0], "rbf")
        self.assertIn("at least 2", str(ctx.exception))

    def test_empty_lists(self):
        """Test empty lists raise ValueError."""
        with self.assertRaises(ValueError):
            self.mod.build_surrogate([], [], "rbf")

    def test_many_samples(self):
        """Test surrogate works with many samples."""
        x = list(range(100))
        y = [i * 2 for i in x]
        result = self.mod.build_surrogate(x, y, "poly")
        self.assertIn("metrics", result)
        self.assertGreater(result["metrics"]["population_variance"], 0)

    def test_parse_list_valid(self):
        """Test parse_list with valid input."""
        result = self.mod.parse_list("1.0, 2.0, 3.0")
        self.assertEqual(result, [1.0, 2.0, 3.0])

    def test_parse_list_integers(self):
        """Test parse_list with integer input."""
        result = self.mod.parse_list("1, 2, 3")
        self.assertEqual(result, [1.0, 2.0, 3.0])

    def test_parse_list_empty(self):
        """Test parse_list with empty string raises ValueError."""
        with self.assertRaises(ValueError) as ctx:
            self.mod.parse_list("")
        self.assertIn("comma-separated", str(ctx.exception))

    def test_metrics_contain_mse_and_population_variance(self):
        """Test that metrics dict contains both mse and population_variance.

        The surrogate builder fits a model and computes predictions, so mse
        (mean squared error of the fit) is a legitimate metric alongside the
        population_variance of the raw output data.
        """
        x = [0.0, 1.0, 2.0, 3.0, 4.0]
        y = [0.0, 1.0, 4.0, 9.0, 16.0]
        result = self.mod.build_surrogate(x, y, "poly")

        self.assertIn("metrics", result)
        metrics = result["metrics"]

        # Both mse and population_variance should be present
        self.assertIn("population_variance", metrics)
        self.assertIn("mse", metrics)

        # mse should be a non-negative float
        self.assertIsInstance(metrics["mse"], float)
        self.assertGreaterEqual(metrics["mse"], 0.0)


if __name__ == "__main__":
    unittest.main()
