"""Dependency flags, API key resolution, and prerequisite checks."""

from __future__ import annotations

import logging
import os

from mcp_materials._validation import _error_response

logger = logging.getLogger(__name__)

# ============================================================================
# Dependency flags
# ============================================================================

try:
    from mp_api.client import MPRester  # noqa: F401
    from pymatgen.analysis.phase_diagram import PhaseDiagram  # noqa: F401
    from pymatgen.io.cif import CifWriter  # noqa: F401
    from pymatgen.io.vasp import Poscar  # noqa: F401

    HAS_MP_API = True
except ImportError:
    HAS_MP_API = False

try:
    from mpcontribs.client import Client as ContribsClient  # noqa: F401

    HAS_MPCONTRIBS = True
except ImportError:
    ContribsClient = None
    HAS_MPCONTRIBS = False

if not HAS_MPCONTRIBS:
    logger.warning(
        "mpcontribs-client not installed. Contribs tools will return install guidance. "
        "Run: pip install materials-mcp[contribs]"
    )


# ============================================================================
# API key resolution
# ============================================================================


def get_mp_api_key() -> str | None:
    """Get Materials Project API key from environment.

    Precedence:
    1. MP_API_KEY
    2. PMG_MAPI_KEY (pymatgen legacy fallback)
    """
    return os.environ.get("MP_API_KEY") or os.environ.get("PMG_MAPI_KEY")


def check_api_key() -> tuple[bool, str]:
    """Check if API key is configured.

    Returns:
        A tuple of (has_key, key_or_error). When has_key is True, the second
        element is the API key string. When False, it is a user-facing error
        message explaining how to set the key.
    """
    key = get_mp_api_key()
    if not key:
        return False, (
            "MP_API_KEY environment variable not set. "
            "Get your key at https://materialsproject.org/api"
        )
    return True, key


# ============================================================================
# Prerequisite checks
# ============================================================================


def _check_prerequisites() -> tuple[str | None, str | None]:
    """Check API key and mp-api availability.

    Returns:
        A tuple of (error_response, api_key). When error_response is not None
        the caller should return it immediately. When None, api_key is the
        validated key string ready for MPRester.
    """
    has_key, key_or_error = check_api_key()
    if not has_key:
        return _error_response(key_or_error), None
    if not HAS_MP_API:
        return (
            _error_response(
                "mp-api and/or pymatgen not installed. Run: pip install mp-api pymatgen"
            ),
            None,
        )
    return None, key_or_error


def _check_contribs_prerequisites() -> tuple[str | None, str | None]:
    """Check mpcontribs-client availability and API key.

    Returns:
        (error_response, api_key). When error_response is not None the caller
        should return it immediately.
    """
    if not HAS_MPCONTRIBS:
        return (
            _error_response(
                "mpcontribs-client not installed. "
                "Run: pip install materials-mcp[contribs]"
            ),
            None,
        )
    has_key, key_or_error = check_api_key()
    if not has_key:
        return _error_response(key_or_error), None
    return None, key_or_error
