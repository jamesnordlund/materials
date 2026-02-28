# materials-mcp

An MCP (Model Context Protocol) server that gives Claude direct access to the [Materials Project](https://materialsproject.org/) and [MPContribs](https://mpcontribs.org/) APIs. Search materials, retrieve crystal structures, analyze phase diagrams, and query community-contributed materials data—all from within Claude.

## Overview

**materials-mcp** is a specialized MCP server for computational materials science. It bridges Claude's reasoning capabilities with two major materials informatics platforms:

- **Materials Project**: A comprehensive database of computational materials properties including thermodynamics, electronic structure, and crystal structures
- **MPContribs**: Community-contributed experimental and calculated materials data

The server provides 18 specialized tools and 3 domain-specific prompts for high-throughput materials screening and design workflows.

## Prerequisites

- Python 3.10 or higher
- A [Materials Project API key](https://materialsproject.org/api) (free registration required)

## Installation

### As a Standalone Package

Install from PyPI:

```bash
pip install materials-mcp
```

Or with MPContribs support (optional):

```bash
pip install materials-mcp[contribs]
```

### From Source

Clone the repository and install in development mode:

```bash
git clone https://github.com/jamesnordlund/materials.git
cd materials/packages/materials-mcp
pip install -e .
```

With development dependencies:

```bash
pip install -e ".[contribs,dev]"
```

## Configuration

### Setting Your API Key

The server requires a Materials Project API key. Set it as an environment variable:

```bash
export MP_API_KEY="your-api-key-here"
```

Or, if you're using the legacy pymatgen key format:

```bash
export PMG_MAPI_KEY="your-api-key-here"
```

The server checks for `MP_API_KEY` first, then falls back to `PMG_MAPI_KEY`.

**Get your API key:**
1. Sign up at [materialsproject.org](https://materialsproject.org)
2. Navigate to Account > API Settings
3. Generate or copy your API key

### Optional: MPContribs Support

To use the MPContribs tools, install the optional dependency:

```bash
pip install materials-mcp[contribs]
```

If MPContribs is not installed, the corresponding tools will return a helpful error message with installation instructions.

## Running the Server

### Standalone

Start the server directly:

```bash
mcp-materials
```

The server will listen on `stdio` and log diagnostic messages to stderr. You'll see confirmation that tools and resources have been registered.

### With Claude Code

The easiest way to use materials-mcp is through the [Claude Code](https://docs.anthropic.com/en/docs/agents-and-tools/claude-code) plugin system. The plugin automatically handles server startup and dependency resolution.

Inside Claude Code:

```
/plugin install materials-mcp
```

Then reference Materials Project data directly in your prompts.

### Programmatic Usage

You can also import and compose the server in Python:

```python
from mcp_materials.server import compose_server

server = compose_server()
server.run()
```

## Available Tools

### Materials Project Tools (10 tools)

All return JSON-formatted results.

#### `search_materials(formula: str, max_results: int = 10)`
Search the Materials Project database by chemical formula.

**Example:**
```
formula: "Fe2O3"
max_results: 5
```

Returns material IDs, formation energy, band gap, density, crystal system, stability, and more.

#### `get_structure(material_id: str, output_format: str = "cif")`
Retrieve the crystal structure for a material.

**Parameters:**
- `material_id`: Materials Project ID (e.g., "mp-149" for Silicon)
- `output_format`: "cif", "poscar", or "json" (default: "cif")

**Example:**
```
material_id: "mp-149"
output_format: "cif"
```

Returns the structure in your chosen format.

#### `get_properties(material_id: str)`
Fetch comprehensive properties: thermodynamics, electronic structure, symmetry, magnetism.

**Example:**
```
material_id: "mp-149"
```

Returns a detailed property dictionary including:
- Formation energy and stability metrics
- Band gap and electronic properties
- Crystal system and space group
- Density and volume

#### `compare_materials(material_ids: list[str])`
Compare properties of multiple materials side by side.

**Example:**
```
material_ids: ["mp-149", "mp-66", "mp-1"]
```

Returns a table comparing key properties across materials.

#### `search_by_elements(elements: list[str], max_results: int = 10)`
Search for materials containing specific elements.

**Example:**
```
elements: ["Li", "Fe", "O"]
max_results: 20
```

Returns stable and metastable phases in the system.

#### `search_by_band_gap(min_gap: float = 0.0, max_gap: float = 5.0, max_results: int = 10)`
Find materials with band gaps in a specified range.

**Example:**
```
min_gap: 1.5
max_gap: 3.0
max_results: 10
```

Returns semiconductors and insulators in the gap range.

#### `get_similar_structures(material_id: str, max_results: int = 5)`
Find structurally similar materials using the Materials Project structure matcher.

**Example:**
```
material_id: "mp-149"
max_results: 5
```

Returns similar materials ranked by structure distance.

#### `get_phase_diagram(elements: list[str])`
Retrieve or construct a phase diagram for a chemical system.

**Example:**
```
elements: ["Li", "O"]
```

Returns stable phases, energies, and phase boundaries. Useful for understanding phase stability and equilibrium compositions.

#### `get_elastic_properties(material_id: str)`
Retrieve elastic properties including elastic tensor, bulk modulus, and shear modulus.

**Example:**
```
material_id: "mp-149"
```

Returns full elastic tensors and derived mechanical properties.

#### `search_by_elastic_properties(min_bulk_modulus: float = 0.0, max_bulk_modulus: float = 500.0, max_results: int = 10)`
Find materials with specific elastic properties.

**Example:**
```
min_bulk_modulus: 100.0
max_bulk_modulus: 300.0
max_results: 10
```

Returns materials ranked by bulk modulus.

### MPContribs Tools (8 tools)

Community-contributed materials data. Requires `materials-mcp[contribs]` installation.

#### `contribs_search_projects()`
List all available MPContribs projects and their contributors.

#### `contribs_get_project(project_name: str)`
Get metadata and statistics for a specific project.

**Example:**
```
project_name: "boltztrap"
```

#### `contribs_search_contributions(project_name: str, max_results: int = 20)`
Search contributions within a specific project.

**Example:**
```
project_name: "phonons"
max_results: 20
```

#### `contribs_get_contribution(object_id: str, max_results: int = 20)`
Retrieve a specific contribution by ID.

#### `contribs_get_table(object_id: str, table_name: str)`
Extract tabular data from a contribution.

#### `contribs_get_structure(object_id: str, output_format: str = "cif")`
Get a crystal structure associated with a contribution.

#### `contribs_get_attachment(object_id: str, attachment_name: str)`
Download an attached file from a contribution.

#### `contribs_get_project_stats(project_name: str)`
Get statistics and metadata about a project.

### Resources

Reference data available via the MCP resource interface:

- **`cmi://ref/periodic-table`**: Full periodic table with atomic properties
- **`cmi://ref/crystal-systems`**: Crystal system definitions and properties

## Specialized Prompts

The server includes three domain-specific prompt templates for common workflows:

### `catalyst_feasibility_study(material_id: str)`
Generates a structured workflow for evaluating a material as a catalyst candidate, including electronic structure assessment, thermodynamic stability, benchmarking, and scalability rating.

**Example usage in Claude:**
```
"Conduct a feasibility study on mp-149 for hydrogen evolution reaction catalysis."
```

### `hydrogen_storage_screening(target_element: str = "Mg")`
Creates a screening protocol for identifying hydrogen storage materials containing a target element, with filtering for metastability and mechanical properties.

### `sorbent_selection_workflow(base_system: str = "Ca,O,Si")`
Designs a material selection workflow for carbon capture sorbents, including phase stability mapping, thermodynamic analysis, and competing phase assessment.

## Usage Examples

### Search for Lithium Compounds

```python
# In Claude, type:
"Search for lithium iron phosphate in the Materials Project.
 Tell me about its stability and band gap."
```

The server will use `search_materials("LiFePO4")` and `get_properties()` to provide detailed results.

### Analyze Phase Stability

```
"What are the stable phases in the Li-O system?
 Use the phase diagram to identify equilibrium compositions."
```

Uses `get_phase_diagram(["Li", "O"])` to construct and analyze stability relationships.

### Find Band Gap Semiconductors

```
"Find materials with band gaps between 2.0 and 3.0 eV.
 Compare their elastic properties to understand mechanical stability."
```

Uses `search_by_band_gap()` and `get_elastic_properties()` for comprehensive screening.

### Access Community Data

```
"What are the available phonon datasets in MPContribs?
 Get the phonon dispersion for the most-studied material."
```

Uses `contribs_search_projects()` and `contribs_get_contribution()` to access community data.

## Output Format

All tools return JSON-formatted results for structured parsing:

```json
{
  "material_id": "mp-149",
  "formula": "Si",
  "band_gap_eV": 1.12,
  "formation_energy_eV_atom": 0.0,
  "crystal_system": "cubic",
  "space_group_symbol": "Fd-3m",
  "is_stable": true
}
```

Errors include helpful diagnostic information:

```json
{
  "error": "MP_API_KEY environment variable not set. Get your key at https://materialsproject.org/api",
  "error_category": "missing_configuration"
}
```

## Error Handling

The server includes comprehensive error handling:

- **Missing API key**: Clear instructions to obtain and configure your API key
- **Invalid inputs**: Validation errors for formulas, material IDs, and parameter ranges
- **API timeouts**: Graceful timeout handling (60-second limit per request)
- **Missing dependencies**: Instructions to install optional packages (mpcontribs-client)

All errors are returned as JSON objects with `error` and `error_category` fields for programmatic handling.

## Troubleshooting

### "MP_API_KEY environment variable not set"

Set your API key:

```bash
export MP_API_KEY="your-api-key-here"
```

Verify it's set:

```bash
echo $MP_API_KEY
```

### "mp-api and/or pymatgen not installed"

Install required dependencies:

```bash
pip install mp-api pymatgen
```

Or reinstall materials-mcp:

```bash
pip install --upgrade materials-mcp
```

### "mpcontribs-client not installed"

The MPContribs tools require an optional dependency:

```bash
pip install materials-mcp[contribs]
```

### Server Won't Start

Check that all dependencies are installed:

```bash
pip list | grep -E "mcp|mp-api|pymatgen|pandas"
```

Ensure your API key is set and valid. Verify by testing with curl:

```bash
curl -X GET "https://api.materialsproject.org/materials/summary/mp-149" \
  -H "X-API-KEY: $MP_API_KEY"
```

## Performance Considerations

- **API Calls**: Each tool call makes a request to Materials Project or MPContribs APIs. Requests have a 60-second timeout.
- **Result Limits**: Use the `max_results` parameter to limit data transfer. The default is 10-20 results.
- **Phase Diagrams**: Computing phase diagrams for systems with many elements can take several seconds.
- **Rate Limiting**: Materials Project and MPContribs have rate limits. The server respects these with polite request spacing.

## Security

- **API Keys**: Your API key is read from the environment and never logged or transmitted insecurely. Store it safely in your shell profile or credential manager.
- **Input Sanitization**: All user inputs (formulas, material IDs, etc.) are validated and sanitized before use.
- **Output Filtering**: Sensitive data (credentials, internal URLs) is filtered from error messages.

## Contributing

This package is part of the [materials toolkit](https://github.com/jamesnordlund/materials). For bug reports, feature requests, or contributions, please open an issue or pull request on GitHub.

## Related Packages

- **[materials-simulation-skills](../materials-simulation-skills/)**: Agent skills for numerical simulation workflows (solvers, meshing, time-stepping, optimization, validation)
- **[Materials Project](https://materialsproject.org/)**: The underlying database and API
- **[pymatgen](https://pymatgen.org/)**: Materials structure analysis toolkit
- **[MPContribs](https://mpcontribs.org/)**: Community materials data platform

## License

Apache License 2.0. See the [LICENSE](../../LICENSE) file for details.

## Citation

If you use materials-mcp in your research, please cite:

```
materials-mcp: An MCP server for Materials Project and MPContribs APIs.
https://github.com/jamesnordlund/materials
```

## Support

For questions or issues:

1. Check the [Materials Project API documentation](https://api.materialsproject.org)
2. Review the [materials toolkit repository](https://github.com/jamesnordlund/materials)
3. Open an issue on [GitHub](https://github.com/jamesnordlund/materials/issues)

---

Built with the [Model Context Protocol](https://modelcontextprotocol.io/) for Claude.
