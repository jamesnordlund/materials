#!/usr/bin/env python3
"""
Field Extractor - Extract field data from simulation output files.

Supports JSON and CSV formats. Extracts specified fields at given timesteps
and provides metadata about available data.

Usage:
    python field_extractor.py --input results/field.json --field phi --json
    python field_extractor.py --input results/ --list --json
"""

import argparse
import json
import os
import sys
from typing import Any

# Import shared utilities
try:
    from ._utils import flatten_field, get_field_shape, load_json_file
    from ._utils import load_csv_file as _load_csv_file
except ImportError:
    # Fallback for standalone execution
    import importlib.util
    _utils_path = os.path.join(os.path.dirname(__file__), "_utils.py")
    spec = importlib.util.spec_from_file_location("_utils", _utils_path)
    _utils = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(_utils)
    load_json_file = _utils.load_json_file
    _load_csv_file = _utils.load_csv_file
    flatten_field = _utils.flatten_field
    get_field_shape = _utils.get_field_shape


def load_csv_file(path: str) -> dict[str, Any]:
    """Load CSV file with data wrapped in _data key for consistent field access."""
    csv_data = _load_csv_file(path)
    return {"_data": csv_data}


def load_data_file(filepath: str) -> dict[str, Any]:
    """Load data file based on extension."""
    if filepath.endswith(".json"):
        return load_json_file(filepath)
    elif filepath.endswith(".csv"):
        return load_csv_file(filepath)
    else:
        raise ValueError(f"Unsupported file format: {filepath}")


def list_available_fields(data: dict[str, Any]) -> list[str]:
    """List available field names in data."""
    fields = []

    if "_fields" in data:
        fields.extend(data["_fields"])
    elif "_data" in data:
        fields.extend(data["_data"].keys())
    else:
        # Try to find field-like keys
        for key, value in data.items():
            if isinstance(value, (list, dict)) and not key.startswith("_"):
                fields.append(key)

    return sorted(set(fields))


def list_available_files(directory: str) -> list[dict[str, Any]]:
    """List available data files in directory."""
    files = []

    for filename in os.listdir(directory):
        if filename.endswith((".json", ".csv")):
            filepath = os.path.join(directory, filename)
            stat = os.stat(filepath)
            files.append({
                "filename": filename,
                "filepath": filepath,
                "size_bytes": stat.st_size,
                "format": filename.split(".")[-1]
            })

    return sorted(files, key=lambda x: x["filename"])


def extract_field(data: dict[str, Any], field_name: str) -> dict[str, Any] | None:
    """Extract a specific field from data."""
    field_data = None

    # Try direct access
    if field_name in data:
        field_data = data[field_name]
    elif "_data" in data and field_name in data["_data"]:
        field_data = data["_data"][field_name]
    elif "fields" in data and field_name in data["fields"]:
        field_data = data["fields"][field_name]

    if field_data is None:
        return None

    # Compute statistics
    result = {
        "field": field_name,
        "found": True
    }

    if isinstance(field_data, list):
        result["data"] = field_data
        flat = flatten_list(field_data)
        if flat and all(isinstance(x, (int, float)) for x in flat):
            result["shape"] = get_shape(field_data)
            result["min"] = min(flat)
            result["max"] = max(flat)
            result["mean"] = sum(flat) / len(flat)
            result["count"] = len(flat)
    elif isinstance(field_data, dict):
        result["data"] = field_data
        if "values" in field_data:
            flat = flatten_list(field_data["values"])
            if flat and all(isinstance(x, (int, float)) for x in flat):
                result["min"] = min(flat)
                result["max"] = max(flat)
                result["mean"] = sum(flat) / len(flat)
                result["count"] = len(flat)
    else:
        result["data"] = field_data

    return result


# Use flatten_field from _utils (renamed from flatten_list for consistency)
flatten_list = flatten_field


# Use get_field_shape from _utils (renamed from get_shape for consistency)
get_shape = get_field_shape


def extract_multiple_fields(
    data: dict[str, Any],
    field_names: list[str]
) -> dict[str, Any]:
    """Extract multiple fields from data."""
    results = {"fields": {}}

    for field in field_names:
        result = extract_field(data, field)
        if result and result.get("found"):
            results["fields"][field] = result
        else:
            results["fields"][field] = {"field": field, "found": False}

    return results


def get_timestep_info(data: dict[str, Any]) -> dict[str, Any] | None:
    """Extract timestep/time information from data."""
    info = {}

    for key in ["timestep", "time_step", "step", "iteration", "n"]:
        if key in data:
            info["timestep"] = data[key]
            break

    for key in ["time", "t", "physical_time"]:
        if key in data:
            info["time"] = data[key]
            break

    return info if info else None


def main():
    parser = argparse.ArgumentParser(
        description="Extract field data from simulation output files"
    )
    parser.add_argument(
        "--input", "-i",
        required=True,
        help="Input file or directory path"
    )
    parser.add_argument(
        "--field", "-f",
        help="Field name(s) to extract (comma-separated)"
    )
    parser.add_argument(
        "--list", "-l",
        action="store_true",
        help="List available fields or files"
    )
    parser.add_argument(
        "--timestep", "-t",
        type=int,
        help="Specific timestep to extract (for directory input)"
    )
    parser.add_argument(
        "--include-data",
        action="store_true",
        help="Include raw data in output (default: metadata only)"
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output as JSON"
    )

    args = parser.parse_args()

    try:
        # Check if input is directory or file
        if os.path.isdir(args.input):
            if args.list:
                # List available files
                files = list_available_files(args.input)
                result = {
                    "directory": args.input,
                    "file_count": len(files),
                    "files": files
                }

                if args.json:
                    print(json.dumps(result, indent=2))
                else:
                    print(f"Directory: {args.input}")
                    print(f"Files found: {len(files)}")
                    for f in files:
                        print(f"  - {f['filename']} ({f['format']}, {f['size_bytes']} bytes)")
                return

            elif args.timestep is not None:
                # Find file for specific timestep
                pattern = f"_{args.timestep:04d}."
                matching = [f for f in os.listdir(args.input)
                           if pattern in f or f"_{args.timestep}." in f]
                if not matching:
                    print(f"Error: No file found for timestep {args.timestep}",
                          file=sys.stderr)
                    sys.exit(1)
                input_path = os.path.join(args.input, matching[0])
            else:
                print("Error: For directory input, use --list or specify --timestep",
                      file=sys.stderr)
                sys.exit(1)
        else:
            input_path = args.input

        # Load data file
        if not os.path.exists(input_path):
            print(f"Error: File not found: {input_path}", file=sys.stderr)
            sys.exit(1)

        data = load_data_file(input_path)

        if args.list:
            # List available fields
            fields = list_available_fields(data)
            timestep_info = get_timestep_info(data)

            result = {
                "file": input_path,
                "available_fields": fields,
                "field_count": len(fields)
            }
            if timestep_info:
                result["timestep_info"] = timestep_info

            if args.json:
                print(json.dumps(result, indent=2))
            else:
                print(f"File: {input_path}")
                if timestep_info:
                    print(f"Timestep info: {timestep_info}")
                print(f"Available fields ({len(fields)}):")
                for f in fields:
                    print(f"  - {f}")
            return

        if not args.field:
            print("Error: --field required when not using --list", file=sys.stderr)
            sys.exit(1)

        # Extract requested fields
        field_names = [f.strip() for f in args.field.split(",")]

        if len(field_names) == 1:
            result = extract_field(data, field_names[0])
            if not result or not result.get("found"):
                available = list_available_fields(data)
                print(f"Error: Field '{field_names[0]}' not found. "
                      f"Available: {available}", file=sys.stderr)
                sys.exit(1)
        else:
            result = extract_multiple_fields(data, field_names)

        # Add metadata
        result["source_file"] = input_path
        timestep_info = get_timestep_info(data)
        if timestep_info:
            result["timestep_info"] = timestep_info

        # Remove raw data if not requested
        if not args.include_data:
            if "data" in result:
                del result["data"]
            if "fields" in result:
                for field_result in result["fields"].values():
                    if "data" in field_result:
                        del field_result["data"]

        # Output
        if args.json:
            print(json.dumps(result, indent=2))
        else:
            print(f"File: {input_path}")
            if "field" in result:
                # Single field
                print(f"Field: {result['field']}")
                if "shape" in result:
                    print(f"Shape: {result['shape']}")
                if "min" in result:
                    print(f"Min: {result['min']:.6g}")
                    print(f"Max: {result['max']:.6g}")
                    print(f"Mean: {result['mean']:.6g}")
            else:
                # Multiple fields
                for field, fdata in result.get("fields", {}).items():
                    print(f"\nField: {field}")
                    if fdata.get("found"):
                        if "shape" in fdata:
                            print(f"  Shape: {fdata['shape']}")
                        if "min" in fdata:
                            print(f"  Range: [{fdata['min']:.6g}, {fdata['max']:.6g}]")
                    else:
                        print("  Not found")

    except FileNotFoundError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"Error parsing JSON: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
