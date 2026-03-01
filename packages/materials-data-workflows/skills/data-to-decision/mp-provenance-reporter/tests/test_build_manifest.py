"""Tests for build_manifest.py -- provenance manifest generation (TASK-024).

Uses importlib to load the script as a module for unit tests, and
subprocess.run for CLI integration tests.

Traces: R-SKL-012, R-TEST-002, R-TEST-003
"""

from __future__ import annotations

import importlib.util
import json
import pathlib
import subprocess
import sys
import unittest
from datetime import datetime

# ---------------------------------------------------------------------------
# Module import via importlib (script is not in a regular package)
# ---------------------------------------------------------------------------

_SCRIPT_PATH = (
    pathlib.Path(__file__).resolve().parent.parent
    / "scripts"
    / "build_manifest.py"
)

_spec = importlib.util.spec_from_file_location("build_manifest", _SCRIPT_PATH)
assert _spec is not None and _spec.loader is not None
_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_mod)

build_manifest = _mod.build_manifest
compute_input_hash = _mod.compute_input_hash
compute_hash_of_outputs = _mod.compute_hash_of_outputs
validate_tool_calls = _mod.validate_tool_calls

# ---------------------------------------------------------------------------
# Fixture loading
# ---------------------------------------------------------------------------

_FIXTURES = pathlib.Path(__file__).resolve().parent / "fixtures"


def _load_fixture(name: str):
    """Load and return parsed JSON from the fixtures/ directory."""
    return json.loads((_FIXTURES / name).read_text())


# ===========================================================================
# Unit tests for build_manifest() function
# ===========================================================================


class TestBuildManifestFunction(unittest.TestCase):
    """Tests for the ``build_manifest()`` function."""

    def test_manifest_has_required_top_level_keys(self):
        """Manifest output contains 'metadata' and 'manifest' top-level keys."""
        tool_calls = _load_fixture("tool_calls_input.json")
        validated = validate_tool_calls(tool_calls)
        result = build_manifest(validated)

        self.assertIn("metadata", result)
        self.assertIn("manifest", result)

    def test_metadata_has_required_keys(self):
        """metadata contains script name and version."""
        tool_calls = _load_fixture("tool_calls_input.json")
        validated = validate_tool_calls(tool_calls)
        result = build_manifest(validated)

        metadata = result["metadata"]
        self.assertIn("script", metadata)
        self.assertIn("version", metadata)
        self.assertEqual(metadata["script"], "build_manifest.py")
        self.assertIsInstance(metadata["version"], str)

    def test_manifest_has_required_keys(self):
        """manifest section contains all required sub-keys."""
        tool_calls = _load_fixture("tool_calls_input.json")
        validated = validate_tool_calls(tool_calls)
        result = build_manifest(validated)

        manifest = result["manifest"]
        for key in ("inputs", "tool_calls", "db_version", "timestamps", "hash_of_outputs"):
            self.assertIn(key, manifest, f"Missing manifest key: {key}")

    def test_inputs_section_has_required_keys(self):
        """manifest.inputs contains input_hash and tool_calls_count."""
        tool_calls = _load_fixture("tool_calls_input.json")
        validated = validate_tool_calls(tool_calls)
        result = build_manifest(validated)

        inputs = result["manifest"]["inputs"]
        self.assertIn("input_hash", inputs)
        self.assertIn("tool_calls_count", inputs)
        self.assertEqual(inputs["tool_calls_count"], len(tool_calls))

    def test_generated_at_is_iso_8601(self):
        """timestamps.generated_at is a valid ISO-8601 datetime string."""
        tool_calls = _load_fixture("tool_calls_input.json")
        validated = validate_tool_calls(tool_calls)
        result = build_manifest(validated)

        generated_at = result["manifest"]["timestamps"]["generated_at"]
        self.assertIsInstance(generated_at, str)
        # Should parse without error.
        datetime.fromisoformat(generated_at)

    def test_tool_calls_echoed_in_output(self):
        """tool_calls in the manifest match the input."""
        tool_calls = _load_fixture("tool_calls_input.json")
        validated = validate_tool_calls(tool_calls)
        result = build_manifest(validated)

        self.assertEqual(result["manifest"]["tool_calls"], tool_calls)

    def test_manifest_output_is_json_serializable(self):
        """Full manifest can be serialised to JSON without errors."""
        tool_calls = _load_fixture("tool_calls_input.json")
        validated = validate_tool_calls(tool_calls)
        result = build_manifest(validated)

        # Should not raise.
        json_str = json.dumps(result, indent=2, sort_keys=True)
        roundtrip = json.loads(json_str)
        self.assertEqual(roundtrip["metadata"]["script"], "build_manifest.py")

    def test_structure_matches_expected_fixture(self):
        """Manifest structure matches the expected fixture schema."""
        expected = _load_fixture("manifest_expected.json")
        tool_calls = _load_fixture("tool_calls_input.json")
        validated = validate_tool_calls(tool_calls)
        result = build_manifest(validated)

        # Validate top-level keys.
        for key in expected["_test_notes"]["required_top_level_keys"]:
            self.assertIn(key, result, f"Missing top-level key: {key}")

        # Validate manifest sub-keys.
        for key in expected["_test_notes"]["required_manifest_keys"]:
            self.assertIn(key, result["manifest"], f"Missing manifest key: {key}")

        # Validate metadata sub-keys.
        for key in expected["_test_notes"]["required_metadata_keys"]:
            self.assertIn(key, result["metadata"], f"Missing metadata key: {key}")

        # Validate input sub-keys.
        for key in expected["_test_notes"]["required_input_keys"]:
            self.assertIn(
                key, result["manifest"]["inputs"], f"Missing input key: {key}"
            )


# ===========================================================================
# Hash stability tests
# ===========================================================================


class TestHashStability(unittest.TestCase):
    """Verify that hash computation is deterministic (same input -> same hash)."""

    def test_input_hash_deterministic(self):
        """compute_input_hash returns the same value on repeated calls."""
        tool_calls = _load_fixture("tool_calls_input.json")
        hash1 = compute_input_hash(tool_calls)
        hash2 = compute_input_hash(tool_calls)
        self.assertEqual(hash1, hash2)

    def test_hash_of_outputs_deterministic(self):
        """compute_hash_of_outputs returns the same value on repeated calls."""
        tool_calls = _load_fixture("tool_calls_input.json")
        hash1 = compute_hash_of_outputs(tool_calls)
        hash2 = compute_hash_of_outputs(tool_calls)
        self.assertEqual(hash1, hash2)

    def test_build_manifest_hash_stability(self):
        """Two calls to build_manifest produce identical hashes."""
        tool_calls = _load_fixture("tool_calls_input.json")
        validated = validate_tool_calls(tool_calls)

        result1 = build_manifest(validated)
        result2 = build_manifest(validated)

        self.assertEqual(
            result1["manifest"]["inputs"]["input_hash"],
            result2["manifest"]["inputs"]["input_hash"],
        )
        self.assertEqual(
            result1["manifest"]["hash_of_outputs"],
            result2["manifest"]["hash_of_outputs"],
        )

    def test_hashes_start_with_sha256_prefix(self):
        """All hashes carry a 'sha256:' prefix."""
        tool_calls = _load_fixture("tool_calls_input.json")
        validated = validate_tool_calls(tool_calls)
        result = build_manifest(validated)

        self.assertTrue(
            result["manifest"]["inputs"]["input_hash"].startswith("sha256:")
        )
        self.assertTrue(
            result["manifest"]["hash_of_outputs"].startswith("sha256:")
        )

    def test_input_hash_matches_direct_computation(self):
        """Manifest input_hash matches direct compute_input_hash call."""
        tool_calls = _load_fixture("tool_calls_input.json")
        validated = validate_tool_calls(tool_calls)
        result = build_manifest(validated)

        expected_hash = compute_input_hash(validated)
        self.assertEqual(result["manifest"]["inputs"]["input_hash"], expected_hash)

    def test_hash_of_outputs_matches_direct_computation(self):
        """Manifest hash_of_outputs matches direct compute_hash_of_outputs call."""
        tool_calls = _load_fixture("tool_calls_input.json")
        validated = validate_tool_calls(tool_calls)
        result = build_manifest(validated)

        expected_hash = compute_hash_of_outputs(validated)
        self.assertEqual(result["manifest"]["hash_of_outputs"], expected_hash)


# ===========================================================================
# Empty tool_calls tests
# ===========================================================================


class TestEmptyToolCalls(unittest.TestCase):
    """Tests for empty tool_calls array (function-level, not CLI).

    Note: The CLI rejects empty arrays with exit code 1. These tests exercise
    the ``build_manifest()`` function directly to verify it handles the
    degenerate case gracefully.
    """

    def test_empty_tool_calls_produces_valid_manifest(self):
        """build_manifest([]) returns a dict with all required keys."""
        result = build_manifest([])

        self.assertIn("metadata", result)
        self.assertIn("manifest", result)
        manifest = result["manifest"]
        self.assertIn("inputs", manifest)
        self.assertIn("tool_calls", manifest)
        self.assertIn("hash_of_outputs", manifest)
        self.assertIn("timestamps", manifest)

    def test_empty_tool_calls_count_is_zero(self):
        """tool_calls_count is 0 for empty input."""
        result = build_manifest([])
        self.assertEqual(result["manifest"]["inputs"]["tool_calls_count"], 0)

    def test_empty_tool_calls_hash_is_deterministic(self):
        """Hash of empty input is deterministic."""
        result1 = build_manifest([])
        result2 = build_manifest([])

        self.assertEqual(
            result1["manifest"]["hash_of_outputs"],
            result2["manifest"]["hash_of_outputs"],
        )
        self.assertEqual(
            result1["manifest"]["inputs"]["input_hash"],
            result2["manifest"]["inputs"]["input_hash"],
        )

    def test_empty_tool_calls_list_in_output(self):
        """tool_calls in the manifest is an empty list."""
        result = build_manifest([])
        self.assertEqual(result["manifest"]["tool_calls"], [])


# ===========================================================================
# CLI integration tests (subprocess)
# ===========================================================================


class TestBuildManifestCLI(unittest.TestCase):
    """Integration tests that invoke build_manifest.py as a subprocess."""

    def test_help_exits_zero(self):
        """--help exits with code 0."""
        result = subprocess.run(
            [sys.executable, str(_SCRIPT_PATH), "--help"],
            capture_output=True,
            text=True,
            timeout=30,
        )
        self.assertEqual(result.returncode, 0)
        self.assertIn("build_manifest.py", result.stdout)

    def test_valid_input_produces_json(self):
        """Valid input file produces parseable JSON on stdout."""
        input_path = _FIXTURES / "tool_calls_input.json"
        result = subprocess.run(
            [sys.executable, str(_SCRIPT_PATH), "--input", str(input_path), "--json"],
            capture_output=True,
            text=True,
            timeout=30,
        )
        self.assertEqual(result.returncode, 0, msg=result.stderr)

        output = json.loads(result.stdout)
        self.assertIn("metadata", output)
        self.assertIn("manifest", output)

    def test_missing_input_exits_nonzero(self):
        """Missing --input argument causes non-zero exit."""
        result = subprocess.run(
            [sys.executable, str(_SCRIPT_PATH)],
            capture_output=True,
            text=True,
            timeout=30,
        )
        self.assertNotEqual(result.returncode, 0)

    def test_nonexistent_file_exits_one(self):
        """Non-existent input file exits with code 1."""
        result = subprocess.run(
            [sys.executable, str(_SCRIPT_PATH), "--input", "/tmp/does_not_exist.json"],
            capture_output=True,
            text=True,
            timeout=30,
        )
        self.assertEqual(result.returncode, 1, msg=result.stderr)
        self.assertIn("not found", result.stderr.lower())


if __name__ == "__main__":
    unittest.main()
