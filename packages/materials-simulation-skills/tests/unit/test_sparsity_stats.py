import unittest

import numpy as np
import scipy.sparse

from tests.unit._utils import load_module


class TestSparsityStats(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.mod = load_module(
            "sparsity_stats",
            "skills/core-numerical/linear-solvers/scripts/sparsity_stats.py",
        )

    def test_identity(self):
        matrix = np.eye(4)
        stats = self.mod.compute_stats(matrix, symmetry_tol=1e-8)
        self.assertEqual(stats["nnz"], 4)
        self.assertTrue(stats["symmetry"])
        self.assertEqual(stats["bandwidth"], 0)

    def test_bandwidth(self):
        matrix = np.array([[1, 1, 0], [1, 1, 1], [0, 1, 1]], dtype=float)
        stats = self.mod.compute_stats(matrix, symmetry_tol=1e-8)
        self.assertEqual(stats["bandwidth"], 1)

    def test_non_finite(self):
        matrix = np.array([[1.0, float("nan")]])
        with self.assertRaises(ValueError):
            self.mod.compute_stats(matrix, symmetry_tol=1e-8)


    def test_sparse_non_finite_nan(self):
        """Sparse matrix with NaN in .data should raise ValueError."""
        dense = np.array([[1.0, float("nan")], [0.0, 2.0]])
        sparse_matrix = scipy.sparse.csr_matrix(dense)
        with self.assertRaises(ValueError, msg="matrix contains non-finite values"):
            self.mod.compute_stats(sparse_matrix, symmetry_tol=1e-8)

    def test_sparse_non_finite_inf(self):
        """Sparse matrix with Inf in .data should raise ValueError."""
        dense = np.array([[float("inf"), 0.0], [0.0, 2.0]])
        sparse_matrix = scipy.sparse.csr_matrix(dense)
        with self.assertRaises(ValueError, msg="matrix contains non-finite values"):
            self.mod.compute_stats(sparse_matrix, symmetry_tol=1e-8)

    def test_sparse_finite_succeeds(self):
        """Valid sparse matrix should compute stats without error."""
        dense = np.eye(4)
        sparse_matrix = scipy.sparse.csr_matrix(dense)
        stats = self.mod.compute_stats(sparse_matrix, symmetry_tol=1e-8)
        self.assertTrue(stats["is_sparse"])
        self.assertEqual(stats["nnz"], 4)


if __name__ == "__main__":
    unittest.main()
