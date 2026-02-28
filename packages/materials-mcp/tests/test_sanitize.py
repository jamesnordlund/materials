"""Tests for _sanitize.py -- API key sanitization."""

import os
import unittest
from unittest.mock import patch

from mcp_materials._sanitize import sanitize_message


class TestSanitizeMessage(unittest.TestCase):
    """Tests for sanitize_message function."""

    def test_key_present_in_message(self):
        """API key value in message is replaced with [REDACTED]."""
        with patch.dict(os.environ, {"MP_API_KEY": "abcd1234secret"}):
            result = sanitize_message("Error connecting with key abcd1234secret")
            self.assertNotIn("abcd1234secret", result)
            self.assertIn("[REDACTED]", result)

    def test_key_absent_from_message(self):
        """Message without key value is returned unchanged."""
        with patch.dict(os.environ, {"MP_API_KEY": "abcd1234secret"}):
            result = sanitize_message("Connection timed out")
            self.assertEqual(result, "Connection timed out")

    def test_empty_key_env_var(self):
        """Empty env var does not cause replacement."""
        with patch.dict(os.environ, {"MP_API_KEY": ""}, clear=False):
            result = sanitize_message("some message")
            self.assertEqual(result, "some message")

    def test_short_key_skipped(self):
        """Keys shorter than 4 chars are not replaced (avoids false positives)."""
        with patch.dict(os.environ, {"MP_API_KEY": "abc"}, clear=False):
            result = sanitize_message("abc is in the message abc")
            # "abc" should NOT be replaced since len < 4
            self.assertEqual(result, "abc is in the message abc")

    def test_multiple_env_vars(self):
        """Both MP_API_KEY and PMG_MAPI_KEY are sanitized."""
        with patch.dict(os.environ, {
            "MP_API_KEY": "key_primary_1234",
            "PMG_MAPI_KEY": "key_legacy_5678",
        }):
            msg = "Used key_primary_1234 and key_legacy_5678"
            result = sanitize_message(msg)
            self.assertNotIn("key_primary_1234", result)
            self.assertNotIn("key_legacy_5678", result)
            self.assertEqual(result.count("[REDACTED]"), 2)

    def test_key_appears_multiple_times(self):
        """All occurrences of the key are replaced."""
        with patch.dict(os.environ, {"MP_API_KEY": "mykey1234"}):
            result = sanitize_message("mykey1234 failed, retry with mykey1234")
            self.assertNotIn("mykey1234", result)
            self.assertEqual(result.count("[REDACTED]"), 2)

    def test_no_env_vars_set(self):
        """Message unchanged when no API key env vars are set."""
        with patch.dict(os.environ, {}, clear=True):
            os.environ.pop("MP_API_KEY", None)
            os.environ.pop("PMG_MAPI_KEY", None)
            result = sanitize_message("some error occurred")
            self.assertEqual(result, "some error occurred")

    def test_bearer_token_redacted(self):
        """Bearer tokens are redacted."""
        msg = "Failed: Bearer abc123def456ghi789jkl012mno345"
        result = sanitize_message(msg)
        self.assertNotIn("abc123def456ghi789jkl012mno345", result)
        self.assertIn("[REDACTED]", result)

    def test_bearer_token_case_insensitive(self):
        """Bearer token redaction is case-insensitive."""
        msg = "Failed: bearer token123456secret789"
        result = sanitize_message(msg)
        self.assertNotIn("token123456secret789", result)
        self.assertIn("[REDACTED]", result)

    def test_url_redacted(self):
        """URLs are redacted."""
        msg = "Connected to https://api.example.com/v1/endpoint?key=secret"
        result = sanitize_message(msg)
        self.assertNotIn("https://api.example.com", result)
        self.assertIn("[REDACTED_URL]", result)

    def test_http_url_redacted(self):
        """HTTP URLs are redacted."""
        msg = "Connected to http://example.com/path"
        result = sanitize_message(msg)
        self.assertNotIn("http://example.com", result)
        self.assertIn("[REDACTED_URL]", result)

    def test_basic_auth_redacted(self):
        """Basic auth credentials are redacted."""
        msg = "Authorization: Basic dXNlcjpwYXNzd29yZA=="
        result = sanitize_message(msg)
        self.assertNotIn("dXNlcjpwYXNzd29yZA==", result)
        self.assertIn("[REDACTED]", result)

    def test_basic_auth_case_insensitive(self):
        """Basic auth redaction is case-insensitive."""
        msg = "AUTHORIZATION: basic token123456"
        result = sanitize_message(msg)
        self.assertNotIn("token123456", result)
        self.assertIn("[REDACTED]", result)

    def test_query_param_token_redacted(self):
        """Query parameters with 'token' are redacted."""
        msg = "Request ?token=secret123456789"
        result = sanitize_message(msg)
        self.assertNotIn("secret123456789", result)
        self.assertIn("[REDACTED]", result)

    def test_query_param_key_redacted(self):
        """Query parameters with 'key' are redacted."""
        msg = "Request &key=myapikey123"
        result = sanitize_message(msg)
        self.assertNotIn("myapikey123", result)
        self.assertIn("[REDACTED]", result)

    def test_query_param_api_key_redacted(self):
        """Query parameters with 'api_key' are redacted."""
        msg = "Request ?api_key=abc123def456"
        result = sanitize_message(msg)
        self.assertNotIn("abc123def456", result)
        self.assertIn("[REDACTED]", result)

    def test_query_param_apikey_redacted(self):
        """Query parameters with 'apikey' are redacted."""
        msg = "Request &apikey=xyz789"
        result = sanitize_message(msg)
        self.assertNotIn("xyz789", result)
        self.assertIn("[REDACTED]", result)

    def test_query_param_secret_redacted(self):
        """Query parameters with 'secret' are redacted."""
        msg = "Request ?secret=topsecretvalue"
        result = sanitize_message(msg)
        self.assertNotIn("topsecretvalue", result)
        self.assertIn("[REDACTED]", result)

    def test_query_param_case_insensitive(self):
        """Query parameter redaction is case-insensitive."""
        msg = "Request ?TOKEN=secret123&KEY=key456&API_KEY=apikey789"
        result = sanitize_message(msg)
        self.assertNotIn("secret123", result)
        self.assertNotIn("key456", result)
        self.assertNotIn("apikey789", result)
        self.assertEqual(result.count("[REDACTED]"), 3)

    def test_multiple_sensitive_patterns(self):
        """Multiple sensitive patterns in one message are all redacted."""
        msg = (
            "Error: Bearer auth123 failed. URL: https://api.example.com/endpoint. "
            "Auth: Authorization: Basic secret456. Query: ?token=abc123&key=def456"
        )
        result = sanitize_message(msg)
        # Verify no original sensitive values remain
        self.assertNotIn("auth123", result)
        self.assertNotIn("https://api.example.com", result)
        self.assertNotIn("secret456", result)
        self.assertNotIn("abc123", result)
        self.assertNotIn("def456", result)


if __name__ == "__main__":
    unittest.main()
