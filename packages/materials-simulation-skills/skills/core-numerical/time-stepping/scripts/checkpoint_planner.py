#!/usr/bin/env python3
import argparse
import json
import math
import sys
from typing import Dict, Optional


def compute_interval(
    run_time: float,
    checkpoint_cost: float,
    max_lost_time: float,
    mtbf: Optional[float],
    formula: str = "young",
) -> Dict[str, object]:
    if run_time <= 0:
        raise ValueError("run_time must be positive")
    if checkpoint_cost <= 0:
        raise ValueError("checkpoint_cost must be positive")
    if max_lost_time <= 0:
        raise ValueError("max_lost_time must be positive")
    if mtbf is not None and mtbf <= 0:
        raise ValueError("mtbf must be positive")
    if mtbf is not None and formula == "daly" and mtbf <= checkpoint_cost:
        raise ValueError(
            "mtbf must be greater than checkpoint_cost for the Daly formula"
        )
    if formula not in {"young", "daly"}:
        raise ValueError("formula must be 'young' or 'daly'")

    if mtbf is not None:
        if formula == "young":
            # Young (1974): τ = sqrt(2 × δ × MTBF)
            interval = math.sqrt(2.0 * checkpoint_cost * mtbf)
        else:  # daly
            # Daly (2006): τ = sqrt(2 × δ × (MTBF - δ)) + δ
            # Accounts for restart overhead
            interval = math.sqrt(2.0 * checkpoint_cost * (mtbf - checkpoint_cost)) + checkpoint_cost
        method = formula
    else:
        interval = max_lost_time
        method = "cap"

    interval = min(interval, max_lost_time)
    checkpoints = int(math.floor(run_time / interval))
    overhead_fraction = (checkpoints * checkpoint_cost) / run_time

    return {
        "checkpoint_interval": interval,
        "checkpoints": checkpoints,
        "overhead_fraction": overhead_fraction,
        "method": method,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Plan checkpoint cadence for long runs.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("--run-time", type=float, required=True, help="Total run time (s)")
    parser.add_argument(
        "--checkpoint-cost",
        type=float,
        required=True,
        help="Checkpoint write cost (s)",
    )
    parser.add_argument(
        "--max-lost-time",
        type=float,
        default=3600,
        help="Maximum acceptable lost time (s)",
    )
    parser.add_argument(
        "--mtbf",
        type=float,
        default=None,
        help="Mean time between failures (s)",
    )
    parser.add_argument(
        "--formula",
        choices=["young", "daly"],
        default="young",
        help="Checkpoint formula: Young (1974) or Daly (2006) refinement",
    )
    parser.add_argument("--json", action="store_true", help="Emit JSON output")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    try:
        result = compute_interval(
            run_time=args.run_time,
            checkpoint_cost=args.checkpoint_cost,
            max_lost_time=args.max_lost_time,
            mtbf=args.mtbf,
            formula=args.formula,
        )
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        sys.exit(2)

    payload = {
        "inputs": {
            "run_time": args.run_time,
            "checkpoint_cost": args.checkpoint_cost,
            "max_lost_time": args.max_lost_time,
            "mtbf": args.mtbf,
            "formula": args.formula,
        },
        "results": result,
    }

    if args.json:
        print(json.dumps(payload, indent=2, sort_keys=True))
        return

    print("Checkpoint plan")
    print(f"  interval: {result['checkpoint_interval']:.6g}")
    print(f"  checkpoints: {result['checkpoints']}")
    print(f"  overhead_fraction: {result['overhead_fraction']:.6g}")
    print(f"  method: {result['method']}")


if __name__ == "__main__":
    main()
