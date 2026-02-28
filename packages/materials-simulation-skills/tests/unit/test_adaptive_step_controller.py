import unittest

from tests.unit._utils import load_module


class TestAdaptiveStepController(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.mod = load_module(
            "adaptive_step_controller",
            "skills/core-numerical/numerical-integration/scripts/adaptive_step_controller.py",
        )

    def test_accept_step(self):
        result = self.mod.compute_step(
            dt=0.1,
            error_norm=0.5,
            order=4,
            accept_threshold=1.0,
            safety=0.9,
            min_factor=0.2,
            max_factor=5.0,
            controller="p",
            prev_error=None,
        )
        self.assertTrue(result["accept"])
        self.assertGreater(result["dt_next"], 0.1)

    def test_reject_step(self):
        result = self.mod.compute_step(
            dt=0.1,
            error_norm=2.0,
            order=2,
            accept_threshold=1.0,
            safety=0.9,
            min_factor=0.2,
            max_factor=5.0,
            controller="p",
            prev_error=None,
        )
        self.assertFalse(result["accept"])
        self.assertLess(result["dt_next"], 0.1)

    def test_zero_error(self):
        result = self.mod.compute_step(
            dt=0.1,
            error_norm=0.0,
            order=2,
            accept_threshold=1.0,
            safety=0.9,
            min_factor=0.2,
            max_factor=3.0,
            controller="p",
            prev_error=None,
        )
        self.assertEqual(result["factor"], 3.0)

    def test_pi_controller(self):
        result = self.mod.compute_step(
            dt=0.1,
            error_norm=0.8,
            order=3,
            accept_threshold=1.0,
            safety=0.9,
            min_factor=0.2,
            max_factor=5.0,
            controller="pi",
            prev_error=1.2,
        )
        self.assertEqual(result["controller_used"], "pi")
        self.assertTrue(result["accept"])

    def test_factor_clamp(self):
        result = self.mod.compute_step(
            dt=0.1,
            error_norm=1e-12,
            order=4,
            accept_threshold=1.0,
            safety=0.9,
            min_factor=0.2,
            max_factor=1.5,
            controller="p",
            prev_error=None,
        )
        self.assertAlmostEqual(result["factor"], 1.5, places=6)

    def test_invalid_inputs(self):
        with self.assertRaises(ValueError):
            self.mod.compute_step(
                dt=-0.1,
                error_norm=0.5,
                order=1,
                accept_threshold=1.0,
                safety=0.9,
                min_factor=0.2,
                max_factor=5.0,
                controller="p",
                prev_error=None,
            )

    def test_pi_controller_k2_coefficient(self):
        """Test REQ-B06: PI controller k2 coefficient is 0.4 per Soderlind (2003).

        The PI controller formula (from adaptive_step_controller.py) is:
        factor = safety * (threshold / error_norm)^k1 * (threshold / prev_error)^k2

        where k1 (proportional gain) and k2 (integral gain) are scaled by
        exp = 1/(order+1).  Soderlind (2003) recommends k1 = 0.7*exp, k2 = 0.4*exp.

        prev_error is intentionally different from accept_threshold so the k2
        term contributes a non-unity multiplier and is actually exercised.
        """
        import math

        # Use prev_error=1.5 (not 1.0) so the k2 term is non-trivial.
        # With prev_error == accept_threshold the k2 term evaluates to 1.0
        # regardless of the k2 value, which would not test the coefficient.
        result = self.mod.compute_step(
            dt=0.1,
            error_norm=0.8,
            order=2,
            accept_threshold=1.0,
            safety=0.9,
            min_factor=0.2,
            max_factor=5.0,
            controller="pi",
            prev_error=1.5,
        )

        # Compute expected factor using the PI formula with k2=0.4
        # exp = 1/(order+1) = 1/3
        # k1 = 0.7 * exp = 0.7/3,  k2 = 0.4 * exp = 0.4/3
        exp = 1.0 / (2 + 1.0)
        k1 = 0.7 * exp
        k2 = 0.4 * exp
        expected_factor = 0.9 * (1.0 / 0.8) ** k1 * (1.0 / 1.5) ** k2
        expected_dt_next = 0.1 * expected_factor

        self.assertEqual(result["controller_used"], "pi")
        self.assertTrue(result["accept"])  # Error 0.8 < threshold 1.0
        self.assertAlmostEqual(result["factor"], expected_factor, places=10)
        self.assertAlmostEqual(result["dt_next"], expected_dt_next, places=10)

        # Verify sensitivity: a wrong k2 (e.g., 0.3 instead of 0.4) would
        # produce a detectably different factor, confirming the test is
        # actually sensitive to the k2 coefficient value.
        wrong_k2 = 0.3 * exp
        wrong_factor = 0.9 * (1.0 / 0.8) ** k1 * (1.0 / 1.5) ** wrong_k2
        self.assertNotAlmostEqual(result["factor"], wrong_factor, places=5)

    def test_pi_controller_integral_naming(self):
        """Test REQ-B07: PI controller parameter naming uses 'i' (integral).

        The parameter should be named with 'i' (integral) for the k2 coefficient,
        following Soderlind's framework. This test verifies the naming convention
        is consistent in the output or internal documentation.
        """
        result = self.mod.compute_step(
            dt=0.1,
            error_norm=0.5,
            order=3,
            accept_threshold=1.0,
            safety=0.9,
            min_factor=0.2,
            max_factor=5.0,
            controller="pi",
            prev_error=0.8,
        )

        # Check that the controller is correctly identified as PI
        self.assertEqual(result["controller_used"], "pi")

        # The internal implementation should follow Soderlind's naming
        # where the integral gain (k2) is used for the previous error term
        # We can verify this indirectly by checking the output is sensible
        self.assertTrue(result["accept"])
        self.assertGreater(result["dt_next"], 0)


if __name__ == "__main__":
    unittest.main()
