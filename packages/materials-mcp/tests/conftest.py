"""Pytest configuration for mcp_materials tests."""

from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest


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
