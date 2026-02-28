"""Path validation sandbox for materials-simulation-skills CLI scripts.

This module provides functions to validate that file paths supplied as CLI
arguments remain within a designated sandbox directory.  It prevents path-
traversal attacks (via '..' components, symlinks, or absolute paths outside the
sandbox) by resolving every path through os.path.realpath and checking
containment with os.path.commonpath.

Typical usage inside a CLI script's main():

    from _path_validation import add_sandbox_args, resolve_sandbox_root, validate_all_paths

    parser = argparse.ArgumentParser(...)
    add_sandbox_args(parser)
    args = parser.parse_args()

    sandbox = resolve_sandbox_root(args)
    validate_all_paths(args, sandbox, ["input", "output", "output_dir", "log"])
"""

from __future__ import annotations

import argparse
import os
from pathlib import Path


def add_sandbox_args(parser: argparse.ArgumentParser) -> None:
    """Add the --sandbox-root argument to an argparse parser.

    Args:
        parser: The argument parser to augment.
    """
    parser.add_argument(
        "--sandbox-root",
        type=str,
        default=None,
        help="Root directory for path validation sandbox (default: CWD)",
    )


def resolve_sandbox_root(args: argparse.Namespace) -> Path:
    """Determine the sandbox root directory.

    Resolution order:
        1. --sandbox-root CLI argument (if provided)
        2. MATERIALS_SANDBOX_ROOT environment variable (if set)
        3. Current working directory

    The result is always canonicalised via os.path.realpath so that symlinks
    and relative components are resolved.

    Args:
        args: Parsed argparse namespace (should contain sandbox_root attribute).

    Returns:
        Resolved absolute Path to the sandbox root.
    """
    if getattr(args, "sandbox_root", None):
        return Path(os.path.realpath(args.sandbox_root))
    env_root = os.environ.get("MATERIALS_SANDBOX_ROOT")
    if env_root:
        return Path(os.path.realpath(env_root))
    return Path(os.path.realpath(os.getcwd()))


def validate_path(path: str | os.PathLike, sandbox_root: Path) -> str | None:
    """Validate that a path is within the sandbox directory.

    Resolves the supplied path and the sandbox root via os.path.realpath,
    then checks containment using os.path.commonpath (which compares path
    components, not string prefixes, avoiding directory-name prefix attacks).

    Args:
        path: The path to validate (may be relative or absolute).
        sandbox_root: The resolved sandbox root directory.

    Returns:
        An error message string if the path escapes the sandbox, or None
        if the path is valid.
    """
    resolved = Path(os.path.realpath(path))
    sandbox_resolved = Path(os.path.realpath(sandbox_root))

    try:
        common = Path(os.path.commonpath([resolved, sandbox_resolved]))
    except ValueError:
        # On Windows, paths on different drives have no common path
        return f"Path '{path}' is outside sandbox '{sandbox_resolved}'"

    if common != sandbox_resolved:
        return f"Path '{path}' is outside sandbox '{sandbox_resolved}'"

    return None


def validate_all_paths(
    args: argparse.Namespace, sandbox_root: Path, path_args: list[str]
) -> str | None:
    """Validate all path-type arguments against the sandbox root.

    Iterates over the named attributes in the argparse namespace and calls
    validate_path for each non-None value.

    Args:
        args: Parsed argparse namespace.
        sandbox_root: The resolved sandbox root directory.
        path_args: List of attribute names on args that hold file paths.

    Returns:
        An error message string if any path is invalid, or None if all
        paths are valid.
    """
    for attr_name in path_args:
        value = getattr(args, attr_name, None)
        if value is not None:
            err = validate_path(value, sandbox_root)
            if err is not None:
                return err
    return None
