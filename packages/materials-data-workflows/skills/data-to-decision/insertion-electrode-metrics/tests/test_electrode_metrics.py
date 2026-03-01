"""Tests for electrode_metrics.py -- electrode performance metric computation.

Tests the ``compute_metrics`` function directly and the CLI via subprocess.
Validates computed values against fixture data, and verifies that missing
fields produce null values in the output.

Traces: R-SKL-011, R-TEST-002, R-TEST-003, R-ERR-005
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
_SCRIPT = _SCRIPTS_DIR / "electrode_metrics.py"
_FIXTURE_DOC = _FIXTURES_DIR / "electrode_doc.json"


# ---------------------------------------------------------------------------
# Fixture helpers
# ---------------------------------------------------------------------------


@pytest.fixture()
def electrode_doc() -> dict:
    """Load the electrode_doc.json fixture."""
    return json.loads(_FIXTURE_DOC.read_text(encoding="utf-8"))


# ---------------------------------------------------------------------------
# Direct function tests (import compute_metrics)
# ---------------------------------------------------------------------------

# We import the function dynamically since the script is not installed as a
# package.  Using importlib avoids sys.path manipulation at module level.

def _import_compute_metrics():
    """Import ``compute_metrics`` from the electrode_metrics script."""
    import importlib.util

    spec = importlib.util.spec_from_file_location("electrode_metrics", _SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.compute_metrics


class TestComputeMetrics:
    """Test ``compute_metrics`` with the electrode_doc fixture."""

    def test_material_id_propagated(self, electrode_doc):
        """material_id from input appears in output."""
        compute = _import_compute_metrics()
        result = compute(electrode_doc)
        assert result["material_id"] == "mp-19017"

    def test_working_ion_propagated(self, electrode_doc):
        """working_ion from input appears in output."""
        compute = _import_compute_metrics()
        result = compute(electrode_doc)
        assert result["working_ion"] == "Li"

    def test_avg_voltage_matches_fixture(self, electrode_doc):
        """avg_voltage_V matches the fixture average_voltage."""
        compute = _import_compute_metrics()
        result = compute(electrode_doc)
        assert result["avg_voltage_V"] == pytest.approx(3.45)

    def test_grav_capacity_matches_fixture(self, electrode_doc):
        """grav_capacity_mAh_g matches the fixture capacity_grav."""
        compute = _import_compute_metrics()
        result = compute(electrode_doc)
        assert result["grav_capacity_mAh_g"] == pytest.approx(170.0)

    def test_vol_capacity_matches_fixture(self, electrode_doc):
        """vol_capacity_mAh_cm3 matches the fixture capacity_vol."""
        compute = _import_compute_metrics()
        result = compute(electrode_doc)
        assert result["vol_capacity_mAh_cm3"] == pytest.approx(590.0)

    def test_energy_density_computed_correctly(self, electrode_doc):
        """energy_density_Wh_kg equals avg_voltage * capacity_grav."""
        compute = _import_compute_metrics()
        result = compute(electrode_doc)
        expected = 3.45 * 170.0  # 586.5
        assert result["energy_density_Wh_kg"] == pytest.approx(expected)

    def test_stability_flags_present(self, electrode_doc):
        """stability_flags dict is present with expected keys."""
        compute = _import_compute_metrics()
        result = compute(electrode_doc)
        flags = result["stability_flags"]
        assert "stability_charge_eV" in flags
        assert "stability_discharge_eV" in flags
        assert "max_delta_volume_pct" in flags

    def test_stability_flag_values(self, electrode_doc):
        """stability flag values match fixture floats (eV above hull)."""
        compute = _import_compute_metrics()
        result = compute(electrode_doc)
        flags = result["stability_flags"]
        assert flags["stability_charge_eV"] == pytest.approx(0.0)
        assert flags["stability_discharge_eV"] == pytest.approx(0.032)
        assert flags["max_delta_volume_pct"] == pytest.approx(6.5)

    def test_metadata_present(self, electrode_doc):
        """Output includes metadata with script name and version."""
        compute = _import_compute_metrics()
        result = compute(electrode_doc)
        assert result["metadata"]["script"] == "electrode_metrics.py"
        assert "version" in result["metadata"]


class TestComputeMetricsMissingFields:
    """Test that missing optional fields produce null in output."""

    def test_missing_average_voltage_produces_null(self, electrode_doc):
        """Missing average_voltage yields null avg_voltage_V."""
        compute = _import_compute_metrics()
        del electrode_doc["average_voltage"]
        result = compute(electrode_doc)
        assert result["avg_voltage_V"] is None

    def test_missing_capacity_grav_produces_null(self, electrode_doc):
        """Missing capacity_grav yields null grav_capacity_mAh_g."""
        compute = _import_compute_metrics()
        del electrode_doc["capacity_grav"]
        result = compute(electrode_doc)
        assert result["grav_capacity_mAh_g"] is None

    def test_missing_capacity_vol_produces_null(self, electrode_doc):
        """Missing capacity_vol yields null vol_capacity_mAh_cm3."""
        compute = _import_compute_metrics()
        del electrode_doc["capacity_vol"]
        result = compute(electrode_doc)
        assert result["vol_capacity_mAh_cm3"] is None

    def test_missing_voltage_nulls_energy_density(self, electrode_doc):
        """Missing average_voltage prevents energy_density computation."""
        compute = _import_compute_metrics()
        del electrode_doc["average_voltage"]
        result = compute(electrode_doc)
        assert result["energy_density_Wh_kg"] is None

    def test_missing_capacity_nulls_energy_density(self, electrode_doc):
        """Missing capacity_grav prevents energy_density computation."""
        compute = _import_compute_metrics()
        del electrode_doc["capacity_grav"]
        result = compute(electrode_doc)
        assert result["energy_density_Wh_kg"] is None

    def test_missing_stability_fields_produce_null(self, electrode_doc):
        """Missing stability fields yield null in stability_flags."""
        compute = _import_compute_metrics()
        del electrode_doc["stability_charge"]
        del electrode_doc["stability_discharge"]
        del electrode_doc["max_delta_volume"]
        result = compute(electrode_doc)
        flags = result["stability_flags"]
        assert flags["stability_charge_eV"] is None
        assert flags["stability_discharge_eV"] is None
        assert flags["max_delta_volume_pct"] is None


# ---------------------------------------------------------------------------
# CLI subprocess tests
# ---------------------------------------------------------------------------


class TestElectrodeMetricsCLI:
    """Test the electrode_metrics.py CLI via subprocess."""

    def test_cli_json_output(self):
        """CLI with --json produces valid JSON on stdout."""
        proc = subprocess.run(
            [sys.executable, str(_SCRIPT), "--input", str(_FIXTURE_DOC), "--json"],
            capture_output=True,
            text=True,
            timeout=30,
        )
        assert proc.returncode == 0, f"stderr: {proc.stderr}"
        output = json.loads(proc.stdout)
        assert output["material_id"] == "mp-19017"
        assert output["avg_voltage_V"] == pytest.approx(3.45)

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

    def test_cli_output_to_file(self, tmp_path):
        """CLI --out writes output to the specified file."""
        out_file = tmp_path / "result.json"
        proc = subprocess.run(
            [
                sys.executable,
                str(_SCRIPT),
                "--input",
                str(_FIXTURE_DOC),
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
        assert output["material_id"] == "mp-19017"
