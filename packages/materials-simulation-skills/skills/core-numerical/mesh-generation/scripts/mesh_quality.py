#!/usr/bin/env python3
import argparse
import json
import sys
from typing import Dict


def compute_quality(dx: float, dy: float, dz: float) -> Dict[str, object]:
    """Compute mesh quality metrics for a hexahedral cell.

    Computes aspect ratio, mean-deviation skewness, and anisotropy index for
    an axis-aligned hexahedral element with dimensions dx, dy, dz.

    Skewness is computed as 1 - min(sizes) / mean(sizes), measuring how far
    the smallest dimension deviates from the average.  This is distinct from
    anisotropy_index (1 - min/max) which only considers the extremes.

    Reference: Knupp, P.M., "Algebraic Mesh Quality Metrics," SIAM J. Sci. Comput.,
               23(1), 2001, pp. 193-218.

    Args:
        dx: Cell size in x direction (positive)
        dy: Cell size in y direction (positive)
        dz: Cell size in z direction (positive)

    Returns:
        Dictionary with aspect_ratio, skewness, anisotropy_index, and quality_flags
    """
    if dx <= 0 or dy <= 0 or dz <= 0:
        raise ValueError("dx, dy, dz must be positive")

    sizes = [dx, dy, dz]
    aspect_ratio = max(sizes) / min(sizes)

    # Compute size-based skewness and anisotropy for hexahedral cell.
    #
    # For axis-aligned rectangular hexahedra, all interior angles are exactly 90 deg,
    # so the classical equiangle skewness (Knupp 2001) is identically zero.
    # We therefore report a mean-deviation skewness that captures how far the
    # smallest dimension deviates from the arithmetic mean of all dimensions:
    #
    #   skewness = 1 - min(sizes) / mean(sizes)
    #
    # This is 0 for a perfect cube and approaches 1 for extremely elongated cells.
    # It differs from anisotropy_index (which uses max instead of mean) and is more
    # sensitive to cases where one dimension is small relative to the others.
    mean_size = sum(sizes) / len(sizes)
    skewness = 1.0 - (min(sizes) / mean_size)

    # Anisotropy index: measures cell stretching via edge-length ratio
    # (0 for cube, approaches 1 for extreme stretching)
    anisotropy_index = 1.0 - (min(sizes) / max(sizes))

    flags = []
    if aspect_ratio > 5.0:
        flags.append("high_aspect_ratio")
    if anisotropy_index > 0.5:
        flags.append("high_anisotropy")

    return {
        "aspect_ratio": aspect_ratio,
        "skewness": skewness,
        "anisotropy_index": anisotropy_index,
        "quality_flags": flags,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Estimate mesh quality metrics from spacing.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("--dx", type=float, required=True, help="Cell size in x")
    parser.add_argument("--dy", type=float, required=True, help="Cell size in y")
    parser.add_argument("--dz", type=float, required=True, help="Cell size in z")
    parser.add_argument("--json", action="store_true", help="Emit JSON output")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    try:
        result = compute_quality(args.dx, args.dy, args.dz)
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        sys.exit(2)

    payload = {
        "inputs": {"dx": args.dx, "dy": args.dy, "dz": args.dz},
        "results": result,
    }

    if args.json:
        print(json.dumps(payload, indent=2, sort_keys=True))
        return

    print("Mesh quality")
    print(f"  aspect_ratio: {result['aspect_ratio']:.6g}")
    print(f"  skewness: {result['skewness']:.6g}")
    print(f"  anisotropy_index: {result['anisotropy_index']:.6g}")
    for flag in result["quality_flags"]:
        print(f"  flag: {flag}")


if __name__ == "__main__":
    main()
