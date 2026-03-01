# materials

A toolkit for computational materials science, designed for use with [Claude Code](https://docs.anthropic.com/en/docs/agents-and-tools/claude-code). It contains three packages:

- **`materials-mcp`** — An MCP server that gives Claude access to the [Materials Project](https://materialsproject.org/) and [MPContribs](https://mpcontribs.org/) APIs (search materials, retrieve crystal structures, analyze phase diagrams, query community datasets, search insertion electrodes, and retrieve provenance metadata). Provides 23 tools and 3 domain-specific prompts.
- **`materials-data-workflows`** — [Agent Skills](https://agentskills.io) for data-to-decision workflows: multi-objective Pareto screening, insertion electrode metrics, and provenance/reproducibility reporting.
- **`materials-simulation-skills`** — 14 [Agent Skills](https://agentskills.io) for numerical simulation workflows (stability analysis, solvers, meshing, time-stepping, optimization, validation, post-processing).

## Prerequisites

- [Claude Code](https://docs.anthropic.com/en/docs/agents-and-tools/claude-code)
- [uv](https://docs.astral.sh/uv/)
- Python 3.11+ (required by `materials-mcp` and `materials-data-workflows`; `materials-simulation-skills` supports 3.10+)
- A [Materials Project API key](https://next-gen.materialsproject.org/api) (for the MCP server)

## Installation

First, set your Materials Project API key. Add this to your shell profile (e.g. `~/.zshrc` or `~/.bashrc`) so it persists across sessions:

```bash
export MP_API_KEY="your-key-here"
```

Optionally, set a dedicated key for MPContribs (falls back to `MP_API_KEY` if not set):

```bash
export MPCONTRIBS_API_KEY="your-contribs-key"
```

Then inside Claude Code, add the marketplace and install the plugins:

```
/plugin marketplace add jamesnordlund/materials
/plugin install materials-mcp@jamesnordlund-materials
/plugin install materials-simulation-skills@jamesnordlund-materials
/plugin install materials-data-workflows@jamesnordlund-materials
```

The `materials-mcp` plugin registers an MCP server that Claude Code starts automatically. It uses `uv` to resolve dependencies on first launch and starts the server process. The two skills plugins register agent skills that Claude can invoke during conversations.

## Local development

If you want to modify the skills or MCP server, clone the repo and add it as a local marketplace:

```bash
git clone https://github.com/jamesnordlund/materials.git
```

Then inside Claude Code:

```
/plugin marketplace add ./materials
/plugin install materials-mcp@jamesnordlund-materials
```

To run the skill scripts outside of Claude Code, install all workspace dependencies:

```bash
cd materials
uv sync --all-extras
```

For examples and usage patterns, see the individual package READMEs:
- [materials-mcp README](packages/materials-mcp/README.md)
- [materials-data-workflows README](packages/materials-data-workflows/README.md)
- [materials-simulation-skills README](packages/materials-simulation-skills/README.md)

## Skills

### Data-to-Decision (materials-data-workflows)

| Skill | Description |
|---|---|
| `mp-pareto-screening` | Multi-objective Pareto frontier screening with constraint filtering and CSV/JSON export |
| `insertion-electrode-metrics` | Electrode performance metrics (voltage, capacity, energy density) and voltage curve analysis |
| `mp-provenance-reporter` | Reproducibility manifest generation with input/output hashes and database version tracking |

### Simulation (materials-simulation-skills)

| Category | Skill | Description |
|---|---|---|
| Core numerical | `numerical-stability` | CFL conditions, von Neumann analysis, stiffness detection |
| | `numerical-integration` | Integrator selection, IMEX schemes, adaptive step control |
| | `linear-solvers` | Solver/preconditioner selection, scaling, sparsity analysis |
| | `nonlinear-solvers` | Newton, quasi-Newton, fixed-point methods, convergence diagnostics |
| | `time-stepping` | Time-step planning, CFL coupling, checkpoint scheduling |
| | `differentiation-schemes` | Finite-difference stencils, boundary handling |
| | `mesh-generation` | Grid sizing, mesh quality metrics, mesh type selection |
| Phase-field | `multiphase-field` | End-to-end phase-field workflow integrating stability, solvers, and meshing |
| | `multiphase-field-imex` | IMEX splitting for coupled stiff/non-stiff phase-field terms |
| Simulation workflow | `simulation-validator` | Preflight checks, runtime monitoring, result validation |
| | `parameter-optimization` | DOE generation, surrogate models, optimizer selection |
| | `simulation-orchestrator` | Sweep generation, campaign management |
| | `post-processing` | Field extraction, derived quantities, statistical analysis |
| | `performance-profiling` | Bottleneck detection, optimization strategies |

## Usage examples

```
"Search Materials Project for stable lithium cobalt oxides with band gap above 2 eV."

"Screen Li-Fe-O cathode candidates with energy above hull <= 0.05 eV/atom.
Rank by Pareto tradeoff of stability vs band gap. Export top 50 to CSV."

"Find top Li insertion cathodes in Li-Mn-O and compute theoretical capacity
and average voltage."

"Check whether a time-step of 0.001 is stable for my phase-field simulation
with diffusivity 1e-5 and grid spacing 0.01."

"Generate a 50-point Latin Hypercube sample over 3 parameters."
```

## License

Apache-2.0
