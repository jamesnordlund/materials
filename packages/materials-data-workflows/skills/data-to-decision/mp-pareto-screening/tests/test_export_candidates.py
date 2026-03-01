"""Tests for export_candidates.py CLI script."""

from __future__ import annotations

import csv
import json
import subprocess
import sys
from pathlib import Path

SCRIPT = str(
    Path(__file__).resolve().parent.parent / "scripts" / "export_candidates.py"
)


def _run(args: list[str], *, check: bool = False) -> subprocess.CompletedProcess[str]:
    """Invoke export_candidates.py in a subprocess."""
    return subprocess.run(
        [sys.executable, SCRIPT, *args],
        capture_output=True,
        text=True,
        check=check,
        timeout=30,
    )


def _make_pareto_output(frontier: list[dict]) -> dict:
    """Build a minimal pareto_frontier.py output structure."""
    return {
        "metadata": {
            "script": "pareto_frontier.py",
            "version": "1.0.0",
            "n_candidates": len(frontier),
            "n_objectives": 2,
            "n_constraints": 0,
            "n_after_constraints": len(frontier),
            "n_frontier": len(frontier),
        },
        "objectives": [
            {"field": "energy_above_hull_eV", "direction": "min"},
            {"field": "band_gap_eV", "direction": "max"},
        ],
        "constraints_applied": [],
        "frontier": frontier,
        "dominated": [],
        "scores": {},
    }


SAMPLE_FRONTIER = [
    {
        "material_id": "mp-P3",
        "energy_above_hull_eV": 0.03,
        "band_gap_eV": 3.5,
        "rank": 1,
        "dominated_count": 5,
    },
    {
        "material_id": "mp-P1",
        "energy_above_hull_eV": 0.01,
        "band_gap_eV": 3.0,
        "rank": 1,
        "dominated_count": 4,
    },
    {
        "material_id": "mp-P2",
        "energy_above_hull_eV": 0.005,
        "band_gap_eV": 2.0,
        "rank": 1,
        "dominated_count": 3,
    },
]


# ------------------------------------------------------------------
# CSV export
# ------------------------------------------------------------------

class TestCsvExport:
    """Test CSV output correctness."""

    def test_csv_has_sorted_headers(self, tmp_path: Path) -> None:
        """CSV columns must be sorted alphabetically."""
        input_path = tmp_path / "frontier_input.json"
        input_path.write_text(
            json.dumps(_make_pareto_output(SAMPLE_FRONTIER)),
            encoding="utf-8",
        )

        out_path = tmp_path / "output.csv"
        result = _run([
            "--input", str(input_path),
            "--format", "csv",
            "--out", str(out_path),
        ])
        assert result.returncode == 0, f"Script failed:\n{result.stderr}"

        with open(out_path, encoding="utf-8", newline="") as fh:
            reader = csv.reader(fh)
            headers = next(reader)

        expected_headers = sorted(SAMPLE_FRONTIER[0].keys())
        assert headers == expected_headers

    def test_csv_rows_sorted_by_rank(self, tmp_path: Path) -> None:
        """CSV rows must be sorted by rank (ascending), preserving original order as tiebreaker."""
        # Give candidates different ranks to test sorting
        frontier = [
            {
                "material_id": "mp-C",
                "energy_above_hull_eV": 0.05,
                "band_gap_eV": 2.5,
                "rank": 2,
                "dominated_count": 1,
            },
            {
                "material_id": "mp-A",
                "energy_above_hull_eV": 0.01,
                "band_gap_eV": 3.0,
                "rank": 1,
                "dominated_count": 5,
            },
            {
                "material_id": "mp-B",
                "energy_above_hull_eV": 0.03,
                "band_gap_eV": 3.5,
                "rank": 1,
                "dominated_count": 4,
            },
        ]

        input_path = tmp_path / "frontier_input.json"
        input_path.write_text(
            json.dumps(_make_pareto_output(frontier)),
            encoding="utf-8",
        )

        out_path = tmp_path / "output.csv"
        result = _run([
            "--input", str(input_path),
            "--format", "csv",
            "--out", str(out_path),
        ])
        assert result.returncode == 0

        with open(out_path, encoding="utf-8", newline="") as fh:
            reader = csv.DictReader(fh)
            rows = list(reader)

        material_ids = [r["material_id"] for r in rows]
        # rank=1 candidates first (mp-A, mp-B in original order), then rank=2 (mp-C)
        assert material_ids == ["mp-A", "mp-B", "mp-C"]


# ------------------------------------------------------------------
# JSON export
# ------------------------------------------------------------------

class TestJsonExport:
    """Test JSON output correctness."""

    def test_json_has_deterministic_key_ordering(self, tmp_path: Path) -> None:
        """JSON output must have keys sorted alphabetically."""
        input_path = tmp_path / "frontier_input.json"
        input_path.write_text(
            json.dumps(_make_pareto_output(SAMPLE_FRONTIER)),
            encoding="utf-8",
        )

        out_path = tmp_path / "output.json"
        result = _run([
            "--input", str(input_path),
            "--format", "json",
            "--out", str(out_path),
        ])
        assert result.returncode == 0, f"Script failed:\n{result.stderr}"

        raw = out_path.read_text(encoding="utf-8")
        records = json.loads(raw)
        assert isinstance(records, list)
        assert len(records) == len(SAMPLE_FRONTIER)

        # Verify keys are sorted in the raw JSON string
        for record in records:
            keys = list(record.keys())
            assert keys == sorted(keys), (
                f"Keys not sorted: {keys}"
            )


# ------------------------------------------------------------------
# --json flag to stdout
# ------------------------------------------------------------------

class TestJsonFlag:
    """Test the --json flag emits valid JSON status to stdout."""

    def test_json_flag_emits_valid_json_to_stdout(self, tmp_path: Path) -> None:
        """The --json flag should emit a status object to stdout."""
        input_path = tmp_path / "frontier_input.json"
        input_path.write_text(
            json.dumps(_make_pareto_output(SAMPLE_FRONTIER)),
            encoding="utf-8",
        )

        out_path = tmp_path / "output.csv"
        result = _run([
            "--input", str(input_path),
            "--format", "csv",
            "--out", str(out_path),
            "--json",
        ])
        assert result.returncode == 0, f"Script failed:\n{result.stderr}"

        # stdout should be valid JSON
        status = json.loads(result.stdout)
        assert status["status"] == "ok"
        assert status["rows"] == len(SAMPLE_FRONTIER)
        assert status["path"] == str(out_path)
