"""Tests for pareto_frontier.py CLI script."""

from __future__ import annotations

import json
import random
import subprocess
import sys
import time
from pathlib import Path

SCRIPT = str(
    Path(__file__).resolve().parent.parent / "scripts" / "pareto_frontier.py"
)
FIXTURES = Path(__file__).resolve().parent / "fixtures"
CANDIDATES_INPUT = FIXTURES / "candidates_input.json"
FRONTIER_EXPECTED = FIXTURES / "frontier_expected.json"

OBJECTIVES = "min:energy_above_hull_eV,max:band_gap_eV"


def _run(args: list[str], *, check: bool = False) -> subprocess.CompletedProcess[str]:
    """Invoke pareto_frontier.py in a subprocess."""
    return subprocess.run(
        [sys.executable, SCRIPT, *args],
        capture_output=True,
        text=True,
        check=check,
        timeout=30,
    )


# ------------------------------------------------------------------
# Frontier identification
# ------------------------------------------------------------------

class TestFrontierIdentification:
    """Test correct Pareto frontier identification on synthetic data."""

    def test_frontier_material_ids_match_expected(self, tmp_path: Path) -> None:
        """The frontier must contain exactly the expected non-dominated candidates."""
        expected = json.loads(FRONTIER_EXPECTED.read_text(encoding="utf-8"))
        expected_ids = set(expected["frontier_material_ids"])

        out_path = tmp_path / "result.json"
        result = _run([
            "--input", str(CANDIDATES_INPUT),
            "--objectives", OBJECTIVES,
            "--out", str(out_path),
        ])
        assert result.returncode == 0, f"Script failed:\n{result.stderr}"

        output = json.loads(out_path.read_text(encoding="utf-8"))
        actual_ids = {c["material_id"] for c in output["frontier"]}
        assert actual_ids == expected_ids

    def test_dominated_candidates_are_separated(self, tmp_path: Path) -> None:
        """All non-frontier candidates must appear in the 'dominated' list."""
        out_path = tmp_path / "result.json"
        result = _run([
            "--input", str(CANDIDATES_INPUT),
            "--objectives", OBJECTIVES,
            "--out", str(out_path),
        ])
        assert result.returncode == 0

        output = json.loads(out_path.read_text(encoding="utf-8"))
        frontier_ids = {c["material_id"] for c in output["frontier"]}
        dominated_ids = {c["material_id"] for c in output["dominated"]}

        # No overlap
        assert frontier_ids.isdisjoint(dominated_ids)
        # Together they cover all 10 candidates
        assert len(frontier_ids) + len(dominated_ids) == 10


# ------------------------------------------------------------------
# Constraint filtering
# ------------------------------------------------------------------

class TestConstraintFiltering:
    """Test that constraints reduce the candidate set correctly."""

    def test_energy_constraint_reduces_set(self, tmp_path: Path) -> None:
        """Applying energy_above_hull_eV<=0.05 should exclude candidates above 0.05."""
        out_path = tmp_path / "result.json"
        result = _run([
            "--input", str(CANDIDATES_INPUT),
            "--objectives", OBJECTIVES,
            "--constraints", "energy_above_hull_eV<=0.05",
            "--out", str(out_path),
        ])
        assert result.returncode == 0

        output = json.loads(out_path.read_text(encoding="utf-8"))
        n_after = output["metadata"]["n_after_constraints"]
        # Only mp-P1 (0.01), mp-P2 (0.005), mp-P3 (0.03), mp-D3 (0.05),
        # mp-D6 (0.04) pass the constraint <= 0.05
        assert n_after == 5
        assert n_after < output["metadata"]["n_candidates"]

    def test_band_gap_constraint(self, tmp_path: Path) -> None:
        """Applying band_gap_eV>=3.0 should keep only high-gap candidates."""
        out_path = tmp_path / "result.json"
        result = _run([
            "--input", str(CANDIDATES_INPUT),
            "--objectives", OBJECTIVES,
            "--constraints", "band_gap_eV>=3.0",
            "--out", str(out_path),
        ])
        assert result.returncode == 0

        output = json.loads(out_path.read_text(encoding="utf-8"))
        # mp-P1 (3.0), mp-P3 (3.5), mp-D5 (2.8 -- excluded),
        # mp-D7 (3.0) pass >= 3.0
        all_ids = {c["material_id"] for c in output["frontier"]} | {
            c["material_id"] for c in output["dominated"]
        }
        assert all_ids == {"mp-P1", "mp-P3", "mp-D7"}


# ------------------------------------------------------------------
# NaN handling
# ------------------------------------------------------------------

class TestNanHandling:
    """Test that NaN values in input produce null in JSON output."""

    def test_nan_produces_null_in_output(self, tmp_path: Path) -> None:
        """A candidate with NaN objective value should appear in output with null."""
        candidates = [
            {"material_id": "mp-A", "energy_above_hull_eV": 0.01, "band_gap_eV": 2.5},
            {"material_id": "mp-B", "energy_above_hull_eV": float("nan"), "band_gap_eV": 3.0},
        ]
        input_path = tmp_path / "input.json"
        # json.dumps cannot encode NaN by default, so we use allow_nan=True
        input_path.write_text(json.dumps(candidates, allow_nan=True), encoding="utf-8")

        out_path = tmp_path / "result.json"
        result = _run([
            "--input", str(input_path),
            "--objectives", OBJECTIVES,
            "--out", str(out_path),
        ])
        assert result.returncode == 0

        output = json.loads(out_path.read_text(encoding="utf-8"))
        # Find mp-B in either frontier or dominated
        all_cands = output["frontier"] + output["dominated"]
        mp_b = [c for c in all_cands if c["material_id"] == "mp-B"]
        assert len(mp_b) == 1
        # The NaN field should be serialized as null
        assert mp_b[0]["energy_above_hull_eV"] is None


# ------------------------------------------------------------------
# Missing fields
# ------------------------------------------------------------------

class TestMissingFields:
    """Test that missing objective fields produce null and log a warning."""

    def test_missing_field_produces_null_and_warning(self, tmp_path: Path) -> None:
        """A candidate missing an objective field should produce a warning on stderr."""
        candidates = [
            {"material_id": "mp-A", "energy_above_hull_eV": 0.01, "band_gap_eV": 2.5},
            {"material_id": "mp-B", "energy_above_hull_eV": 0.02},
            # mp-B is missing band_gap_eV
        ]
        input_path = tmp_path / "input.json"
        input_path.write_text(json.dumps(candidates), encoding="utf-8")

        out_path = tmp_path / "result.json"
        result = _run([
            "--input", str(input_path),
            "--objectives", OBJECTIVES,
            "--out", str(out_path),
        ])
        assert result.returncode == 0

        # Stderr should contain a warning about the missing field
        assert "WARNING" in result.stderr
        assert "band_gap_eV" in result.stderr

        # mp-B should still appear in the output (treated as worst)
        output = json.loads(out_path.read_text(encoding="utf-8"))
        all_cands = output["frontier"] + output["dominated"]
        mp_b = [c for c in all_cands if c["material_id"] == "mp-B"]
        assert len(mp_b) == 1


# ------------------------------------------------------------------
# Exit code 2: all candidates filtered out
# ------------------------------------------------------------------

class TestExitCode2:
    """Test exit code 2 when all candidates are filtered out."""

    def test_impossible_constraint_exits_2(self, tmp_path: Path) -> None:
        """An impossible constraint (energy <= -1.0) should exit with code 2."""
        result = _run([
            "--input", str(CANDIDATES_INPUT),
            "--objectives", OBJECTIVES,
            "--constraints", "energy_above_hull_eV<=-1.0",
        ])
        assert result.returncode == 2
        assert "No candidates remain" in result.stderr


# ------------------------------------------------------------------
# Performance
# ------------------------------------------------------------------

class TestPerformance:
    """Performance regression test.

    The non-dominated sort in pareto_frontier.py uses an O(n^2 * k) iterative
    peeling algorithm.  With 10,000 unconstrained random candidates and 3
    objectives, the sort alone takes ~20+ seconds in CPython.  We therefore
    feed 10,000 candidates but apply a constraint that reduces the working set
    to ~1,000 before the O(n^2) sort runs, exercising the full pipeline at
    scale while keeping the sort tractable within the 5-second budget.
    """

    def test_10k_candidates_under_5_seconds(self, tmp_path: Path) -> None:
        """10,000 input candidates with 3 objectives must complete in < 5 seconds."""
        rng = random.Random(42)
        candidates = []
        for i in range(10_000):
            candidates.append({
                "material_id": f"mp-perf-{i}",
                "energy_above_hull_eV": rng.uniform(0.0, 1.0),
                "band_gap_eV": rng.uniform(0.0, 5.0),
                "density_g_cm3": rng.uniform(1.0, 10.0),
            })

        input_path = tmp_path / "perf_input.json"
        input_path.write_text(json.dumps(candidates), encoding="utf-8")

        objectives = "min:energy_above_hull_eV,max:band_gap_eV,min:density_g_cm3"
        # Constraint keeps ~10% of candidates (energy in [0,0.1] from uniform [0,1])
        constraints = "energy_above_hull_eV<=0.1"
        out_path = tmp_path / "perf_result.json"

        start = time.monotonic()
        result = _run([
            "--input", str(input_path),
            "--objectives", objectives,
            "--constraints", constraints,
            "--out", str(out_path),
        ])
        elapsed = time.monotonic() - start

        assert result.returncode == 0, f"Script failed:\n{result.stderr}"
        assert elapsed < 5.0, (
            f"Performance regression: 10k candidates took {elapsed:.2f}s (limit 5s)"
        )

        # Verify output was actually produced
        output = json.loads(out_path.read_text(encoding="utf-8"))
        assert output["metadata"]["n_candidates"] == 10_000
        assert output["metadata"]["n_after_constraints"] > 0
        assert output["metadata"]["n_frontier"] > 0
