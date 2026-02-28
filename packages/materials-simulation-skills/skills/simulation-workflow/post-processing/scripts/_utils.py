"""Shared utility functions for post-processing scripts."""

import json


def load_json_file(path):
    """Load and parse a JSON file."""
    with open(path, "r", encoding="utf-8") as fh:
        return json.load(fh)


def load_csv_file(path, delimiter=","):
    """Load CSV file as column-based dict.

    Returns:
        dict mapping column header names to lists of values.
    """
    data = {}

    with open(path, "r", encoding="utf-8") as f:
        lines = f.readlines()

    if not lines:
        return data

    header = lines[0].strip().split(delimiter)
    for col in header:
        data[col.strip()] = []

    for line in lines[1:]:
        values = line.strip().split(delimiter)
        for i, col in enumerate(header):
            col = col.strip()
            if i < len(values):
                data[col].append(_try_float(values[i]))

    return data


def get_field_data(data, field_name):
    """Extract field data as nested list, searching nested structures."""
    if field_name in data:
        return data[field_name]
    if "fields" in data and field_name in data["fields"]:
        field_data = data["fields"][field_name]
        if isinstance(field_data, dict) and "values" in field_data:
            return field_data["values"]
        return field_data
    if "_data" in data and field_name in data["_data"]:
        return data["_data"][field_name]
    return None


def flatten_field(field):
    """Recursively flatten a nested list/array into a flat list of floats.

    Non-numeric values are skipped silently.
    """
    result = []
    if isinstance(field, (list, tuple)):
        for item in field:
            result.extend(flatten_field(item))
    else:
        try:
            result.append(float(field))
        except (ValueError, TypeError):
            # Skip non-numeric values
            pass
    return result


def get_field_shape(field):
    """Return the shape of a nested list as a list of ints.

    For ragged (non-rectangular) arrays, returns the shape up to and
    including the first dimension where lengths differ, with -1 as
    the sentinel value for that ragged dimension.
    """
    shape = []
    if not isinstance(field, (list, tuple)):
        return shape
    # Walk each nesting level
    current_level = [field]
    while True:
        item = current_level[0]
        if not isinstance(item, (list, tuple)):
            break
        lengths = {len(c) for c in current_level if isinstance(c, (list, tuple))}
        if len(lengths) != 1:
            # Ragged dimension detected
            shape.append(-1)
            break
        dim_size = lengths.pop()
        shape.append(dim_size)
        if dim_size == 0:
            break
        # Descend into next level
        next_level = []
        for c in current_level:
            if isinstance(c, (list, tuple)):
                next_level.extend(c)
        current_level = next_level
    return shape


def _is_numeric(s):
    """Check if a string represents a number."""
    try:
        float(s.strip())
        return True
    except (ValueError, AttributeError):
        return False


def _try_float(s):
    """Try to convert string to float, return original string on failure."""
    try:
        return float(s)
    except (ValueError, TypeError):
        return s
