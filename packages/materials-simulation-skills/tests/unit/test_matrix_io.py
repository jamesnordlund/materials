"""Unit tests for the shared _matrix_io module."""

import os
import tempfile
import unittest

import numpy as np
import scipy.io
import scipy.sparse

from tests.unit._utils import load_module


class TestLoadMatrix(unittest.TestCase):
    """Tests for load_matrix in skills/_shared/_matrix_io.py."""

    @classmethod
    def setUpClass(cls):
        cls.mod = load_module(
            "_matrix_io",
            "skills/_shared/_matrix_io.py",
        )

    def test_load_text_whitespace_delimited(self):
        """Plain text file with whitespace delimiter loads as dense ndarray."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
            f.write("1 2 3\n4 5 6\n")
            path = f.name
        try:
            m = self.mod.load_matrix(path)
            self.assertIsInstance(m, np.ndarray)
            np.testing.assert_array_equal(m, [[1, 2, 3], [4, 5, 6]])
        finally:
            os.unlink(path)

    def test_load_text_comma_delimited(self):
        """Plain text file with comma delimiter loads correctly."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
            f.write("1,2\n3,4\n")
            path = f.name
        try:
            m = self.mod.load_matrix(path, delimiter=",")
            self.assertIsInstance(m, np.ndarray)
            np.testing.assert_array_equal(m, [[1, 2], [3, 4]])
        finally:
            os.unlink(path)

    def test_load_npy(self):
        """NumPy .npy binary file loads as dense ndarray."""
        arr = np.array([[7.0, 8.0], [9.0, 10.0]])
        with tempfile.NamedTemporaryFile(suffix=".npy", delete=False) as f:
            np.save(f.name, arr)
            path = f.name
        try:
            m = self.mod.load_matrix(path)
            self.assertIsInstance(m, np.ndarray)
            np.testing.assert_array_equal(m, arr)
        finally:
            os.unlink(path)

    def test_load_mtx(self):
        """Matrix Market .mtx file loads as sparse CSR matrix."""
        dense = np.array([[1.0, 0.0], [0.0, 2.0]])
        sparse_mat = scipy.sparse.csr_matrix(dense)
        with tempfile.NamedTemporaryFile(suffix=".mtx", delete=False) as f:
            scipy.io.mmwrite(f.name, sparse_mat)
            path = f.name
        try:
            m = self.mod.load_matrix(path)
            self.assertTrue(scipy.sparse.issparse(m))
            self.assertEqual(m.format, "csr")
            np.testing.assert_array_equal(m.toarray(), dense)
        finally:
            os.unlink(path)

    def test_delimiter_ignored_for_npy(self):
        """Delimiter argument is harmlessly ignored for .npy files."""
        arr = np.array([[1.0]])
        with tempfile.NamedTemporaryFile(suffix=".npy", delete=False) as f:
            np.save(f.name, arr)
            path = f.name
        try:
            m = self.mod.load_matrix(path, delimiter=",")
            np.testing.assert_array_equal(m, arr)
        finally:
            os.unlink(path)

    def test_delimiter_ignored_for_mtx(self):
        """Delimiter argument is harmlessly ignored for .mtx files."""
        dense = np.eye(2)
        sparse_mat = scipy.sparse.csr_matrix(dense)
        with tempfile.NamedTemporaryFile(suffix=".mtx", delete=False) as f:
            scipy.io.mmwrite(f.name, sparse_mat)
            path = f.name
        try:
            m = self.mod.load_matrix(path, delimiter=",")
            self.assertTrue(scipy.sparse.issparse(m))
        finally:
            os.unlink(path)

    def test_nonexistent_file_raises_valueerror(self):
        """Missing file raises ValueError with path in message."""
        with self.assertRaises(ValueError) as ctx:
            self.mod.load_matrix("/nonexistent/path/matrix.txt")
        self.assertIn("/nonexistent/path/matrix.txt", str(ctx.exception))

    def test_invalid_content_raises_valueerror(self):
        """Unparseable content raises ValueError."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
            f.write("not a matrix at all\n")
            path = f.name
        try:
            with self.assertRaises(ValueError):
                self.mod.load_matrix(path)
        finally:
            os.unlink(path)

    def test_default_delimiter_is_none(self):
        """When delimiter is omitted, whitespace splitting is used."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".dat", delete=False) as f:
            f.write("1  2  3\n4  5  6\n")
            path = f.name
        try:
            m = self.mod.load_matrix(path)
            np.testing.assert_array_equal(m, [[1, 2, 3], [4, 5, 6]])
        finally:
            os.unlink(path)


if __name__ == "__main__":
    unittest.main()
