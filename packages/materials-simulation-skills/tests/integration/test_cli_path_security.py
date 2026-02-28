"""Integration tests for CLI path-traversal rejection."""

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = REPO_ROOT / "skills"
MONOREPO_ROOT = REPO_ROOT.parent.parent

# A path that escapes the sandbox via parent traversal
_TRAVERSAL = "../../../.." + "/nonexistent_file.txt"


def run_script(script_rel_path, extra_args):
    """Run a CLI script with --sandbox-root pointing to MONOREPO_ROOT."""
    script = REPO_ROOT / script_rel_path
    cmd = [
        sys.executable,
        str(script),
        "--sandbox-root",
        str(MONOREPO_ROOT),
        *extra_args,
    ]
    return subprocess.run(
        cmd,
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        check=False,
    )


class TestPathTraversalRejection(unittest.TestCase):
    """Verify that path-traversal inputs are rejected."""

    def _assert_rejected(self, result, msg=""):
        """Assert the script rejected the input via path validation."""
        self.assertNotEqual(
            result.returncode, 0,
            f"Expected non-zero exit code for path traversal. {msg}"
        )
        # Verify the rejection came from sandbox path validation,
        # not from an unrelated error (e.g. unknown argument).
        self.assertIn(
            "outside sandbox",
            result.stderr,
            f"Expected sandbox validation message in stderr. {msg}\n"
            f"stderr was: {result.stderr!r}"
        )

    def test_statistical_analyzer_rejects_traversal(self):
        """statistical_analyzer.py should reject input outside sandbox."""
        result = run_script(
            "skills/simulation-workflow/post-processing/scripts/statistical_analyzer.py",
            ["--input", _TRAVERSAL, "--field", "phi", "--json"],
        )
        self._assert_rejected(result, "statistical_analyzer.py")

    def test_sweep_generator_rejects_traversal(self):
        """sweep_generator.py should reject base-config outside sandbox."""
        result = run_script(
            "skills/simulation-workflow/simulation-orchestrator/scripts/sweep_generator.py",
            [
                "--base-config", _TRAVERSAL,
                "--params", "dt:1e-4:1e-2:3",
                "--method", "linspace",
                "--output-dir", "/tmp/sweep_test_output",
                "--json",
            ],
        )
        self._assert_rejected(result, "sweep_generator.py")


class TestSandboxRootOverride(unittest.TestCase):
    """Verify --sandbox-root allows files inside sandbox."""

    def test_statistical_analyzer_accepts_file_in_sandbox(self):
        """Accept a file that is inside the sandbox-root directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            input_path = Path(tmpdir) / "field.json"
            input_path.write_text(json.dumps({"phi": [1.0, 2.0, 3.0]}))
            result = subprocess.run(
                [
                    sys.executable,
                    str(
                        REPO_ROOT
                        / "skills"
                        / "simulation-workflow"
                        / "post-processing"
                        / "scripts"
                        / "statistical_analyzer.py"
                    ),
                    "--sandbox-root", tmpdir,
                    "--input", str(input_path),
                    "--field", "phi",
                    "--json",
                ],
                cwd=str(REPO_ROOT),
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(result.returncode, 0, f"Expected exit 0, got stderr: {result.stderr}")
            payload = json.loads(result.stdout)
            self.assertNotEqual(payload.get("status"), "error")
            self.assertIn("basic_statistics", payload)


if __name__ == "__main__":
    unittest.main()
