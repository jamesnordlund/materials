---
name: mp-provenance-reporter
description: Build a reproducibility manifest documenting all MCP tool calls, database versions, input hashes, and timestamps used in an analysis session. Use when creating an audit trail for materials screening or reporting workflows to ensure results can be traced back to their data sources.
allowed-tools: Read, Bash, Write, Grep, Glob
---

# MP Provenance Reporter

## Goal

Given a log of MCP tool calls made during an analysis session, generate a structured provenance manifest that records data sources, database versions, input/output hashes, and timestamps for reproducibility and audit purposes.

## Requirements

- Python 3.11+
- NumPy, Pandas
- See `pyproject.toml` at the package root for dependency versions

## Inputs to Gather

| Input | Description | Example |
|-------|-------------|---------|
| Tool calls JSON | Array of {tool_name, args, response_hash} objects | Collected during analysis session |

## Workflow

1. **Collect tool call records** during the analysis session. Each record should include the tool name, arguments, and a SHA-256 hash of the response.
2. **Build the manifest** with `scripts/build_manifest.py`:
   ```bash
   python3 scripts/build_manifest.py --input tool_calls.json --json
   ```
3. **Review the manifest** -- verify database version consistency, check timestamps, and confirm input/output hashes.
4. **Save the manifest** alongside analysis outputs for reproducibility:
   ```bash
   python3 scripts/build_manifest.py --input tool_calls.json --out manifest.json
   ```

## Script Outputs (JSON Fields)

| Script | Key Outputs |
|--------|-------------|
| `scripts/build_manifest.py` | `manifest.inputs`, `manifest.tool_calls`, `manifest.db_version`, `manifest.timestamps`, `manifest.hash_of_outputs` |

## Error Handling

| Error | Cause | Resolution |
|-------|-------|------------|
| Exit code 1 | Invalid input file or malformed tool call records | Check that each record has `tool_name` and `args` fields |
| Missing `response_hash` | Tool call record lacks hash | Hash is set to null; manifest is still generated with a warning |

## Limitations

- The manifest records metadata about tool calls but does not store the actual response data.
- Database version is extracted from tool call metadata; if not present, it is recorded as null.
