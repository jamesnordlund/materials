import unittest

import numpy as np
import scipy.sparse

from tests.unit._utils import load_module


class TestScalingEquilibration(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.mod = load_module(
            "scaling_equilibration",
            "skills/core-numerical/linear-solvers/scripts/scaling_equilibration.py",
        )

    def test_basic_scaling(self):
        matrix = np.array([[2.0, 0.0], [0.0, 4.0]])
        result = self.mod.compute_scaling(matrix, symmetry_tol=1e-8, symmetric=True)
        self.assertEqual(result["row_scale"], [0.5, 0.25])
        self.assertEqual(result["col_scale"], [0.5, 0.25])
        self.assertAlmostEqual(result["symmetric_scale"][0], 1.0 / np.sqrt(2.0), places=6)
        self.assertAlmostEqual(result["symmetric_scale"][1], 0.5, places=6)

    def test_zero_row(self):
        matrix = np.array([[0.0, 0.0], [1.0, 0.0]])
        result = self.mod.compute_scaling(matrix, symmetry_tol=1e-8, symmetric=False)
        self.assertIn(0, result["zero_rows"])

    def test_symmetric_requires_square(self):
        matrix = np.zeros((2, 3))
        with self.assertRaises(ValueError):
            self.mod.compute_scaling(matrix, symmetry_tol=1e-8, symmetric=True)


    def test_sparse_non_finite_nan(self):
        """Sparse matrix with NaN in .data should raise ValueError."""
        dense = np.array([[1.0, 0.0], [0.0, float("nan")]])
        sparse_matrix = scipy.sparse.csr_matrix(dense)
        with self.assertRaises(ValueError, msg="matrix contains non-finite values"):
            self.mod.compute_scaling(sparse_matrix, symmetry_tol=1e-8, symmetric=False)

    def test_sparse_non_finite_inf(self):
        """Sparse matrix with Inf in .data should raise ValueError."""
        dense = np.array([[1.0, 0.0], [0.0, float("inf")]])
        sparse_matrix = scipy.sparse.csr_matrix(dense)
        with self.assertRaises(ValueError, msg="matrix contains non-finite values"):
            self.mod.compute_scaling(sparse_matrix, symmetry_tol=1e-8, symmetric=False)

    def test_sparse_finite_succeeds(self):
        """Valid sparse matrix should compute scaling without error."""
        dense = np.array([[2.0, 0.0], [0.0, 4.0]])
        sparse_matrix = scipy.sparse.csr_matrix(dense)
        result = self.mod.compute_scaling(sparse_matrix, symmetry_tol=1e-8, symmetric=False)
        self.assertTrue(result["is_sparse"])
        self.assertEqual(result["shape"], [2, 2])


if __name__ == "__main__":
    unittest.main()
