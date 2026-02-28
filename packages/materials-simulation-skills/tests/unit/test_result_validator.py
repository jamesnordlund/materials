import unittest

from tests.unit._utils import load_module


class TestResultValidator(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.mod = load_module(
            "result_validator",
            "skills/simulation-workflow/simulation-validator/scripts/result_validator.py",
        )

    def test_mass_conserved(self):
        """Test mass conservation check passes."""
        metrics = {"mass_initial": 1.0, "mass_final": 1.0005}
        result = self.mod.validate_metrics(metrics, None, None, 1e-3)
        self.assertTrue(result["checks"]["mass_conserved"])

    def test_mass_not_conserved(self):
        """Test mass conservation check fails."""
        metrics = {"mass_initial": 1.0, "mass_final": 1.1}
        result = self.mod.validate_metrics(metrics, None, None, 1e-3)
        self.assertFalse(result["checks"]["mass_conserved"])
        self.assertIn("mass_conserved", result["failed_checks"])

    def test_energy_decreases(self):
        """Test energy decrease check passes."""
        metrics = {"energy_history": [10.0, 9.0, 8.0]}
        result = self.mod.validate_metrics(metrics, None, None, 1e-3)
        self.assertTrue(result["checks"]["energy_decreases"])

    def test_energy_increases(self):
        """Test energy increase check fails."""
        metrics = {"energy_history": [10.0, 11.0, 12.0]}
        result = self.mod.validate_metrics(metrics, None, None, 1e-3)
        self.assertFalse(result["checks"]["energy_decreases"])

    def test_bounds_satisfied(self):
        """Test bounds check passes."""
        metrics = {"field_min": 0.0, "field_max": 1.0}
        result = self.mod.validate_metrics(metrics, 0.0, 1.0, 1e-3)
        self.assertTrue(result["checks"]["bounds_satisfied"])

    def test_bounds_violated_min(self):
        """Test bounds check fails on min violation."""
        metrics = {"field_min": -0.1, "field_max": 1.0}
        result = self.mod.validate_metrics(metrics, 0.0, 1.0, 1e-3)
        self.assertFalse(result["checks"]["bounds_satisfied"])

    def test_bounds_violated_max(self):
        """Test bounds check fails on max violation."""
        metrics = {"field_min": 0.0, "field_max": 1.2}
        result = self.mod.validate_metrics(metrics, 0.0, 1.0, 1e-3)
        self.assertFalse(result["checks"]["bounds_satisfied"])

    def test_nan_detected(self):
        """Test NaN detection fails."""
        metrics = {"has_nan": True}
        result = self.mod.validate_metrics(metrics, None, None, 1e-3)
        self.assertFalse(result["checks"]["no_nan"])
        self.assertIn("no_nan", result["failed_checks"])

    def test_no_nan(self):
        """Test no NaN passes."""
        metrics = {"has_nan": False}
        result = self.mod.validate_metrics(metrics, None, None, 1e-3)
        self.assertTrue(result["checks"]["no_nan"])

    def test_confidence_score_all_pass(self):
        """Test confidence score when all checks pass."""
        metrics = {
            "mass_initial": 1.0,
            "mass_final": 1.0,
            "energy_history": [10.0, 9.0],
            "field_min": 0.0,
            "field_max": 1.0,
            "has_nan": False,
        }
        result = self.mod.validate_metrics(metrics, 0.0, 1.0, 1e-3)
        self.assertEqual(result["confidence_score"], 1.0)

    def test_confidence_score_partial(self):
        """Test confidence score with partial pass."""
        metrics = {
            "mass_initial": 1.0,
            "mass_final": 1.0,
            "energy_history": [10.0, 11.0],  # Fails
            "field_min": 0.0,
            "field_max": 1.0,
            "has_nan": False,
        }
        result = self.mod.validate_metrics(metrics, 0.0, 1.0, 1e-3)
        self.assertGreater(result["confidence_score"], 0.5)
        self.assertLess(result["confidence_score"], 1.0)

    def test_no_checks_available(self):
        """Test empty metrics gives no_checks."""
        metrics = {}
        result = self.mod.validate_metrics(metrics, None, None, 1e-3)
        self.assertTrue(result["checks"].get("no_checks", False))

    def test_mass_tolerance_boundary(self):
        """Test mass at tolerance boundary."""
        metrics = {"mass_initial": 1.0, "mass_final": 1.001}
        result = self.mod.validate_metrics(metrics, None, None, 1e-3)
        self.assertTrue(result["checks"]["mass_conserved"])

    def test_energy_constant(self):
        """Test constant energy passes."""
        metrics = {"energy_history": [10.0, 10.0, 10.0]}
        result = self.mod.validate_metrics(metrics, None, None, 1e-3)
        self.assertTrue(result["checks"]["energy_decreases"])

    def test_only_bound_min(self):
        """Test only bound_min specified."""
        metrics = {"field_min": 0.5, "field_max": 10.0}
        result = self.mod.validate_metrics(metrics, 0.0, None, 1e-3)
        self.assertTrue(result["checks"]["bounds_satisfied"])

    def test_only_bound_max(self):
        """Test only bound_max specified."""
        metrics = {"field_min": -10.0, "field_max": 0.9}
        result = self.mod.validate_metrics(metrics, None, 1.0, 1e-3)
        self.assertTrue(result["checks"]["bounds_satisfied"])

    def test_combined_all_checks(self):
        """Test all checks combined."""
        metrics = {
            "mass_initial": 1.0,
            "mass_final": 1.0005,
            "energy_history": [10.0, 9.0],
            "field_min": 0.0,
            "field_max": 1.0,
            "has_nan": False,
        }
        result = self.mod.validate_metrics(metrics, 0.0, 1.0, 1e-3)
        self.assertTrue(result["checks"]["mass_conserved"])
        self.assertTrue(result["checks"]["energy_decreases"])
        self.assertTrue(result["checks"]["bounds_satisfied"])
        self.assertTrue(result["checks"]["no_nan"])
        self.assertEqual(len(result["failed_checks"]), 0)


    # --- Tests for check_energy_monotonic / check_energy_overall helpers ---

    def test_check_energy_monotonic_pass(self):
        """Monotonic helper returns True for strictly decreasing energies."""
        self.assertTrue(self.mod.check_energy_monotonic([10.0, 9.0, 8.0]))

    def test_check_energy_monotonic_constant(self):
        """Monotonic helper returns True for constant energies."""
        self.assertTrue(self.mod.check_energy_monotonic([5.0, 5.0, 5.0]))

    def test_check_energy_monotonic_fail(self):
        """Monotonic helper returns False when any step increases."""
        self.assertFalse(self.mod.check_energy_monotonic([10.0, 9.0, 9.5]))

    def test_check_energy_overall_pass(self):
        """Overall helper returns True when final <= initial."""
        self.assertTrue(self.mod.check_energy_overall([10.0, 11.0, 9.0]))

    def test_check_energy_overall_fail(self):
        """Overall helper returns False when final > initial."""
        self.assertFalse(self.mod.check_energy_overall([10.0, 9.0, 11.0]))

    # --- Tests for energy_mode parameter in validate_metrics ---

    def test_energy_mode_monotonic_non_monotonic_fails(self):
        """Non-monotonic sequence fails with energy_mode='monotonic'."""
        metrics = {"energy_history": [10.0, 9.0, 9.5, 8.0]}
        result = self.mod.validate_metrics(
            metrics, None, None, 1e-3, energy_mode="monotonic",
        )
        self.assertFalse(result["checks"]["energy_decreases"])
        self.assertIn("energy_decreases", result["failed_checks"])

    def test_energy_mode_overall_non_monotonic_passes(self):
        """Non-monotonic-but-overall-decreasing sequence passes with energy_mode='overall'.

        This is the key scenario: energy dips then rises transiently before
        finishing lower than the start -- acceptable for general simulations
        with local energy exchange, but NOT for gradient-flow / phase-field.
        """
        metrics = {"energy_history": [10.0, 9.0, 9.5, 8.0]}
        result = self.mod.validate_metrics(
            metrics, None, None, 1e-3, energy_mode="overall",
        )
        self.assertTrue(result["checks"]["energy_decreases"])
        self.assertNotIn("energy_decreases", result["failed_checks"])

    def test_energy_mode_overall_net_increase_fails(self):
        """Sequence ending higher than start fails with energy_mode='overall'."""
        metrics = {"energy_history": [10.0, 8.0, 12.0]}
        result = self.mod.validate_metrics(
            metrics, None, None, 1e-3, energy_mode="overall",
        )
        self.assertFalse(result["checks"]["energy_decreases"])
        self.assertIn("energy_decreases", result["failed_checks"])

    def test_energy_mode_bounded(self):
        """Bounded mode passes when all values are finite."""
        metrics = {"energy_history": [10.0, 11.0, 9.0]}
        result = self.mod.validate_metrics(
            metrics, None, None, 1e-3, energy_mode="bounded",
        )
        self.assertTrue(result["checks"]["energy_bounded"])

    def test_energy_mode_bounded_inf_fails(self):
        """Bounded mode fails with Inf in energy history."""
        metrics = {"energy_history": [10.0, float("inf"), 9.0]}
        result = self.mod.validate_metrics(
            metrics, None, None, 1e-3, energy_mode="bounded",
        )
        self.assertFalse(result["checks"]["energy_bounded"])
        self.assertIn("energy_bounded", result["failed_checks"])

    def test_energy_mode_overrides_legacy_flag(self):
        """Explicit energy_mode takes precedence over check_energy_dissipation."""
        # Legacy flag says dissipation (monotonic), but energy_mode says overall
        metrics = {"energy_history": [10.0, 9.0, 9.5, 8.0]}
        result = self.mod.validate_metrics(
            metrics, None, None, 1e-3,
            check_energy_dissipation=True,
            energy_mode="overall",
        )
        # Should pass because energy_mode="overall" overrides the legacy flag
        self.assertTrue(result["checks"]["energy_decreases"])

    def test_legacy_flag_true_defaults_to_monotonic(self):
        """Legacy check_energy_dissipation=True maps to monotonic mode."""
        metrics = {"energy_history": [10.0, 9.0, 9.5, 8.0]}
        result = self.mod.validate_metrics(
            metrics, None, None, 1e-3, check_energy_dissipation=True,
        )
        # Non-monotonic -> should fail under default monotonic mode
        self.assertFalse(result["checks"]["energy_decreases"])

    def test_legacy_flag_false_defaults_to_bounded(self):
        """Legacy check_energy_dissipation=False maps to bounded mode."""
        metrics = {"energy_history": [10.0, 11.0, 9.0]}
        result = self.mod.validate_metrics(
            metrics, None, None, 1e-3, check_energy_dissipation=False,
        )
        self.assertTrue(result["checks"]["energy_bounded"])

    def test_invalid_energy_mode_raises(self):
        """Invalid energy_mode raises ValueError."""
        metrics = {"energy_history": [10.0, 9.0]}
        with self.assertRaises(ValueError):
            self.mod.validate_metrics(
                metrics, None, None, 1e-3, energy_mode="invalid",
            )


if __name__ == "__main__":
    unittest.main()
