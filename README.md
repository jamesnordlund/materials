# materials

A toolkit for computational materials science, designed for use with [Claude Code](https://docs.anthropic.com/en/docs/agents-and-tools/claude-code). It contains two packages:

- **`materials-mcp`** — An MCP server that gives Claude access to the [Materials Project](https://materialsproject.org/) and [MPContribs](https://mpcontribs.org/) APIs (search materials, retrieve crystal structures, analyze phase diagrams, query community datasets).
- **`materials-simulation-skills`** — 12 [Agent Skills](https://agentskills.io) that give Claude knowledge and scripts for numerical simulation workflows (stability analysis, solvers, meshing, time-stepping, optimization, validation, post-processing).

## Prerequisites

- [Claude Code](https://docs.anthropic.com/en/docs/agents-and-tools/claude-code)
- [uv](https://docs.astral.sh/uv/)
- Python 3.10+
- A [Materials Project API key](https://next-gen.materialsproject.org/api) (for the MCP server)

## Installation

Inside Claude Code, add the marketplace and install the plugin:

```
/plugin marketplace add jamesnordlund/materials
/plugin install materials-simulation-skills@jamesnordlund-materials
```

Then set your Materials Project API key so the MCP server can authenticate. Add this to your shell profile (e.g. `~/.zshrc` or `~/.bashrc`) so it persists across sessions:

```bash
export MP_API_KEY="your-key-here"
```

The plugin handles everything else — Claude Code downloads the skills and starts the MCP server automatically via `uv` (dependencies are resolved on first run).

## Local development

If you want to modify the skills or MCP server, clone the repo and point Claude Code at it directly:

```bash
git clone https://github.com/jamesnordlund/materials.git
claude --plugin-dir ./materials
```

To run the skill scripts outside of Claude Code, install all workspace dependencies:

```bash
cd materials
uv sync --all-extras
```

For examples and usage patterns, see the [materials-simulation-skills README](packages/materials-simulation-skills/README.md).

## Skills

| Category | Skill | Description |
|---|---|---|
| Core numerical | `numerical-stability` | CFL conditions, von Neumann analysis, stiffness detection |
| | `numerical-integration` | Integrator selection, IMEX schemes, adaptive step control |
| | `linear-solvers` | Solver/preconditioner selection, scaling, sparsity analysis |
| | `nonlinear-solvers` | Newton, quasi-Newton, fixed-point methods, convergence diagnostics |
| | `time-stepping` | Time-step planning, CFL coupling, checkpoint scheduling |
| | `differentiation-schemes` | Finite-difference stencils, boundary handling |
| | `mesh-generation` | Grid sizing, mesh quality metrics, mesh type selection |
| Simulation workflow | `simulation-validator` | Preflight checks, runtime monitoring, result validation |
| | `parameter-optimization` | DOE generation, surrogate models, optimizer selection |
| | `simulation-orchestrator` | Sweep generation, campaign management |
| | `post-processing` | Field extraction, derived quantities, statistical analysis |
| | `performance-profiling` | Bottleneck detection, optimization strategies |

## Usage examples

```
"Search Materials Project for stable lithium cobalt oxides with band gap above 2 eV."

"Check whether a time-step of 0.001 is stable for my phase-field simulation
with diffusivity 1e-5 and grid spacing 0.01."

"Generate a 50-point Latin Hypercube sample over 3 parameters."
```

## License

Apache-2.0
