"""Tests for _prereqs.py -- MPCONTRIBS_API_KEY resolution in contribs prerequisites."""

import os
import unittest
from unittest.mock import patch


class TestContribsApiKeyResolution(unittest.TestCase):
    """Verify MPCONTRIBS_API_KEY support in _check_contribs_prerequisites."""

    @patch("mcp_materials._prereqs.HAS_MPCONTRIBS", True)
    def test_contribs_api_key_used_when_mp_api_key_unset(self):
        """MPCONTRIBS_API_KEY is returned when MP_API_KEY is not set."""
        from mcp_materials._prereqs import _check_contribs_prerequisites

        with patch.dict(os.environ, {
            "MPCONTRIBS_API_KEY": "contribs-key-12345678",
        }, clear=True):
            error_response, api_key = _check_contribs_prerequisites()
            self.assertIsNone(error_response)
            self.assertEqual(api_key, "contribs-key-12345678")

    @patch("mcp_materials._prereqs.HAS_MPCONTRIBS", True)
    def test_contribs_api_key_takes_precedence_over_mp_api_key(self):
        """MPCONTRIBS_API_KEY takes precedence when both are set."""
        from mcp_materials._prereqs import _check_contribs_prerequisites

        with patch.dict(os.environ, {
            "MPCONTRIBS_API_KEY": "contribs-key-preferred",
            "MP_API_KEY": "mp-key-fallback",
        }, clear=True):
            error_response, api_key = _check_contribs_prerequisites()
            self.assertIsNone(error_response)
            self.assertEqual(api_key, "contribs-key-preferred")

    @patch("mcp_materials._prereqs.HAS_MPCONTRIBS", True)
    def test_contribs_api_key_takes_precedence_over_pmg_mapi_key(self):
        """MPCONTRIBS_API_KEY takes precedence over PMG_MAPI_KEY."""
        from mcp_materials._prereqs import _check_contribs_prerequisites

        with patch.dict(os.environ, {
            "MPCONTRIBS_API_KEY": "contribs-key-preferred",
            "PMG_MAPI_KEY": "pmg-key-fallback",
        }, clear=True):
            error_response, api_key = _check_contribs_prerequisites()
            self.assertIsNone(error_response)
            self.assertEqual(api_key, "contribs-key-preferred")

    @patch("mcp_materials._prereqs.HAS_MPCONTRIBS", True)
    def test_falls_back_to_mp_api_key_when_contribs_key_unset(self):
        """Falls back to MP_API_KEY when MPCONTRIBS_API_KEY is not set."""
        from mcp_materials._prereqs import _check_contribs_prerequisites

        with patch.dict(os.environ, {
            "MP_API_KEY": "mp-key-fallback-val",
        }, clear=True):
            error_response, api_key = _check_contribs_prerequisites()
            self.assertIsNone(error_response)
            self.assertEqual(api_key, "mp-key-fallback-val")

    @patch("mcp_materials._prereqs.HAS_MPCONTRIBS", True)
    def test_error_when_no_keys_set(self):
        """Returns error when no API keys are set at all."""
        from mcp_materials._prereqs import _check_contribs_prerequisites

        with patch.dict(os.environ, {}, clear=True):
            error_response, api_key = _check_contribs_prerequisites()
            self.assertIsNotNone(error_response)
            self.assertIsNone(api_key)
            self.assertIn("MPCONTRIBS_API_KEY", error_response)


if __name__ == "__main__":
    unittest.main()
