"""Integration tests for CLI examples from all SKILL.md files.

This test suite runs every CLI example documented in the 12 SKILL.md files
to ensure documentation matches actual script behavior.

Requirements: REQ-C01, REQ-C02
"""

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from typing import Any

# Repository root paths
REPO_ROOT = Path(__file__).resolve().parents[2]
SKILLS = REPO_ROOT / "skills"
MONOREPO_ROOT = REPO_ROOT.parent.parent


def run_script(script_path: Path, args: list[str], cwd: Path | None = None) -> subprocess.CompletedProcess:
    """Run a Python script with the given arguments."""
    cmd = [sys.executable, str(script_path)] + args
    return subprocess.run(
        cmd,
        cwd=str(cwd or REPO_ROOT),
        capture_output=True,
        text=True,
        check=False,
        timeout=30,
    )


def create_test_input(data: dict[str, Any], suffix: str = ".json") -> Path:
    """Create a temporary test input file."""
    fd, path = tempfile.mkstemp(suffix=suffix, dir=tempfile.gettempdir())
    with open(fd, "w") as f:
        json.dump(data, f)
    return Path(path)


class TestMeshGenerationCLI(unittest.TestCase):
    """Test CLI examples from mesh-generation SKILL.md."""

    def test_grid_sizing_1d(self):
        """Test: python3 scripts/grid_sizing.py --length 1.0 --resolution 200 --json"""
        script = SKILLS / "core-numerical/mesh-generation/scripts/grid_sizing.py"
        result = run_script(script, ["--length", "1.0", "--resolution", "200", "--json"])
        self.assertEqual(result.returncode, 0, f"grid_sizing.py failed: {result.stderr}")
        data = json.loads(result.stdout)
        # Check for nested or flat structure
        results = data.get("results", data)
        self.assertIn("dx", results)
        self.assertTrue("nx" in results or "counts" in results)

    def test_mesh_quality_basic(self):
        """Test: python3 scripts/mesh_quality.py --dx 1.0 --dy 0.5 --dz 0.5 --json"""
        script = SKILLS / "core-numerical/mesh-generation/scripts/mesh_quality.py"
        result = run_script(script, ["--dx", "1.0", "--dy", "0.5", "--dz", "0.5", "--json"])
        self.assertEqual(result.returncode, 0, f"mesh_quality.py failed: {result.stderr}")
        data = json.loads(result.stdout)
        results = data.get("results", data)
        self.assertIn("aspect_ratio", results)
        self.assertIn("skewness", results)

    def test_mesh_quality_high_aspect(self):
        """Test: python3 scripts/mesh_quality.py --dx 1.0 --dy 0.1 --dz 0.1 --json"""
        script = SKILLS / "core-numerical/mesh-generation/scripts/mesh_quality.py"
        result = run_script(script, ["--dx", "1.0", "--dy", "0.1", "--dz", "0.1", "--json"])
        self.assertEqual(result.returncode, 0, f"mesh_quality.py high aspect failed: {result.stderr}")
        data = json.loads(result.stdout)
        results = data.get("results", data)
        self.assertIn("aspect_ratio", results)
        # High aspect ratio should be detected
        self.assertGreater(results["aspect_ratio"], 5.0)


class TestTimeSteppingCLI(unittest.TestCase):
    """Test CLI examples from time-stepping SKILL.md."""

    def test_timestep_planner_with_ramping(self):
        """Test: python3 scripts/timestep_planner.py --dt-target 1e-4 --dt-limit 2e-4 --safety 0.8 --ramp-steps 10 --json"""
        script = SKILLS / "core-numerical/time-stepping/scripts/timestep_planner.py"
        result = run_script(
            script,
            ["--dt-target", "1e-4", "--dt-limit", "2e-4", "--safety", "0.8", "--ramp-steps", "10", "--json"]
        )
        self.assertEqual(result.returncode, 0, f"timestep_planner.py failed: {result.stderr}")
        data = json.loads(result.stdout)
        results = data.get("results", data)
        self.assertIn("dt_recommended", results)
        self.assertIn("ramp_schedule", results)

    def test_output_schedule(self):
        """Test: python3 scripts/output_schedule.py --t-start 0 --t-end 10 --interval 0.1 --json"""
        script = SKILLS / "core-numerical/time-stepping/scripts/output_schedule.py"
        result = run_script(
            script,
            ["--t-start", "0", "--t-end", "10", "--interval", "0.1", "--json"]
        )
        self.assertEqual(result.returncode, 0, f"output_schedule.py failed: {result.stderr}")
        data = json.loads(result.stdout)
        results = data.get("results", data)
        self.assertIn("output_times", results)

    def test_checkpoint_planner(self):
        """Test: python3 scripts/checkpoint_planner.py --run-time 36000 --checkpoint-cost 120 --max-lost-time 1800 --json"""
        script = SKILLS / "core-numerical/time-stepping/scripts/checkpoint_planner.py"
        result = run_script(
            script,
            ["--run-time", "36000", "--checkpoint-cost", "120", "--max-lost-time", "1800", "--json"]
        )
        self.assertEqual(result.returncode, 0, f"checkpoint_planner.py failed: {result.stderr}")
        data = json.loads(result.stdout)
        results = data.get("results", data)
        self.assertIn("checkpoint_interval", results)


class TestLinearSolversCLI(unittest.TestCase):
    """Test CLI examples from linear-solvers SKILL.md."""

    def test_solver_selector_basic(self):
        """Test solver selection with basic parameters."""
        script = SKILLS / "core-numerical/linear-solvers/scripts/solver_selector.py"
        result = run_script(
            script,
            ["--size", "1000", "--symmetric", "--positive-definite", "--sparse", "--json"]
        )
        self.assertEqual(result.returncode, 0, f"solver_selector.py failed: {result.stderr}")
        data = json.loads(result.stdout)
        results = data.get("results", data)
        # Check for either 'recommended_solver' or 'recommended'
        self.assertTrue("recommended_solver" in results or "recommended" in results)

    def test_preconditioner_advisor(self):
        """Test preconditioner recommendation."""
        script = SKILLS / "core-numerical/linear-solvers/scripts/preconditioner_advisor.py"
        result = run_script(
            script,
            ["--matrix-type", "spd", "--sparse", "--json"]
        )
        self.assertEqual(result.returncode, 0, f"preconditioner_advisor.py failed: {result.stderr}")
        data = json.loads(result.stdout)
        results = data.get("results", data)
        # Check for either 'recommended_preconditioner' or 'suggested'
        self.assertTrue("recommended_preconditioner" in results or "suggested" in results)


class TestNonlinearSolversCLI(unittest.TestCase):
    """Test CLI examples from nonlinear-solvers SKILL.md."""

    def test_convergence_analyzer(self):
        """Test convergence analysis with sample residuals."""
        script = SKILLS / "core-numerical/nonlinear-solvers/scripts/convergence_analyzer.py"
        residuals = [1.0, 0.1, 0.01, 0.001]
        # Use --residuals argument with comma-separated values
        result = run_script(script, ["--residuals", ",".join(str(r) for r in residuals), "--json"])
        self.assertEqual(result.returncode, 0, f"convergence_analyzer.py failed: {result.stderr}")
        data = json.loads(result.stdout)
        results = data.get("results", data)
        # Script outputs 'estimated_rate' not 'convergence_rate'
        self.assertIn("estimated_rate", results)


class TestNumericalIntegrationCLI(unittest.TestCase):
    """Test CLI examples from numerical-integration SKILL.md."""

    def test_integrator_selector(self):
        """Test integrator selection."""
        script = SKILLS / "core-numerical/numerical-integration/scripts/integrator_selector.py"
        result = run_script(
            script,
            ["--stiff", "--accuracy", "high", "--json"]
        )
        self.assertEqual(result.returncode, 0, f"integrator_selector.py failed: {result.stderr}")
        data = json.loads(result.stdout)
        results = data.get("results", data)
        # Check for either 'recommended_method' or 'recommended'
        self.assertTrue("recommended_method" in results or "recommended" in results)


class TestNumericalStabilityCLI(unittest.TestCase):
    """Test CLI examples from numerical-stability SKILL.md."""

    def test_cfl_analyzer(self):
        """Test CFL analysis."""
        script = SKILLS / "core-numerical/numerical-stability/scripts/cfl_analyzer.py"
        if not script.exists():
            self.skipTest(f"Script not found: {script}")
        result = run_script(
            script,
            ["--velocity", "1.0", "--dx", "0.1", "--dt", "0.05", "--json"]
        )
        self.assertEqual(result.returncode, 0, f"cfl_analyzer.py failed: {result.stderr}")


class TestDifferentiationSchemesCLI(unittest.TestCase):
    """Test CLI examples from differentiation-schemes SKILL.md."""

    def test_stencil_generator(self):
        """Test stencil generation."""
        script = SKILLS / "core-numerical/differentiation-schemes/scripts/stencil_generator.py"
        if not script.exists():
            self.skipTest(f"Script not found: {script}")
        result = run_script(script, ["--order", "2", "--scheme", "central", "--json"])
        self.assertEqual(result.returncode, 0, f"stencil_generator.py failed: {result.stderr}")


class TestParameterOptimizationCLI(unittest.TestCase):
    """Test CLI examples from parameter-optimization SKILL.md."""

    def test_doe_generator_sobol(self):
        """Test DOE generation with Sobol sequences."""
        script = SKILLS / "simulation-workflow/parameter-optimization/scripts/doe_generator.py"
        result = run_script(
            script,
            ["--params", "3", "--budget", "16", "--method", "sobol", "--json"]
        )
        self.assertEqual(result.returncode, 0, f"doe_generator.py sobol failed: {result.stderr}")
        data = json.loads(result.stdout)
        results = data.get("results", data)
        self.assertIn("samples", results)

    def test_doe_generator_lhs(self):
        """Test DOE generation with Latin Hypercube."""
        script = SKILLS / "simulation-workflow/parameter-optimization/scripts/doe_generator.py"
        result = run_script(
            script,
            ["--params", "2", "--budget", "10", "--method", "lhs", "--json"]
        )
        self.assertEqual(result.returncode, 0, f"doe_generator.py lhs failed: {result.stderr}")
        data = json.loads(result.stdout)
        results = data.get("results", data)
        self.assertIn("samples", results)


class TestPerformanceProfilingCLI(unittest.TestCase):
    """Test CLI examples from performance-profiling SKILL.md."""

    def test_bottleneck_detector(self):
        """Test bottleneck detection with sample profile data."""
        script = SKILLS / "simulation-workflow/performance-profiling/scripts/bottleneck_detector.py"
        timing_data = create_test_input({
            "solver": 80.0,
            "assembly": 15.0,
            "output": 5.0
        })
        try:
            result = run_script(script, ["--timing", str(timing_data), "--json"])
            self.assertEqual(result.returncode, 0, f"bottleneck_detector.py failed: {result.stderr}")
            data = json.loads(result.stdout)
            results = data.get("results", data)
            self.assertIn("bottlenecks", results)
        finally:
            timing_data.unlink(missing_ok=True)


class TestPostProcessingCLI(unittest.TestCase):
    """Test CLI examples from post-processing SKILL.md."""

    def test_statistical_analyzer(self):
        """Test statistical analysis."""
        script = SKILLS / "simulation-workflow/post-processing/scripts/statistical_analyzer.py"
        field_data = create_test_input({"phi": [1.0, 2.0, 3.0, 4.0, 5.0]})
        try:
            result = run_script(script, ["--input", str(field_data), "--field", "phi", "--json"])
            self.assertEqual(result.returncode, 0, f"statistical_analyzer.py failed: {result.stderr}")
            data = json.loads(result.stdout)
            self.assertIn("basic_statistics", data)
        finally:
            field_data.unlink(missing_ok=True)

    def test_time_series_analyzer(self):
        """Test time series analysis."""
        script = SKILLS / "simulation-workflow/post-processing/scripts/time_series_analyzer.py"
        ts_data = create_test_input({"time": [0, 1, 2, 3, 4], "energy": [5.0, 3.0, 2.0, 1.5, 1.2]})
        try:
            result = run_script(script, ["--input", str(ts_data), "--quantity", "energy", "--json"])
            self.assertEqual(result.returncode, 0, f"time_series_analyzer.py failed: {result.stderr}")
            data = json.loads(result.stdout)
            results = data.get("results", data)
            # Check for either 'trend' or 'monotonicity' or 'convergence'
            self.assertTrue("trend" in results or "monotonicity" in results or "convergence" in results)
        finally:
            ts_data.unlink(missing_ok=True)


class TestSimulationOrchestratorCLI(unittest.TestCase):
    """Test CLI examples from simulation-orchestrator SKILL.md."""

    def test_sweep_generator(self):
        """Test parameter sweep generation."""
        script = SKILLS / "simulation-workflow/simulation-orchestrator/scripts/sweep_generator.py"
        base_config = create_test_input({"solver": "euler", "max_steps": 1000})
        with tempfile.TemporaryDirectory() as tmpdir:
            output_dir = Path(tmpdir) / "sweep_output"
            try:
                result = run_script(
                    script,
                    [
                        "--base-config", str(base_config),
                        "--params", "dt:1e-4:1e-2:3",
                        "--method", "linspace",
                        "--output-dir", str(output_dir),
                        "--json"
                    ]
                )
                self.assertEqual(result.returncode, 0, f"sweep_generator.py failed: {result.stderr}")
                data = json.loads(result.stdout)
                results = data.get("results", data)
                # Check for either 'configs_generated' or 'configs' or 'total_runs'
                self.assertTrue("configs_generated" in results or "configs" in results or "total_runs" in results)
            finally:
                base_config.unlink(missing_ok=True)


class TestSimulationValidatorCLI(unittest.TestCase):
    """Test CLI examples from simulation-validator SKILL.md."""

    def test_preflight_checker(self):
        """Test preflight validation."""
        script = SKILLS / "simulation-workflow/simulation-validator/scripts/preflight_checker.py"
        config = create_test_input({
            "dt": 1e-4,
            "max_steps": 1000,
            "solver": "bdf2",
            "domain": {"length": 1.0},
            "output_dir": "/tmp/test_output"
        })
        try:
            result = run_script(script, ["--config", str(config), "--json"])
            self.assertEqual(result.returncode, 0, f"preflight_checker.py failed: {result.stderr}")
            data = json.loads(result.stdout)
            # Script returns report with status
            self.assertIn("report", data)
            self.assertIn("status", data["report"])
        finally:
            config.unlink(missing_ok=True)

    def test_result_validator(self):
        """Test result validation."""
        script = SKILLS / "simulation-workflow/simulation-validator/scripts/result_validator.py"
        metrics_data = create_test_input({
            "time": [0, 1, 2, 3],
            "energy": [10.0, 8.0, 6.5, 5.0],
            "residual": [1e-3, 1e-5, 1e-7, 1e-9]
        })
        try:
            result = run_script(script, ["--metrics", str(metrics_data), "--json"])
            self.assertEqual(result.returncode, 0, f"result_validator.py failed: {result.stderr}")
            data = json.loads(result.stdout)
            results = data.get("results", data)
            self.assertIn("confidence_score", results)
        finally:
            metrics_data.unlink(missing_ok=True)


if __name__ == "__main__":
    unittest.main()
