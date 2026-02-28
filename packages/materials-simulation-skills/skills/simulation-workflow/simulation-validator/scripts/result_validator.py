#!/usr/bin/env python3
import argparse
import json
import math
import sys


def load_metrics(path: str) -> dict[str, object]:
    with open(path, encoding="utf-8") as handle:
        return json.load(handle)


def check_energy_monotonic(energies: list[float]) -> bool:
    """Check that energy decreases (or stays constant) at every step.

    Appropriate for dissipative / gradient-flow systems such as
    Allen-Cahn and Cahn-Hilliard phase-field models, where the free
    energy functional is mathematically guaranteed to decrease
    monotonically in time.
    """
    return all(
        energies[i + 1] <= energies[i] for i in range(len(energies) - 1)
    )


def check_energy_overall(energies: list[float]) -> bool:
    """Check that the final energy is less than or equal to the initial energy.

    Appropriate for general simulations where local energy fluctuations
    are acceptable (e.g. coupled multi-physics, stochastic forcing,
    thermostat-driven equilibration) but the overall trend must be
    dissipative.
    """
    return energies[-1] <= energies[0]


# Valid energy_mode values for validate_metrics.
_ENERGY_MODES = ("monotonic", "overall", "bounded")


def validate_metrics(
    metrics: dict[str, object],
    bound_min: float | None,
    bound_max: float | None,
    mass_tol: float,
    check_energy_dissipation: bool = True,
    energy_mode: str | None = None,
) -> dict[str, object]:
    """Validate simulation result metrics.

    Parameters
    ----------
    metrics : dict
        Simulation output metrics (mass, energy history, field bounds, etc.).
    bound_min, bound_max : float or None
        Expected field value bounds.
    mass_tol : float
        Relative mass-conservation tolerance.
    check_energy_dissipation : bool
        Legacy toggle.  When *energy_mode* is ``None`` (the default),
        ``True`` maps to ``energy_mode="monotonic"`` and ``False`` maps
        to ``energy_mode="bounded"``.
    energy_mode : str or None
        Explicit energy-validation strategy.  One of:

        * ``"monotonic"`` -- energy must decrease (or stay constant) at
          every time step.  Correct for gradient-flow / dissipative
          systems (phase-field Allen-Cahn, Cahn-Hilliard).
        * ``"overall"`` -- only the final energy must be <= the initial
          energy; local fluctuations are tolerated.  Useful for general
          simulations where sub-system energy exchange or stochastic
          noise can cause transient increases.
        * ``"bounded"`` -- energy must simply remain finite (no NaN /
          Inf).  Correct for conservative / Hamiltonian systems (e.g.
          NVE molecular dynamics).

        When provided, *energy_mode* takes precedence over the legacy
        *check_energy_dissipation* flag.
    """
    # Resolve energy_mode from the legacy flag when not explicitly given.
    if energy_mode is None:
        energy_mode = "monotonic" if check_energy_dissipation else "bounded"
    if energy_mode not in _ENERGY_MODES:
        raise ValueError(
            f"energy_mode must be one of {_ENERGY_MODES!r}, got {energy_mode!r}"
        )

    checks: dict[str, bool] = {}
    failed: list[str] = []

    mass_initial = metrics.get("mass_initial")
    mass_final = metrics.get("mass_final")
    if mass_initial is not None and mass_final is not None:
        try:
            drift = (
                abs(float(mass_final) - float(mass_initial))
                / max(abs(float(mass_initial)), 1e-12)
            )
            checks["mass_conserved"] = drift <= mass_tol
            if not checks["mass_conserved"]:
                failed.append("mass_conserved")
        except (TypeError, ValueError):
            checks["mass_conserved"] = False
            failed.append("mass_conserved")

    energy_history = metrics.get("energy_history")
    if isinstance(energy_history, list) and energy_history:
        try:
            energies = [float(v) for v in energy_history]
            if energy_mode == "monotonic":
                # Dissipative / gradient-flow system: energy must
                # monotonically decrease (or stay constant) at every step.
                checks["energy_decreases"] = check_energy_monotonic(energies)
                if not checks["energy_decreases"]:
                    failed.append("energy_decreases")
            elif energy_mode == "overall":
                # General dissipative system: final energy <= initial energy,
                # but local fluctuations are tolerated.
                checks["energy_decreases"] = check_energy_overall(energies)
                if not checks["energy_decreases"]:
                    failed.append("energy_decreases")
            else:
                # Conservative / Hamiltonian system: energy should remain
                # bounded (no NaN, no Inf, and no runaway growth).
                checks["energy_bounded"] = all(
                    math.isfinite(e) for e in energies
                )
                if not checks["energy_bounded"]:
                    failed.append("energy_bounded")
        except (TypeError, ValueError):
            key = (
                "energy_decreases"
                if energy_mode in ("monotonic", "overall")
                else "energy_bounded"
            )
            checks[key] = False
            failed.append(key)

    field_min = metrics.get("field_min")
    field_max = metrics.get("field_max")
    if bound_min is not None or bound_max is not None:
        ok = True
        if field_min is not None and bound_min is not None:
            ok = ok and (float(field_min) >= bound_min)
        if field_max is not None and bound_max is not None:
            ok = ok and (float(field_max) <= bound_max)
        checks["bounds_satisfied"] = ok
        if not ok:
            failed.append("bounds_satisfied")

    has_nan = metrics.get("has_nan")
    if has_nan is not None:
        checks["no_nan"] = not bool(has_nan)
        if not checks["no_nan"]:
            failed.append("no_nan")

    if not checks:
        return {
            "checks": {"no_checks": True},
            "failed_checks": [],
            "confidence_score": None,
            "warning": "No validation evidence available",
        }

    passed = sum(1 for v in checks.values() if v)
    confidence = passed / max(len(checks), 1)

    return {
        "checks": checks,
        "failed_checks": failed,
        "confidence_score": confidence,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Validate simulation results from metrics JSON.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("--metrics", required=True, help="Path to metrics JSON")
    parser.add_argument("--bound-min", type=float, default=None, help="Minimum bound")
    parser.add_argument("--bound-max", type=float, default=None, help="Maximum bound")
    parser.add_argument("--mass-tol", type=float, default=1e-3, help="Mass tolerance")
    parser.add_argument(
        "--check-energy-dissipation",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Legacy flag: check monotonic energy decrease (disable for conservative systems). "
        "Prefer --energy-mode for finer control.",
    )
    parser.add_argument(
        "--energy-mode",
        choices=["monotonic", "overall", "bounded"],
        default=None,
        help="Energy validation strategy. 'monotonic': energy must decrease at every step "
        "(gradient-flow / phase-field). 'overall': final energy <= initial energy, local "
        "fluctuations tolerated (general simulations). 'bounded': energy must be finite "
        "(conservative / Hamiltonian systems). Overrides --check-energy-dissipation when set.",
    )
    parser.add_argument("--json", action="store_true", help="Emit JSON output")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    try:
        metrics = load_metrics(args.metrics)
        result = validate_metrics(
            metrics=metrics,
            bound_min=args.bound_min,
            bound_max=args.bound_max,
            mass_tol=args.mass_tol,
            check_energy_dissipation=args.check_energy_dissipation,
            energy_mode=args.energy_mode,
        )
    except (ValueError, OSError) as exc:
        print(str(exc), file=sys.stderr)
        sys.exit(2)

    payload = {
        "inputs": {
            "metrics": args.metrics,
            "bound_min": args.bound_min,
            "bound_max": args.bound_max,
            "mass_tol": args.mass_tol,
        },
        "results": result,
    }

    if args.json:
        print(json.dumps(payload, indent=2, sort_keys=True))
        return

    print("Result validation")
    cs = result["confidence_score"]
    print(f"  confidence_score: {cs:.6g}" if cs is not None else "  confidence_score: N/A")
    if "warning" in result:
        print(f"  warning: {result['warning']}")
    for name, status in result["checks"].items():
        print(f"  {name}: {status}")


if __name__ == "__main__":
    main()
