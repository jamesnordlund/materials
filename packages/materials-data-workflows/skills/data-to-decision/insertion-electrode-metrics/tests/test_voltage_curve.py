"""Tests for voltage_curve_summarizer.py -- voltage curve summary and plateau detection.

Tests the ``summarize_curve``, ``detect_plateaus``, and ``_validate_points``
functions directly and the CLI via subprocess.
Validates summary statistics and plateau detection against fixture data,
and verifies that empty input produces graceful output.

Traces: R-SKL-011, R-TEST-002, R-TEST-003
"""

from __future__ import annotations

import json
import pathlib
import subprocess
import sys

import pytest

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

_TESTS_DIR = pathlib.Path(__file__).parent
_FIXTURES_DIR = _TESTS_DIR / "fixtures"
_SCRIPTS_DIR = _TESTS_DIR.parent / "scripts"
_SCRIPT = _SCRIPTS_DIR / "voltage_curve_summarizer.py"
_FIXTURE_CURVE = _FIXTURES_DIR / "voltage_curve.json"


# ---------------------------------------------------------------------------
# Fixture helpers
# ---------------------------------------------------------------------------


@pytest.fixture()
def voltage_points() -> list[dict]:
    """Load the voltage_curve.json fixture."""
    return json.loads(_FIXTURE_CURVE.read_text(encoding="utf-8"))


# ---------------------------------------------------------------------------
# Dynamic import helper
# ---------------------------------------------------------------------------


def _import_module():
    """Import the voltage_curve_summarizer module from its script path."""
    import importlib.util

    spec = importlib.util.spec_from_file_location("voltage_curve_summarizer", _SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


# ---------------------------------------------------------------------------
# summarize_curve tests
# ---------------------------------------------------------------------------


class TestSummarizeCurve:
    """Test ``summarize_curve`` with the voltage_curve fixture."""

    def test_n_steps_matches_fixture_length(self, voltage_points):
        """n_steps equals the number of points in the fixture."""
        mod = _import_module()
        validated = mod._validate_points(voltage_points)
        result = mod.summarize_curve(validated)
        assert result["n_steps"] == len(voltage_points)

    def test_min_voltage(self, voltage_points):
        """min_voltage_V matches the minimum voltage in the fixture."""
        mod = _import_module()
        validated = mod._validate_points(voltage_points)
        result = mod.summarize_curve(validated)
        expected_min = min(p["voltage_V"] for p in voltage_points)
        assert result["min_voltage_V"] == pytest.approx(expected_min, abs=1e-4)

    def test_max_voltage(self, voltage_points):
        """max_voltage_V matches the maximum voltage in the fixture."""
        mod = _import_module()
        validated = mod._validate_points(voltage_points)
        result = mod.summarize_curve(validated)
        expected_max = max(p["voltage_V"] for p in voltage_points)
        assert result["max_voltage_V"] == pytest.approx(expected_max, abs=1e-4)

    def test_avg_voltage(self, voltage_points):
        """avg_voltage_V is the mean of all fixture voltages."""
        mod = _import_module()
        validated = mod._validate_points(voltage_points)
        result = mod.summarize_curve(validated)
        voltages = [p["voltage_V"] for p in voltage_points]
        expected_avg = sum(voltages) / len(voltages)
        assert result["avg_voltage_V"] == pytest.approx(expected_avg, abs=1e-4)

    def test_metadata_present(self, voltage_points):
        """Output includes metadata with script name and version."""
        mod = _import_module()
        validated = mod._validate_points(voltage_points)
        result = mod.summarize_curve(validated)
        assert result["metadata"]["script"] == "voltage_curve_summarizer.py"
        assert "version" in result["metadata"]

    def test_hysteresis_proxy_present(self, voltage_points):
        """hysteresis_proxy_V is present and equals max - min voltage."""
        mod = _import_module()
        validated = mod._validate_points(voltage_points)
        result = mod.summarize_curve(validated)
        expected = max(p["voltage_V"] for p in voltage_points) - min(
            p["voltage_V"] for p in voltage_points
        )
        assert result["hysteresis_proxy_V"] == pytest.approx(expected, abs=1e-4)

    def test_plateaus_list_present(self, voltage_points):
        """plateaus key is a list in the output."""
        mod = _import_module()
        validated = mod._validate_points(voltage_points)
        result = mod.summarize_curve(validated)
        assert isinstance(result["plateaus"], list)


# ---------------------------------------------------------------------------
# Plateau detection tests
# ---------------------------------------------------------------------------


class TestDetectPlateaus:
    """Test ``detect_plateaus`` with the voltage_curve fixture."""

    def test_at_least_one_plateau_detected(self, voltage_points):
        """The fixture curve (LiFePO4-like) should have at least one plateau."""
        mod = _import_module()
        validated = mod._validate_points(voltage_points)
        plateaus = mod.detect_plateaus(validated)
        assert len(plateaus) >= 1

    def test_plateau_voltage_in_expected_range(self, voltage_points):
        """Detected plateau voltage should be near 3.45 V (the flat region)."""
        mod = _import_module()
        validated = mod._validate_points(voltage_points)
        plateaus = mod.detect_plateaus(validated)
        # At least one plateau should have voltage near 3.45.
        plateau_voltages = [p["voltage_V"] for p in plateaus]
        assert any(
            abs(v - 3.45) < 0.1 for v in plateau_voltages
        ), f"No plateau near 3.45 V found; got {plateau_voltages}"

    def test_plateau_has_capacity_fraction(self, voltage_points):
        """Each plateau has a capacity_fraction key."""
        mod = _import_module()
        validated = mod._validate_points(voltage_points)
        plateaus = mod.detect_plateaus(validated)
        for p in plateaus:
            assert "capacity_fraction" in p
            assert 0.0 < p["capacity_fraction"] <= 1.0

    def test_single_point_no_plateaus(self):
        """A single-point input produces no plateaus."""
        mod = _import_module()
        points = [{"x": 0.0, "voltage_V": 3.5}]
        plateaus = mod.detect_plateaus(points)
        assert plateaus == []

    def test_two_identical_points_plateau(self):
        """Two points with equal voltage spanning full range form a plateau."""
        mod = _import_module()
        points = [
            {"x": 0.0, "voltage_V": 3.5},
            {"x": 1.0, "voltage_V": 3.5},
        ]
        plateaus = mod.detect_plateaus(points)
        assert len(plateaus) == 1
        assert plateaus[0]["voltage_V"] == pytest.approx(3.5)
        assert plateaus[0]["capacity_fraction"] == pytest.approx(1.0)


# ---------------------------------------------------------------------------
# Empty / graceful degradation tests
# ---------------------------------------------------------------------------


class TestEmptyInput:
    """Test that empty or invalid input produces graceful output."""

    def test_empty_list_produces_empty_summary(self):
        """Empty point list yields n_steps=0 and null statistics."""
        mod = _import_module()
        result = mod.summarize_curve([])
        assert result["n_steps"] == 0
        assert result["min_voltage_V"] is None
        assert result["max_voltage_V"] is None
        assert result["avg_voltage_V"] is None
        assert result["plateaus"] == []
        assert result["hysteresis_proxy_V"] is None

    def test_validate_points_filters_invalid(self):
        """_validate_points skips entries with missing or non-numeric fields."""
        mod = _import_module()
        raw = [
            {"x": 0.0, "voltage_V": 3.5},  # valid
            {"x": "bad", "voltage_V": 3.5},  # non-numeric x
            {"voltage_V": 3.5},  # missing x
            {"x": 0.5},  # missing voltage_V
            42,  # not a dict
            {"x": 1.0, "voltage_V": 3.5},  # valid
        ]
        valid = mod._validate_points(raw)
        assert len(valid) == 2
        assert valid[0]["x"] == 0.0
        assert valid[1]["x"] == 1.0

    def test_validate_points_filters_nan_inf(self):
        """_validate_points skips entries with NaN or Inf values."""
        mod = _import_module()
        raw = [
            {"x": 0.0, "voltage_V": float("nan")},
            {"x": float("inf"), "voltage_V": 3.5},
            {"x": 0.5, "voltage_V": 3.5},  # valid
        ]
        valid = mod._validate_points(raw)
        assert len(valid) == 1
        assert valid[0]["x"] == 0.5

    def test_validate_points_sorts_by_x(self):
        """_validate_points returns points sorted by x."""
        mod = _import_module()
        raw = [
            {"x": 0.8, "voltage_V": 3.0},
            {"x": 0.2, "voltage_V": 3.5},
            {"x": 0.5, "voltage_V": 3.3},
        ]
        valid = mod._validate_points(raw)
        xs = [p["x"] for p in valid]
        assert xs == sorted(xs)


# ---------------------------------------------------------------------------
# CLI subprocess tests
# ---------------------------------------------------------------------------


class TestVoltageCurveCLI:
    """Test the voltage_curve_summarizer.py CLI via subprocess."""

    def test_cli_json_output(self):
        """CLI with --json produces valid JSON on stdout."""
        proc = subprocess.run(
            [sys.executable, str(_SCRIPT), "--input", str(_FIXTURE_CURVE), "--json"],
            capture_output=True,
            text=True,
            timeout=30,
        )
        assert proc.returncode == 0, f"stderr: {proc.stderr}"
        output = json.loads(proc.stdout)
        assert output["n_steps"] == 21
        assert output["min_voltage_V"] is not None
        assert output["max_voltage_V"] is not None

    def test_cli_missing_input_file_exits_nonzero(self):
        """CLI exits with code 1 when input file does not exist."""
        proc = subprocess.run(
            [sys.executable, str(_SCRIPT), "--input", "/nonexistent/path.json"],
            capture_output=True,
            text=True,
            timeout=30,
        )
        assert proc.returncode == 1
        assert "ERROR" in proc.stderr

    def test_cli_empty_array_input(self, tmp_path):
        """CLI with an empty array input produces graceful output."""
        empty_file = tmp_path / "empty.json"
        empty_file.write_text("[]", encoding="utf-8")
        proc = subprocess.run(
            [sys.executable, str(_SCRIPT), "--input", str(empty_file), "--json"],
            capture_output=True,
            text=True,
            timeout=30,
        )
        assert proc.returncode == 0, f"stderr: {proc.stderr}"
        output = json.loads(proc.stdout)
        assert output["n_steps"] == 0
        assert output["min_voltage_V"] is None

    def test_cli_output_to_file(self, tmp_path):
        """CLI --out writes output to the specified file."""
        out_file = tmp_path / "result.json"
        proc = subprocess.run(
            [
                sys.executable,
                str(_SCRIPT),
                "--input",
                str(_FIXTURE_CURVE),
                "--out",
                str(out_file),
            ],
            capture_output=True,
            text=True,
            timeout=30,
        )
        assert proc.returncode == 0, f"stderr: {proc.stderr}"
        assert out_file.exists()
        output = json.loads(out_file.read_text(encoding="utf-8"))
        assert output["n_steps"] == 21
