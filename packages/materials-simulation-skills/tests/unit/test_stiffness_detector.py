import json
import unittest

import numpy as np

from tests.unit._utils import load_module


class TestStiffnessDetector(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.mod = load_module(
            "stiffness_detector",
            "skills/core-numerical/numerical-stability/scripts/stiffness_detector.py",
        )

    def test_stiff_system(self):
        eigs = np.array([-1.0, -1000.0])
        result = self.mod.compute_stiffness(eigs, threshold=1e3)
        self.assertTrue(result["stiff"])
        self.assertEqual(result["recommendation"], "implicit (BDF/Radau)")

    def test_non_stiff_system(self):
        eigs = np.array([-1.0, -10.0])
        result = self.mod.compute_stiffness(eigs, threshold=1e3)
        self.assertFalse(result["stiff"])
        self.assertEqual(result["recommendation"], "explicit (RK/Adams)")

    def test_invalid_threshold(self):
        eigs = np.array([-1.0, -10.0])
        with self.assertRaises(ValueError):
            self.mod.compute_stiffness(eigs, threshold=0.0)

    def test_complex_eigs(self):
        eigs = np.array([-1.0 + 2.0j, -1000.0 + 0.5j])
        result = self.mod.compute_stiffness(eigs, threshold=1e2)
        self.assertTrue(result["stiff"])

    def test_zero_eigs(self):
        eigs = np.array([0.0, 0.0])
        result = self.mod.compute_stiffness(eigs, threshold=1e3)
        self.assertFalse(result["stiff"])
        self.assertEqual(result["nonzero_count"], 0)

    def test_non_finite_eigs(self):
        eigs = np.array([1.0, float("nan")])
        with self.assertRaises(ValueError):
            self.mod.compute_stiffness(eigs, threshold=1e3)

    def test_pure_imaginary_eigenvalues(self):
        """Test REQ-B08: Stiffness ratio with pure imaginary eigenvalues.

        For systems with significant imaginary eigenvalue components (e.g.,
        oscillatory systems), the stiffness ratio should use real parts, not modulus.

        Stiffness ratio = max(|Re(lambda)|) / min(|Re(lambda)|) for nonzero real parts.

        Pure imaginary eigenvalues (Re(lambda) = 0) indicate undamped oscillation
        and should be handled separately.
        """
        # System with pure imaginary eigenvalues: +/- 10i (oscillatory)
        # Real parts are all zero, so stiffness ratio is undefined or special
        eigs = np.array([0.0 + 10.0j, 0.0 - 10.0j])
        result = self.mod.compute_stiffness(eigs, threshold=1e3)

        # Should handle gracefully - either mark as non-stiff (no real damping)
        # or provide special classification for oscillatory systems
        self.assertIn("stiffness_ratio", result)

        # Test mixed system: real damping with imaginary oscillation
        # lambda = -1 +/- 100i: significant imaginary part, small real damping
        # Real parts: Re(lambda) = -1, -1
        # Stiffness ratio based on real parts: max|-1| / min|-1| = 1.0 (non-stiff)
        eigs_mixed = np.array([-1.0 + 100.0j, -1.0 - 100.0j])
        result_mixed = self.mod.compute_stiffness(eigs_mixed, threshold=1e3)

        # With small equal real parts, system should not be classified as stiff
        self.assertFalse(result_mixed["stiff"])
        self.assertAlmostEqual(result_mixed["stiffness_ratio"], 1.0, places=2)

        # Test system with different real parts and large imaginary components
        # lambda1 = -1000 + 10i, lambda2 = -1 + 10i
        # Real parts: -1000, -1; stiffness ratio = 1000/1 = 1000 (stiff)
        eigs_stiff_imaginary = np.array([-1000.0 + 10.0j, -1.0 + 10.0j])
        result_stiff = self.mod.compute_stiffness(eigs_stiff_imaginary, threshold=100)

        # Should detect stiffness based on real parts, not modulus
        # Modulus approach would give: sqrt(1000^2+100) / sqrt(1+100) ~= 1000/10 = 100
        # Real parts approach: 1000 / 1 = 1000 (correct)
        self.assertTrue(result_stiff["stiff"])
        self.assertGreater(result_stiff["stiffness_ratio"], 900)

    def test_zero_real_part_stiffness_ratio_is_none_not_nan(self):
        """Stiffness ratio must be None (not NaN) when all eigenvalues have zero real parts.

        NaN does not serialize cleanly to JSON and fails equality comparisons.
        None serializes to JSON null and clearly indicates 'not computable'.
        """
        eigs = np.array([0.0 + 10.0j, 0.0 - 10.0j])
        result = self.mod.compute_stiffness(eigs, threshold=1e3)

        # Must be None, not NaN
        self.assertIsNone(result["stiffness_ratio"])

    def test_zero_real_part_stiffness_ratio_json_serializable(self):
        """Result with zero-real-part eigenvalues must serialize cleanly to JSON.

        json.dumps must not produce NaN (invalid JSON) and must round-trip correctly.
        """
        eigs = np.array([0.0 + 10.0j, 0.0 - 10.0j])
        result = self.mod.compute_stiffness(eigs, threshold=1e3)

        # Must not raise and must produce valid JSON
        json_str = json.dumps(result)
        roundtripped = json.loads(json_str)

        # stiffness_ratio should be null in JSON, None after round-trip
        self.assertIsNone(roundtripped["stiffness_ratio"])
        self.assertNotIn("NaN", json_str)

    def test_all_zero_eigs_stiffness_ratio_is_none(self):
        """All-zero eigenvalues (real zeros) should also yield None stiffness_ratio."""
        eigs = np.array([0.0, 0.0])
        result = self.mod.compute_stiffness(eigs, threshold=1e3)

        self.assertIsNone(result["stiffness_ratio"])
        self.assertFalse(result["stiff"])


if __name__ == "__main__":
    unittest.main()
