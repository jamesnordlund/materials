"""Pytest configuration for mcp_materials tests."""

import json
import os
import re
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

# ============================================================================
# Record / Replay test harness  (TASK-010, traces: R-TEST-001, R-TEST-005)
# ============================================================================

RECORD_MODE: bool = os.environ.get("MCP_TEST_RECORD", "0") == "1"

_FIXTURES_DIR = Path(__file__).parent / "fixtures"

# Patterns used by _check_api_key_leak to satisfy R-TEST-005 / R-SEC-015.
# 1. Known environment variable *values* that should never appear in fixtures.
_KEY_NAME_PATTERNS: list[str] = [
    "MP_API_KEY",
    "PMG_MAPI_KEY",
    "MPCONTRIBS_API_KEY",
]
# 2. Generic pattern: 32+ contiguous alphanumeric chars that look like an API
#    key or bearer token.  UUIDs (with hyphens) are excluded intentionally.
_GENERIC_KEY_RE = re.compile(r"[A-Za-z0-9]{32,}")

# Substrings that are expected to legitimately match the generic regex
# (e.g. POTCAR MD5 hashes in task fixture data).  Extend as needed.
_ALLOWLISTED_LONG_STRINGS: set[str] = {
    "b2b0ea6feb62e7cde209616b0b17e78a",  # Si POTCAR hash in tasks_mp149.json
}


def _check_api_key_leak(raw_text: str, source_path: str) -> None:
    """Raise ``AssertionError`` if *raw_text* contains an API key pattern.

    Checked patterns:
    * Literal occurrences of known key-name strings used as *values*
      (``MP_API_KEY``, ``PMG_MAPI_KEY``, ``MPCONTRIBS_API_KEY``).
    * Any 32+ character alphanumeric token that resembles an API key.

    Parameters
    ----------
    raw_text:
        The full text content of a fixture file.
    source_path:
        Human-readable path used only in the error message.
    """
    for key_name in _KEY_NAME_PATTERNS:
        if key_name in raw_text:
            raise AssertionError(
                f"Fixture {source_path} contains forbidden key pattern "
                f"'{key_name}'.  Remove or redact the value before committing."
            )

    for match in _GENERIC_KEY_RE.finditer(raw_text):
        token = match.group()
        if token not in _ALLOWLISTED_LONG_STRINGS:
            raise AssertionError(
                f"Fixture {source_path} contains a suspected API key or "
                f"token ({token[:12]}..., length {len(token)}).  If this is "
                f"a false positive, add it to _ALLOWLISTED_LONG_STRINGS in "
                f"conftest.py."
            )


def _load_fixture(fixture_dir: Path, fixture_name: str) -> dict:
    """Load a JSON fixture from *fixture_dir* and run the leak check.

    In **replay mode** (default) the fixture is read from disk.
    In **record mode** (``MCP_TEST_RECORD=1``) the behaviour is identical
    for now -- live recording will be wired in a future task.

    Returns the parsed JSON object.
    """
    fixture_path = fixture_dir / f"{fixture_name}.json"
    if not fixture_path.exists():
        raise FileNotFoundError(
            f"Fixture file not found: {fixture_path}.  "
            f"Run with MCP_TEST_RECORD=1 to create it (once recording is wired)."
        )
    raw = fixture_path.read_text(encoding="utf-8")
    _check_api_key_leak(raw, str(fixture_path))
    return json.loads(raw)


def mp_fixture(fixture_name: str) -> dict:
    """Load a Materials Project fixture by name.

    Looks for ``tests/fixtures/mp/{fixture_name}.json``.
    """
    return _load_fixture(_FIXTURES_DIR / "mp", fixture_name)


def contribs_fixture(fixture_name: str) -> dict:
    """Load an MPContribs fixture by name.

    Looks for ``tests/fixtures/contribs/{fixture_name}.json``.
    """
    return _load_fixture(_FIXTURES_DIR / "contribs", fixture_name)


@pytest.fixture(autouse=True)
def _set_dummy_api_key(monkeypatch):
    """Set a dummy API key so mocked tests pass the key check."""
    monkeypatch.setenv("MP_API_KEY", "test-api-key-for-testing")


@pytest.fixture(autouse=True)
def _reset_contribs_singleton():
    """Reset the cached ContribsClient singleton between tests."""
    from mcp_materials.contribs_tools import _reset_contribs_client
    _reset_contribs_client()
    yield
    _reset_contribs_client()

# ============================================================================
# Shared test helpers
# ============================================================================

_UNSET = object()  # sentinel to distinguish "not passed" from explicit None


def _make_symmetry(
    symbol="Fm-3m", number=225, crystal_system="cubic", point_group="m-3m"
):
    return SimpleNamespace(
        symbol=symbol,
        number=number,
        crystal_system=crystal_system,
        point_group=point_group,
    )


def _make_summary_doc(
    material_id="mp-149",
    formula_pretty="Si",
    energy_above_hull=0.0,
    band_gap=1.11,
    formation_energy_per_atom=-0.5,
    density=2.33,
    symmetry=_UNSET,
    is_stable=True,
    elements=None,
    nelements=1,
    nsites=2,
    volume=40.0,
    is_metal=False,
    is_magnetic=False,
    total_magnetization=0.0,
    is_gap_direct=True,
):
    if symmetry is _UNSET:
        symmetry = _make_symmetry()
    return SimpleNamespace(
        material_id=material_id,
        formula_pretty=formula_pretty,
        energy_above_hull=energy_above_hull,
        band_gap=band_gap,
        formation_energy_per_atom=formation_energy_per_atom,
        density=density,
        symmetry=symmetry,
        is_stable=is_stable,
        elements=elements or ["Si"],
        nelements=nelements,
        nsites=nsites,
        volume=volume,
        is_metal=is_metal,
        is_magnetic=is_magnetic,
        total_magnetization=total_magnetization,
        database_IDs={"icsd": [12345]},
        is_gap_direct=is_gap_direct,
    )


def _mock_mprester():
    """Build a mock MPRester context manager."""
    mpr = MagicMock()
    ctx = MagicMock()
    ctx.__enter__ = MagicMock(return_value=mpr)
    ctx.__exit__ = MagicMock(return_value=False)
    return ctx, mpr


def _mock_contribs_client():
    """Build a mock ContribsClient."""
    client = MagicMock()
    client.projects = MagicMock()
    client.contributions = MagicMock()
    client.tables = MagicMock()
    client.structures = MagicMock()
    client.attachments = MagicMock()
    return client


class FakeHTTPError(Exception):
    """Lightweight stand-in for bravado.exception.HTTPError."""

    def __init__(self, status_code, message=""):
        self.status_code = status_code
        super().__init__(message)
