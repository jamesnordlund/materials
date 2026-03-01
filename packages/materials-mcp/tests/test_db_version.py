"""Tests for _db_version.py -- cached database version fetcher."""

import unittest
from unittest.mock import MagicMock, patch

import mcp_materials._db_version as db_version_mod
from mcp_materials._db_version import get_db_version


def _reset_cache():
    """Reset module-level cache state between tests."""
    db_version_mod._cached_db_version = None
    db_version_mod._cached_at = 0.0


class TestGetDbVersion(unittest.IsolatedAsyncioTestCase):
    """Tests for get_db_version async function."""

    def setUp(self):
        _reset_cache()

    def tearDown(self):
        _reset_cache()

    @patch.object(db_version_mod, "MPRester", create=True)
    async def test_success_returns_version_and_no_error(self, mock_rester_cls):
        """Successful fetch returns (version_string, None)."""
        mock_mpr = MagicMock()
        mock_mpr.get_database_version.return_value = "2024.01.15"
        mock_rester_cls.return_value.__enter__ = MagicMock(return_value=mock_mpr)
        mock_rester_cls.return_value.__exit__ = MagicMock(return_value=False)

        version, error = await get_db_version("test-key")

        self.assertEqual(version, "2024.01.15")
        self.assertIsNone(error)

    @patch.object(db_version_mod, "MPRester", create=True)
    async def test_failure_returns_none_and_error(self, mock_rester_cls):
        """Failed fetch returns (None, error_message)."""
        mock_rester_cls.return_value.__enter__ = MagicMock(
            side_effect=RuntimeError("connection refused")
        )

        version, error = await get_db_version("test-key")

        self.assertIsNone(version)
        self.assertIsNotNone(error)
        self.assertIn("connection refused", error)

    @patch.object(db_version_mod, "MPRester", create=True)
    async def test_caching_within_ttl(self, mock_rester_cls):
        """Second call within TTL returns cached result without calling MPRester."""
        mock_mpr = MagicMock()
        mock_mpr.get_database_version.return_value = "2024.02.01"
        mock_rester_cls.return_value.__enter__ = MagicMock(return_value=mock_mpr)
        mock_rester_cls.return_value.__exit__ = MagicMock(return_value=False)

        # First call - populates cache
        v1, e1 = await get_db_version("test-key")
        self.assertEqual(v1, "2024.02.01")
        self.assertIsNone(e1)

        # Reset mock to verify it's NOT called again
        mock_rester_cls.reset_mock()

        # Second call - should use cache
        v2, e2 = await get_db_version("test-key")
        self.assertEqual(v2, "2024.02.01")
        self.assertIsNone(e2)

        # MPRester should not have been called again
        mock_rester_cls.assert_not_called()

    @patch("mcp_materials._db_version.time.monotonic")
    @patch.object(db_version_mod, "MPRester", create=True)
    async def test_ttl_expiry_triggers_refetch(self, mock_rester_cls, mock_time):
        """After TTL expires, MPRester is called again."""
        mock_mpr = MagicMock()
        mock_mpr.get_database_version.return_value = "2024.03.01"
        mock_rester_cls.return_value.__enter__ = MagicMock(return_value=mock_mpr)
        mock_rester_cls.return_value.__exit__ = MagicMock(return_value=False)

        # First call at time=1000
        mock_time.return_value = 1000.0
        v1, e1 = await get_db_version("test-key")
        self.assertEqual(v1, "2024.03.01")

        # Update the version for the second fetch
        mock_mpr.get_database_version.return_value = "2024.04.01"

        # Second call at time=1000 + 301 (past TTL of 300s)
        mock_time.return_value = 1301.0
        v2, e2 = await get_db_version("test-key")
        self.assertEqual(v2, "2024.04.01")
        self.assertIsNone(e2)

    @patch.object(db_version_mod, "MPRester", create=True)
    async def test_timeout_returns_none_and_error(self, mock_rester_cls):
        """If asyncio.wait_for times out, returns (None, error_message)."""
        mock_mpr = MagicMock()
        mock_rester_cls.return_value.__enter__ = MagicMock(return_value=mock_mpr)
        mock_rester_cls.return_value.__exit__ = MagicMock(return_value=False)

        with patch("mcp_materials._db_version.asyncio.wait_for",
                    side_effect=TimeoutError()):
            version, error = await get_db_version("test-key")

        self.assertIsNone(version)
        self.assertIsNotNone(error)

    @patch.object(db_version_mod, "MPRester", create=True)
    async def test_exception_message_is_sanitized(self, mock_rester_cls):
        """Error messages are passed through sanitize_message."""
        mock_rester_cls.return_value.__enter__ = MagicMock(
            side_effect=RuntimeError("failed with key abcdef1234")
        )

        with patch.dict("os.environ", {"MP_API_KEY": "abcdef1234"}):
            version, error = await get_db_version("test-key")

        self.assertIsNone(version)
        # The sanitizer should redact the API key
        self.assertNotIn("abcdef1234", error)


if __name__ == "__main__":
    unittest.main()
