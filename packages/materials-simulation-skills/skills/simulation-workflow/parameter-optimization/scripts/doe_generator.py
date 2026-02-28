#!/usr/bin/env python3
import argparse
import json
import random
import sys

from scipy.stats import qmc


def lhs_samples(dim: int, budget: int, seed: int) -> list[list[float]]:
    rng = random.Random(seed)
    samples = []
    for d in range(dim):
        points = [(i + rng.random()) / budget for i in range(budget)]
        rng.shuffle(points)
        if d == 0:
            samples = [[p] for p in points]
        else:
            for i, p in enumerate(points):
                samples[i].append(p)
    return samples


def sobol_samples(dim: int, budget: int, seed: int) -> list[list[float]]:
    """Generate Sobol quasi-random samples using scipy.stats.qmc.Sobol.

    Sobol sequences require a power-of-2 number of samples for optimal properties.
    This function generates the next power of 2 >= budget, then truncates.

    Reference: Sobol, I. M. (1967). "On the distribution of points in a cube and
    the approximate evaluation of integrals." USSR Computational Mathematics and
    Mathematical Physics 7(4): 86–112.
    """
    # Compute next power of 2 >= budget
    n_pow2 = 1
    while n_pow2 < budget:
        n_pow2 *= 2

    # Generate scrambled Sobol sequence with seed
    sampler = qmc.Sobol(d=dim, scramble=True, seed=seed)
    samples_array = sampler.random(n=n_pow2)

    # Truncate to requested budget
    samples_array = samples_array[:budget]

    # Convert to list of lists
    return samples_array.tolist()


def r_sequence_samples(dim: int, budget: int, seed: int) -> list[list[float]]:
    """Generate R-sequence samples using additive recurrence (golden ratio).

    This is a simplified quasi-random sequence based on the golden ratio.
    Not as high-quality as Sobol, but useful for comparison or when
    Sobol's power-of-2 constraint is problematic.
    """
    rng = random.Random(seed)
    # Use golden ratio based quasi-random for better uniformity than pure random
    phi = (1 + 5 ** 0.5) / 2  # golden ratio
    alpha = [((i + 1) * phi) % 1 for i in range(dim)]
    samples = []
    start = rng.random()
    for n in range(budget):
        point = [((start + (n + 1) * alpha[d]) % 1) for d in range(dim)]
        samples.append(point)
    return samples


def factorial_samples(dim: int, budget: int) -> list[list[float]]:
    levels = int(round(budget ** (1.0 / dim)))
    levels = max(levels, 2)
    grid = [i / (levels - 1) for i in range(levels)]
    samples = [[]]
    for _ in range(dim):
        samples = [s + [g] for s in samples for g in grid]
    return samples[:budget]


def generate_doe(dim: int, budget: int, method: str, seed: int) -> dict[str, object]:
    if dim <= 0:
        raise ValueError("params must be positive")
    if budget <= 0:
        raise ValueError("budget must be positive")
    valid_methods = {"lhs", "sobol", "r-sequence", "factorial"}
    if method not in valid_methods:
        raise ValueError(f"method must be one of: {', '.join(sorted(valid_methods))}")

    if method == "lhs":
        samples = lhs_samples(dim, budget, seed)
    elif method == "sobol":
        # Use actual Sobol sequences via scipy.stats.qmc
        samples = sobol_samples(dim, budget, seed)
    elif method == "r-sequence":
        # Golden-ratio additive recurrence sequence
        samples = r_sequence_samples(dim, budget, seed)
    else:
        samples = factorial_samples(dim, budget)

    return {
        "method": method,
        "samples": samples,
        "coverage": {"count": len(samples), "dimension": dim},
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate design of experiments samples.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("--params", type=int, required=True, help="Number of parameters")
    parser.add_argument("--budget", type=int, required=True, help="Sample budget")
    parser.add_argument(
        "--method",
        choices=["lhs", "sobol", "r-sequence", "factorial"],
        default="lhs",
        help="DOE method (sobol uses scipy Sobol sequences)",
    )
    parser.add_argument("--seed", type=int, default=0, help="Random seed")
    parser.add_argument("--json", action="store_true", help="Emit JSON output")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    try:
        result = generate_doe(args.params, args.budget, args.method, args.seed)
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        sys.exit(2)

    payload = {
        "inputs": {
            "params": args.params,
            "budget": args.budget,
            "method": args.method,
            "seed": args.seed,
        },
        "results": result,
    }

    if args.json:
        print(json.dumps(payload, indent=2, sort_keys=True))
        return

    print("DOE samples")
    print(f"  method: {result['method']}")
    print(f"  count: {result['coverage']['count']}")


if __name__ == "__main__":
    main()
