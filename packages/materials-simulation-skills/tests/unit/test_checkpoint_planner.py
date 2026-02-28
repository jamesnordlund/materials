import unittest

from tests.unit._utils import load_module


class TestCheckpointPlanner(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.mod = load_module(
            "checkpoint_planner",
            "skills/core-numerical/time-stepping/scripts/checkpoint_planner.py",
        )

    def test_cap_method(self):
        result = self.mod.compute_interval(
            run_time=36000,
            checkpoint_cost=120,
            max_lost_time=1800,
            mtbf=None,
        )
        self.assertEqual(result["method"], "cap")
        self.assertGreater(result["checkpoint_interval"], 0)

    def test_daly_method(self):
        result = self.mod.compute_interval(
            run_time=36000,
            checkpoint_cost=120,
            max_lost_time=3600,
            mtbf=72000,
            formula="daly",
        )
        self.assertEqual(result["method"], "daly")

    def test_invalid_inputs(self):
        with self.assertRaises(ValueError):
            self.mod.compute_interval(
                run_time=0,
                checkpoint_cost=1,
                max_lost_time=1,
                mtbf=None,
            )

    def test_daly_mtbf_equal_checkpoint_cost_raises(self):
        with self.assertRaises(ValueError) as ctx:
            self.mod.compute_interval(
                run_time=36000,
                checkpoint_cost=100,
                max_lost_time=3600,
                mtbf=100,
                formula="daly",
            )
        self.assertIn("mtbf must be greater than checkpoint_cost", str(ctx.exception))

    def test_daly_mtbf_less_than_checkpoint_cost_raises(self):
        with self.assertRaises(ValueError) as ctx:
            self.mod.compute_interval(
                run_time=36000,
                checkpoint_cost=200,
                max_lost_time=3600,
                mtbf=100,
                formula="daly",
            )
        self.assertIn("mtbf must be greater than checkpoint_cost", str(ctx.exception))

    def test_daly_mtbf_slightly_above_checkpoint_cost_succeeds(self):
        result = self.mod.compute_interval(
            run_time=36000,
            checkpoint_cost=100,
            max_lost_time=3600,
            mtbf=101,
            formula="daly",
        )
        self.assertEqual(result["method"], "daly")
        self.assertGreater(result["checkpoint_interval"], 0)


if __name__ == "__main__":
    unittest.main()
