import unittest

from tests.unit._utils import load_module


class TestSplittingErrorEstimator(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.mod = load_module(
            "splitting_error_estimator",
            "skills/core-numerical/numerical-integration/scripts/splitting_error_estimator.py",
        )

    def test_strang_error(self):
        result = self.mod.estimate_error(dt=1e-3, scheme="strang", commutator_norm=100.0, target_error=0.0)
        self.assertGreater(result["error_estimate"], 0.0)
        self.assertEqual(result["order"], 2)

    def test_target_error(self):
        result = self.mod.estimate_error(dt=1e-2, scheme="lie", commutator_norm=10.0, target_error=1e-6)
        self.assertGreaterEqual(result["substeps"], 1)
        self.assertLessEqual(result["error_estimate"], 1e-6)

    def test_invalid_dt(self):
        with self.assertRaises(ValueError):
            self.mod.estimate_error(dt=0.0, scheme="lie", commutator_norm=1.0, target_error=0.0)

    def test_substep_exponent_is_one_over_order(self):
        """Test REQ-B05: Substep calculation exponent is 1/order.

        The error for splitting schemes scales as dt^(order+1) for a single step.
        Over the full interval, with N substeps of size dt/N, the accumulated error
        is N * (dt/N)^(order+1) = dt^(order+1) / N^order.

        To achieve a target error E, we need: dt^(order+1) / N^order <= E
        Solving for N: N >= (dt^(order+1) / E)^(1/order)

        The exponent should be 1/order, NOT 1/(order+1).
        """
        # Test with Lie-Trotter (order 1)
        dt = 0.1
        commutator_norm = 1.0
        target_error = 1e-4

        result_lie = self.mod.estimate_error(
            dt=dt, scheme="lie", commutator_norm=commutator_norm, target_error=target_error
        )

        # For Lie-Trotter, order=1, so substeps ~ (dt^2 / target)^(1/1) = dt^2 / target
        # With dt=0.1, commutator=1.0: error ~ 0.5 * dt^2 * C = 0.5 * 0.01 * 1.0 = 0.005
        # To reach 1e-4: need 0.005 / N <= 1e-4, so N >= 50
        self.assertGreaterEqual(result_lie["substeps"], 40)  # Allow some margin

        # Test with Strang (order 2)
        result_strang = self.mod.estimate_error(
            dt=dt, scheme="strang", commutator_norm=commutator_norm, target_error=target_error
        )

        # For Strang, order=2, so substeps ~ (dt^3 / target)^(1/2)
        # With dt=0.1: error ~ dt^3 * C = 0.001 * 1.0 = 0.001
        # To reach 1e-4: need 0.001 / N^2 <= 1e-4, so N^2 >= 10, N >= 3.16
        self.assertGreaterEqual(result_strang["substeps"], 3)

        # Verify that higher order schemes require fewer substeps for same accuracy
        self.assertLess(result_strang["substeps"], result_lie["substeps"])


if __name__ == "__main__":
    unittest.main()
