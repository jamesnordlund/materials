# materials-data-workflows

Agent skills for materials science data-to-decision workflows. This package provides deterministic CLI scripts and playbooks for screening, ranking, and reporting on materials data retrieved from the Materials Project and MPContribs APIs via the `materials-mcp` MCP server.

## Overview

The skills in this package operate on JSON data produced by MCP tools. They do not call the Materials Project API directly. Each skill consists of a playbook (`SKILL.md`) that guides Claude through a multi-step workflow and CLI scripts that perform deterministic computations.

## Prerequisites

- Python 3.11 or higher
- numpy >= 1.24
- pandas >= 2.0.0

## Installation

### Via Claude Code Plugin

```
/plugin marketplace add jamesnordlund/materials
/plugin install materials-data-workflows@jamesnordlund-materials
```

### From Source

```bash
git clone https://github.com/jamesnordlund/materials.git
cd materials
uv sync --all-extras
```

## Skills

### mp-pareto-screening

Multi-objective Pareto frontier screening for materials candidates.

**Scripts:**

- `pareto_frontier.py` -- Computes the Pareto frontier from a set of candidate materials with configurable objectives (minimize/maximize) and constraint filters. Outputs frontier members, dominated candidates, crowding distances, and dominance ranks.
- `export_candidates.py` -- Exports frontier results to CSV or JSON with unit-suffixed column headers and deterministic row ordering.

**Example workflow:**
1. Use `mp_summary_search_advanced` (MCP tool) to find Li-Fe-O candidates with `energy_above_hull_max: 0.05`.
2. Save results to `candidates.json`.
3. Run: `python pareto_frontier.py --input candidates.json --objectives "min:energy_above_hull_eV,max:band_gap_eV" --json`
4. Run: `python export_candidates.py --input frontier.json --format csv --out results.csv`

### insertion-electrode-metrics

Electrode performance evaluation for insertion electrode candidates.

**Scripts:**

- `electrode_metrics.py` -- Computes derived metrics from normalized electrode documents: average voltage (V), gravimetric capacity (mAh/g), volumetric capacity (mAh/cm3), energy density (Wh/kg), and stability flags.
- `voltage_curve_summarizer.py` -- Analyzes voltage curves to detect plateaus, compute min/max/average voltage, and estimate hysteresis.

**Example workflow:**
1. Use `mp_insertion_electrodes_search` (MCP tool) to find Li insertion cathodes in Li-Mn-O.
2. Save an electrode document to `electrode.json`.
3. Run: `python electrode_metrics.py --input electrode.json --json`
4. Run: `python voltage_curve_summarizer.py --input voltage_curve.json --json`

### mp-provenance-reporter

Reproducibility manifest generation for materials workflows.

**Scripts:**

- `build_manifest.py` -- Generates a reproducibility manifest from a list of tool call records. The manifest includes input file hashes, tool call details, database version, timestamps, and a combined output hash.

**Example workflow:**
1. After a multi-step analysis, collect tool call records.
2. Save to `tool_calls.json`.
3. Run: `python build_manifest.py --input tool_calls.json --json`

## Script Interface Convention

All scripts follow a consistent CLI pattern:

```
python script.py --input <path> [--json] [--out <path>]
```

- `--input PATH` -- Path to input JSON file
- `--json` -- Emit JSON output to stdout (logs go to stderr)
- `--out PATH` -- Write output to a file instead of stdout

**Exception:** `export_candidates.py` requires two additional arguments: `--format <csv|json>` (required) and `--out <path>` (required, not optional).

Exit codes: 0 = success, 1 = input error, 2 = no results after filtering.

Output JSON uses unit-suffixed key names (e.g., `energy_above_hull_eV`, `avg_voltage_V`), replaces NaN/Infinity with `null`, and uses explicit `null` for missing fields.

## Running Tests

```bash
cd /path/to/materials
uv run --package materials-data-workflows pytest packages/materials-data-workflows -v --tb=short
```

## Related Packages

- **[materials-mcp](../materials-mcp/)** -- MCP server providing the data access tools that feed into these workflows
- **[materials-simulation-skills](../materials-simulation-skills/)** -- Numerical simulation skills (solvers, meshing, time-stepping)

## License

Apache License 2.0
