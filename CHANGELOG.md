# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [0.2.0] - 2026-03-01

### Added

**MCP Tools (materials-mcp)**

- `mp_get_database_version` -- returns the current Materials Project database version for reproducibility tracking.
- `mp_provenance_get` -- retrieves provenance metadata (task IDs, builder info, timestamps) for a material.
- `mp_tasks_get` -- retrieves task-level provenance data (calculation IDs, input parameters, task types) for a material.
- `mp_summary_search_advanced` -- advanced multi-field search with filters for elements, formula, chemsys, band gap range, energy above hull, stability, and metallicity. Supports field selection, sorting, and result capping (1-100).
- `mp_insertion_electrodes_search` -- searches insertion electrode data by working ion, material ID, or chemical system. Returns voltage, capacity, and framework information.

**Infrastructure (materials-mcp)**

- `_cache.py` -- in-memory LRU cache with TTL for MCP tool responses. Keyed by `(tool_name, args_hash, db_version)` so entries auto-invalidate on database updates.
- `_output.py` -- standardized response builder (`_build_response`) producing consistent JSON with `metadata`, `query`, `count`, `records`, and `errors` keys. Includes `_sanitize_floats` to replace NaN/Inf with null.
- `_db_version.py` -- cached database version fetcher with 5-minute TTL and graceful fallback (sets `db_version` to null on failure instead of failing the tool call).
- All new tool outputs include a `metadata.db_version` field for reproducibility.
- Record/replay test harness in `conftest.py` with `mp_fixture()` and `contribs_fixture()` helpers.
- CI step for API key leak detection in test fixtures.

**New Package: materials-data-workflows (v0.1.0)**

- New plugin package with three MVP skills for data-to-decision workflows.
- `mp-pareto-screening` skill:
  - `pareto_frontier.py` -- multi-objective Pareto frontier computation with constraint filtering, crowding distance, and dominance ranking.
  - `export_candidates.py` -- exports frontier results to CSV or JSON with unit-suffixed column headers and deterministic ordering.
- `insertion-electrode-metrics` skill:
  - `electrode_metrics.py` -- computes derived electrode metrics (average voltage, gravimetric/volumetric capacity, energy density, stability flags) from normalized electrode documents.
  - `voltage_curve_summarizer.py` -- detects voltage plateaus and computes min/max/average voltage and hysteresis proxy.
- `mp-provenance-reporter` skill:
  - `build_manifest.py` -- generates reproducibility manifests with input hashes, tool call records, database version, timestamps, and output hashes.
- Registered in marketplace.json alongside existing plugins.

### Changed

**Breaking: Python >=3.11 required for materials-mcp**

- `requires-python` raised from `>=3.10` to `>=3.11`. This aligns with upstream `mp-api` (>=0.46.0) and `mpcontribs-client` which already require 3.11. Users on Python 3.10 will receive a clear install error. The `materials-simulation-skills` package retains `>=3.10` since its dependencies (`numpy`, `scipy`) do not require 3.11.

**Security: pymatgen >=2024.2.20 required**

- Minimum `pymatgen` version raised from `>=2024.1.0` to `>=2024.2.20` to exclude versions with a known remote code execution vulnerability (eval-based code execution in transformation parser).

**Configuration**

- `MPCONTRIBS_API_KEY` environment variable now supported for MPContribs authentication. Takes precedence over `MP_API_KEY` for MPContribs tools. Redacted in all error messages.
- Root `pyproject.toml` ruff `target-version` updated from `py310` to `py311`.
- CI matrix updated: Python 3.10 removed; tests run on 3.11 and 3.12.
- CI now runs `materials-data-workflows` tests alongside existing packages.

### Migration Guide

**Python 3.10 users:** Upgrade to Python 3.11 or later before updating `materials-mcp`. The install will fail with a clear version error on 3.10.

```bash
# Check your Python version
python3 --version

# If < 3.11, upgrade via your package manager or pyenv
pyenv install 3.12
pyenv local 3.12
```

**pymatgen users:** If you have `pymatgen` pinned below 2024.2.20, update it:

```bash
pip install --upgrade "pymatgen>=2024.2.20"
```

**MPContribs users:** Optionally set a dedicated API key for MPContribs:

```bash
export MPCONTRIBS_API_KEY="your-contribs-key"
```

If not set, the existing `MP_API_KEY` / `PMG_MAPI_KEY` resolution chain is used.
