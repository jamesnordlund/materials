---
name: insertion-electrode-metrics
description: Compute and summarize key performance metrics for insertion electrode materials. Use when evaluating cathode or anode candidates from Materials Project electrode data, comparing voltage profiles, gravimetric/volumetric capacity, energy density, and stability indicators.
allowed-tools: Read, Bash, Write, Grep, Glob
---

# Insertion Electrode Metrics

## Goal

Given a normalized electrode document from the Materials Project insertion electrodes endpoint, compute derived performance metrics (average voltage, capacities, energy density, stability flags) and summarize voltage curve characteristics for rapid cathode/anode evaluation.

## Requirements

- Python 3.11+
- NumPy, Pandas
- See `pyproject.toml` at the package root for dependency versions

## Inputs to Gather

| Input | Description | Example |
|-------|-------------|---------|
| Electrode document JSON | Normalized output from `mp_insertion_electrodes_search` | Saved MCP tool response |
| Voltage curve JSON (optional) | Array of {x, voltage_V} data points | Extracted from electrode document |

## Workflow

1. **Retrieve electrode data** using MCP tool `mp_insertion_electrodes_search` and save the response to a JSON file.
2. **Compute electrode metrics** with `scripts/electrode_metrics.py`:
   ```bash
   python3 scripts/electrode_metrics.py --input electrode_doc.json --json
   ```
3. **Summarize voltage curve** (optional) with `scripts/voltage_curve_summarizer.py`:
   ```bash
   python3 scripts/voltage_curve_summarizer.py --input voltage_curve.json --json
   ```
4. **Interpret results** -- check stability flags, compare capacity and energy density across candidates.
5. **Report** key metrics and any stability concerns to the user.

## Script Outputs (JSON Fields)

| Script | Key Outputs |
|--------|-------------|
| `scripts/electrode_metrics.py` | `material_id`, `working_ion`, `avg_voltage_V`, `grav_capacity_mAh_g`, `vol_capacity_mAh_cm3`, `energy_density_Wh_kg`, `stability_flags` |
| `scripts/voltage_curve_summarizer.py` | `n_steps`, `min_voltage_V`, `max_voltage_V`, `avg_voltage_V`, `plateaus`, `hysteresis_proxy_V` |

## Error Handling

| Error | Cause | Resolution |
|-------|-------|------------|
| Exit code 1 | Invalid input file or missing required fields | Check input file and verify it contains `material_id` and `working_ion` |
| Null metric values | Source electrode document missing optional fields | Fields are set to null and logged to stderr; results are still usable |

## Limitations

- Voltage curve summarizer assumes monotonically ordered capacity fraction data.
- Missing fields in electrode documents are substituted with null rather than causing failure.
