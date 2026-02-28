#!/usr/bin/env python3
import argparse
import json
import os
import re
import sys


def get_free_disk_space_gb(path: str) -> float | None:
    """Get free disk space in GB. Cross-platform (Windows, Linux, macOS)."""
    try:
        if sys.platform == "win32":
            # Windows: use ctypes to call GetDiskFreeSpaceExW
            import ctypes

            free_bytes = ctypes.c_ulonglong(0)
            ctypes.windll.kernel32.GetDiskFreeSpaceExW(
                ctypes.c_wchar_p(os.path.abspath(path)),
                None,
                None,
                ctypes.pointer(free_bytes),
            )
            return free_bytes.value / (1024**3)
        else:
            # Unix-like: use os.statvfs
            stat = os.statvfs(path)
            return (stat.f_bavail * stat.f_frsize) / (1024**3)
    except (OSError, AttributeError):
        return None


def load_config(path: str) -> dict[str, object]:
    if not os.path.exists(path):
        raise ValueError(f"Config not found: {path}")
    if path.endswith(".json"):
        with open(path, encoding="utf-8") as handle:
            return json.load(handle)
    # Minimal YAML-like fallback: key: value per line
    config: dict[str, object] = {}
    # Regex for scientific notation
    sci_notation_re = re.compile(r'^[+-]?\d+\.?\d*[eE][+-]?\d+$')
    with open(path, encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if ":" not in line:
                continue
            key, value = line.split(":", 1)
            key = key.strip()
            value = value.strip()
            try:
                # Check for scientific notation first
                if sci_notation_re.match(value) or "." in value:
                    parsed = float(value)
                else:
                    parsed = int(value)
            except ValueError:
                parsed = value
            config[key] = parsed
    return config


def parse_list(raw: str | None) -> list[str]:
    if not raw:
        return []
    return [p.strip() for p in raw.split(",") if p.strip()]


def parse_ranges(raw: str | None) -> dict[str, tuple[float, float]]:
    ranges: dict[str, tuple[float, float]] = {}
    if not raw:
        return ranges
    parts = [p.strip() for p in raw.split(",") if p.strip()]
    for part in parts:
        if ":" not in part:
            raise ValueError("range entries must be name:min:max")
        name, min_val, max_val = part.split(":", 2)
        ranges[name.strip()] = (float(min_val), float(max_val))
    return ranges


def check_mesh_quality(config: dict[str, object]) -> list[str]:
    """
    Check mesh quality metrics if available in config.

    Conditionally checks mesh quality thresholds:
    - min_element_quality < 0.1 -> warning
    - max_aspect_ratio > 100 -> warning
    - max_skewness > 0.95 -> warning

    Args:
        config: Simulation configuration dict

    Returns:
        List of warning messages (empty if no issues or no mesh data)
    """
    warnings: list[str] = []

    # Check for mesh metrics in config (nested under 'mesh' key or at top level)
    mesh = config.get("mesh", {})
    if not isinstance(mesh, dict):
        # No mesh data or invalid format - skip checks
        return warnings

    # Check minimum element quality
    min_quality = mesh.get("min_element_quality")
    if min_quality is not None:
        try:
            quality_val = float(min_quality)
            if quality_val < 0.1:
                warnings.append(
                    f"Very poor minimum element quality: {quality_val:.3f} "
                    "(threshold: 0.1)"
                )
        except (TypeError, ValueError):
            # Non-numeric value - skip check
            pass

    # Check maximum aspect ratio
    max_aspect = mesh.get("max_aspect_ratio")
    if max_aspect is not None:
        try:
            aspect_val = float(max_aspect)
            if aspect_val > 100:
                warnings.append(
                    f"Extreme aspect ratio: {aspect_val:.1f} "
                    "(threshold: 100)"
                )
        except (TypeError, ValueError):
            # Non-numeric value - skip check
            pass

    # Check maximum skewness
    max_skewness = mesh.get("max_skewness")
    if max_skewness is not None:
        try:
            skewness_val = float(max_skewness)
            if skewness_val > 0.95:
                warnings.append(
                    f"Severe mesh skewness: {skewness_val:.3f} "
                    "(threshold: 0.95)"
                )
        except (TypeError, ValueError):
            # Non-numeric value - skip check
            pass

    return warnings


def preflight_check(
    config: dict[str, object],
    required: list[str],
    ranges: dict[str, tuple[float, float]],
    output_dir: str | None,
    min_free_gb: float,
) -> dict[str, object]:
    blockers: list[str] = []
    warnings: list[str] = []

    params = config.get("parameters", {})
    if not isinstance(params, dict):
        params = {}

    for key in required:
        if key not in config and key not in params:
            blockers.append(f"Missing required parameter: {key}")

    for key, (min_val, max_val) in ranges.items():
        value = config.get(key, params.get(key))
        if value is None:
            warnings.append(f"Range check skipped; missing {key}.")
            continue
        try:
            numeric = float(value)
        except (TypeError, ValueError):
            blockers.append(f"Non-numeric value for {key}.")
            continue
        if numeric < min_val or numeric > max_val:
            blockers.append(f"{key} out of range [{min_val}, {max_val}].")

    output_dir = output_dir or config.get("output_dir")
    if output_dir:
        if not os.path.exists(output_dir):
            warnings.append("Output directory does not exist; will be created.")
        else:
            if not os.access(output_dir, os.W_OK):
                blockers.append("Output directory not writable.")
    else:
        warnings.append("No output directory specified.")

    if min_free_gb > 0:
        free_gb = get_free_disk_space_gb(".")
        if free_gb is not None and free_gb < min_free_gb:
            blockers.append(f"Insufficient disk space: {free_gb:.2f} GB free.")
        elif free_gb is None:
            warnings.append("Could not determine free disk space.")

    if "material_source" not in config and "materials_source" not in config:
        warnings.append("Material property source not specified.")

    # Check mesh quality metrics if present (REQ-F05)
    mesh_warnings = check_mesh_quality(config)
    warnings.extend(mesh_warnings)

    status = "PASS"
    if blockers:
        status = "BLOCK"
    elif warnings:
        status = "WARN"

    return {
        "status": status,
        "blockers": blockers,
        "warnings": warnings,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Pre-flight simulation validation checks.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("--config", required=True, help="Path to simulation config (JSON)")
    parser.add_argument(
        "--required",
        default=None,
        help="Comma-separated required parameters",
    )
    parser.add_argument(
        "--ranges",
        default=None,
        help="Range checks name:min:max (comma-separated)",
    )
    parser.add_argument(
        "--output-dir",
        default=None,
        help="Override output directory for checks",
    )
    parser.add_argument(
        "--min-free-gb",
        type=float,
        default=0.1,
        help="Minimum free disk space (GB)",
    )
    parser.add_argument("--json", action="store_true", help="Emit JSON output")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    try:
        config = load_config(args.config)
        report = preflight_check(
            config=config,
            required=parse_list(args.required),
            ranges=parse_ranges(args.ranges),
            output_dir=args.output_dir,
            min_free_gb=args.min_free_gb,
        )
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        sys.exit(2)

    payload = {
        "inputs": {
            "config": args.config,
            "required": parse_list(args.required),
            "ranges": args.ranges,
            "output_dir": args.output_dir,
            "min_free_gb": args.min_free_gb,
        },
        "report": report,
    }

    if args.json:
        print(json.dumps(payload, indent=2, sort_keys=True))
        return

    print("Preflight report")
    print(f"  status: {report['status']}")
    for item in report["blockers"]:
        print(f"  blocker: {item}")
    for item in report["warnings"]:
        print(f"  warning: {item}")


if __name__ == "__main__":
    main()
