---
name: mp-pareto-screening
description: Screen and rank materials using multi-objective Pareto frontier analysis. Use when comparing candidates across competing properties (e.g., stability vs band gap), filtering by constraints, and exporting ranked shortlists from Materials Project search results.
allowed-tools: Read, Bash, Write, Grep, Glob
---

# MP Pareto Screening

## Goal

Given a set of candidate materials retrieved from the Materials Project, compute the Pareto frontier across user-specified objectives, apply optional constraints, and export a ranked shortlist for downstream analysis.

## Requirements

- Python 3.11+
- NumPy, Pandas
- See `pyproject.toml` at the package root for dependency versions

## Inputs to Gather

| Input | Description | Example |
|-------|-------------|---------|
| Candidates JSON | Array of material objects with numeric properties | Output of `mp_summary_search_advanced` saved to file |
| Objectives | Comma-separated min/max specs per property | `min:energy_above_hull_eV,max:band_gap_eV` |
| Constraints (optional) | Inequality filters on properties | `energy_above_hull_eV<=0.05,band_gap_eV>=1.5` |
| Output format | JSON or CSV | `--json` or `--format csv` |

## Workflow

1. **Retrieve candidates** using MCP tools (e.g., `mp_summary_search_advanced`) and save the response records to a JSON file.
2. **Run Pareto screening** with `scripts/pareto_frontier.py`:
   ```bash
   python3 scripts/pareto_frontier.py --input candidates.json --objectives "min:energy_above_hull_eV,max:band_gap_eV" --json
   ```
3. **Review frontier** -- inspect the `frontier` array for Pareto-optimal candidates and `scores` for crowding distances.
4. **Export results** with `scripts/export_candidates.py`:
   ```bash
   python3 scripts/export_candidates.py --input frontier.json --format csv --out candidates.csv
   ```
5. **Report** the top candidates with their trade-off metrics to the user.

## Script Outputs (JSON Fields)

| Script | Key Outputs |
|--------|-------------|
| `scripts/pareto_frontier.py` | `metadata`, `objectives`, `constraints_applied`, `frontier`, `dominated`, `scores` |
| `scripts/export_candidates.py` | `status`, `path`, `rows` |

## Error Handling

| Error | Cause | Resolution |
|-------|-------|------------|
| Exit code 1 | Invalid input file or malformed JSON | Check input file path and format |
| Exit code 2 | No candidates remain after constraint filtering | Relax constraints or broaden search |
| Missing objective field | Requested field not present in candidates | Verify field names match MCP output keys |

## Limitations

- Pareto frontier computation is O(n^2 * k) where n = candidates, k = objectives. Performance target: <5s for 10,000 candidates with 3 objectives.
- Candidates with NaN values in objective fields are excluded from frontier computation.
