# MCP Materials Server

A Model Context Protocol (MCP) server that provides AI assistants with access to materials science databases, starting with the [Materials Project](https://materialsproject.org/) API.

Built with the [MCP Python SDK](https://github.com/modelcontextprotocol/python-sdk) using FastMCP.

## Features

### Tools (10)

| Tool                           | Description                                                              |
| ------------------------------ | ------------------------------------------------------------------------ |
| `search_materials`             | Search materials by chemical formula (e.g., "Fe2O3", "LiFePO4")          |
| `get_structure`                | Retrieve crystal structure in CIF, POSCAR, or JSON format                |
| `get_properties`               | Get comprehensive material properties (band gap, formation energy, etc.) |
| `compare_materials`            | Side-by-side comparison of multiple materials                            |
| `search_by_elements`           | Find materials containing/excluding specific elements                    |
| `search_by_band_gap`           | Search by electronic band gap range (eV)                                 |
| `get_similar_structures`       | Find materials with similar crystal structures                           |
| `get_phase_diagram`            | Phase stability analysis for chemical systems                            |
| `get_elastic_properties`       | Mechanical properties (bulk/shear modulus, Debye temperature)            |
| `search_by_elastic_properties` | Find materials by mechanical property ranges                             |

### Resources (2)

| Resource        | URI                           | Description                                     |
| --------------- | ----------------------------- | ----------------------------------------------- |
| Periodic Table  | `materials://periodic-table`  | Element data with atomic numbers and masses     |
| Crystal Systems | `materials://crystal-systems` | The 7 crystal systems with symmetry constraints |

### Prompts (3)

| Prompt                       | Description                                       |
| ---------------------------- | ------------------------------------------------- |
| `analyze_material`           | Comprehensive analysis workflow for a material ID |
| `find_battery_materials`     | Search for battery electrode candidates           |
| `compare_alloy_compositions` | Compare phases in an alloy system                 |

## Installation

### Prerequisites

- Python 3.11 or higher
- Materials Project API key ([get one free](https://materialsproject.org/api))

### Setup

```bash
# Clone or navigate to the project
cd mcp-materials-server

# Create virtual environment
python -m venv .venv

# Activate virtual environment
# On Windows:
.venv\Scripts\activate
# On macOS/Linux:
source .venv/bin/activate

# Install the package
pip install -e ".[dev]"
```

### Set API Key

```bash
# On Windows (PowerShell):
$env:MP_API_KEY = "your_api_key_here"

# On Windows (CMD):
set MP_API_KEY=your_api_key_here

# On macOS/Linux:
export MP_API_KEY="your_api_key_here"
```

## Usage

### Run the Server

```bash
# Using the installed command
mcp-materials

# Or run directly
python -m mcp_materials.server
```

### Claude Desktop Integration

Add to your Claude Desktop configuration file:

**Location:**

- Windows: `%APPDATA%\Claude\claude_desktop_config.json`
- macOS: `~/Library/Application Support/Claude/claude_desktop_config.json`

**Configuration:**

```json
{
  "mcpServers": {
    "materials": {
      "command": "python",
      "args": ["-m", "mcp_materials.server"],
      "cwd": "D:\\path\\to\\mcp-materials-server",
      "env": {
        "MP_API_KEY": "your_api_key_here"
      }
    }
  }
}
```

After adding the configuration, restart Claude Desktop.

## Example Queries

Once connected to Claude, you can ask:

### Basic Searches

- "Search for lithium cobalt oxide materials"
- "Find materials with formula Fe2O3"
- "Search for materials containing Li, Fe, and O"

### Property Lookups

- "Get the properties of mp-149 (Silicon)"
- "What is the band gap of mp-19017?"
- "Get the crystal structure of mp-149 in CIF format"

### Advanced Analysis

- "Find materials with band gap between 1.5 and 2.5 eV"
- "Get the elastic properties of silicon (mp-149)"
- "Generate a phase diagram for the Li-Fe-O system"
- "Compare the properties of LiCoO2 and LiFePO4"
- "Find stiff materials with bulk modulus > 200 GPa"

### Research Workflows

- "Analyze material mp-149 comprehensively"
- "Find potential Li-ion battery cathode materials"
- "Compare phases in the Fe-Cr-Ni alloy system"

## Development

### Run Tests

```bash
# Run all tests
pytest

# Run with verbose output
pytest -v

# Run specific test class
pytest tests/test_server.py::TestToolFunctions -v
```

### Lint Code

```bash
# Check for issues
ruff check src/

# Auto-format
ruff format src/
```

### Project Structure

```
mcp-materials-server/
├── src/
│   └── mcp_materials/
│       ├── __init__.py          # Package version
│       └── server.py            # MCP server (10 tools, 2 resources, 3 prompts)
├── tests/
│   ├── __init__.py
│   ├── conftest.py              # Pytest configuration
│   └── test_server.py           # Comprehensive test suite
├── pyproject.toml               # Project configuration
├── claude_desktop_config.example.json
├── .gitignore
└── README.md
```

## API Reference

### Tool Details

#### `search_materials(formula, max_results=10)`

Search by chemical formula. Returns material IDs, band gaps, formation energies, and stability.

#### `get_structure(material_id, format="cif")`

Get crystal structure. Formats: `cif`, `poscar`, `json`.

#### `get_properties(material_id)`

Full property set: composition, symmetry, electronic, thermodynamic properties.

#### `compare_materials(material_ids)`

Compare list of materials side-by-side.

#### `search_by_elements(elements, exclude_elements=None, max_results=10)`

Find materials by element composition.

#### `search_by_band_gap(min_gap=0, max_gap=10, direct_gap_only=False, max_results=10)`

Search by band gap range in eV.

#### `get_similar_structures(material_id, max_results=5)`

Find materials with same space group.

#### `get_phase_diagram(elements)`

Build phase diagram for chemical system. Returns stable/unstable phases with decomposition products.

#### `get_elastic_properties(material_id)`

Mechanical properties: bulk modulus, shear modulus (Voigt/Reuss/VRH), Poisson ratio, Debye temperature.

#### `search_by_elastic_properties(min_bulk_modulus=None, max_bulk_modulus=None, min_shear_modulus=None, max_shear_modulus=None, max_results=10)`

Filter materials by mechanical properties.

## Roadmap

- [ ] Add AFLOW database integration
- [ ] Add OQMD database support
- [ ] Add electronic structure (DOS, band structure) tools
- [ ] Add XRD pattern simulation
- [ ] Add synthesis route suggestions
- [ ] Add surface/interface properties

## License

MIT

## References

- [Model Context Protocol](https://modelcontextprotocol.io/)
- [MCP Python SDK](https://github.com/modelcontextprotocol/python-sdk)
- [Materials Project](https://materialsproject.org/)
- [Materials Project API](https://api.materialsproject.org/)
- [pymatgen](https://pymatgen.org/)

## Author

Hesham Salama
