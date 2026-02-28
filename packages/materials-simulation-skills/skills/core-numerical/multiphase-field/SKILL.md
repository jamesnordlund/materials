---
name: multiphase-field
description: Advanced example integrating multiple core numerical skills for phase-field simulations. Use for combining numerical stability checks, adaptive time integration, linear/nonlinear solvers, and stiffness diagnostics on multiphase systems with conserved and non-conserved order parameters.
allowed-tools: Read, Bash, Write, Grep, Glob
---

# Multiphase-Field Simulation Example

## Goal

Provide a comprehensive, real-world example that integrates all core numerical methods (numerical-stability, numerical-integration, linear-solvers, nonlinear-solvers) for a complex multiphase-field problem with coupled stiff dynamics and multiple order parameters.

## Problem Overview

This is an advanced example for a multiphase-field simulation with:

- **Multiple order parameters**: Typically Allen-Cahn (non-conserved) and Cahn-Hilliard (conserved) equations
- **Realistic physics**: Diffusion-dominated microstructure evolution with stiff relaxation terms
- **Coupled dynamics**: Strong coupling between fields, leading to non-trivial stiffness structure
- **Practical challenges**: Stability limits, adaptive time stepping, matrix conditioning, and convergence diagnostics

### Scenario Parameters (Illustrative)

- **Domain**: 2D grid with dx = 2e-9 m (nanoscale)
- **Interface width**: ~5 dx (thin interface regime)
- **Effective diffusion**: D_eff = 1e-14 m²/s
- **Allen-Cahn relaxation**: k = 200 1/s (very stiff)
- **Trial time step**: dt = 1e-5 s (intentionally aggressive to test robustness)

## What This Example Demonstrates

### 1. Multiscale Stability Analysis
Integration with `numerical-stability` skill:
- CFL (Courant-Friedrichs-Lewy) number checks for each field
- Fourier number assessment for diffusive terms
- Reaction-rate stability for stiff relaxation (Allen-Cahn)
- Combined safety factor for coupled systems

**Script**: `run_stability_precheck.sh` (expect reaction limit violation on aggressive dt)

### 2. Stiffness and Integration Method Selection
Integration with `numerical-integration` skill:
- Detect stiffness from eigenvalue spectrum or reaction-rate timescale ratio
- Recommend integrator family (BDF, Rosenbrock, IMEX)
- Plan solver composition for stiff/non-stiff splitting if needed

**Script**: `run_integration_selector.sh`

### 3. Error Norm and Step Acceptance
Using core error norm machinery:
- Scaled error norm across multi-field vector
- Adaptive step acceptance/rejection with controller
- Local truncation error estimation

**Scripts**:
- `run_error_norm_multifield.sh` - Compute error norm on coupled state
- `run_adaptive_step_reject.sh` - Test step rejection and retry logic

### 4. Linear Solver Conditioning
Integration with `linear-solvers` skill:
- Assess condition number of coupled operator (e.g., implicit diffusion block)
- Identify ill-conditioning from stiff coupling
- Guide preconditioner selection

**Script**: `run_matrix_condition_coupled.sh`

### 5. Comprehensive Preflight
All diagnostics together:
- Stability check (CFL, Fourier, reaction limits)
- Integrator recommendation
- Matrix conditioning
- Error tolerance guidance

**Script**: `run_full_preflight.sh`

## When to Use This Example

- You are implementing a phase-field simulation (Allen-Cahn, Cahn-Hilliard, or hybrid)
- You need to verify stability before large-scale computations
- You want to understand interaction of stiffness, timestep, and error control
- You are diagnosing slow convergence or unexpected failures in coupled multiphase systems
- You want a reference for how to orchestrate multiple core skills

## Key Insights

### Stiffness Structure
Multiphase systems exhibit **separate stiffness timescales**:
- **Diffusion (slow)**: Governed by CFL with fast diffusion coefficient
- **Relaxation (fast)**: Governed by relaxation rate k (Allen-Cahn), can be 100–1000× faster

**Action**: Use CFL and Fourier limits conservatively, especially on reaction limit. Often dt is set by the stiffest term, not diffusion.

### Coupling Effects
When multiple fields are coupled:
- Condition number of implicit operator can be much worse than single-field case
- Block preconditioners (one field per block) sometimes help
- Weak coupling → simple operator splitting; strong coupling → fully implicit or IMEX-RK

**Action**: Check matrix condition number with `run_matrix_condition_coupled.sh`. If > 10⁶, consider preconditioner.

### Error Control in Multiphase Systems
With N order parameters, error norm reflects all fields:
- Relative error: depends on scaling across fields
- Use separate atol/rtol per field if amplitudes differ widely
- Step controller must account for all fields together

**Action**: Scale error norms by field magnitude. See `run_error_norm_multifield.sh` output.

## Workflow

1. **Characterize your system**
   - Identify all equations (Allen-Cahn, Cahn-Hilliard, etc.)
   - List parameters: diffusivity, relaxation rates, coupling strength
   - Estimate timescales for each process

2. **Run stability precheck** (expected to fail on aggressive dt)
   ```bash
   bash examples/multiphase-field/run_stability_precheck.sh
   ```
   → Identify which limit (CFL, Fourier, reaction) is tightest

3. **Adjust and recheck**
   ```bash
   bash examples/multiphase-field/run_stability_adjusted.sh
   ```
   → Run with reduced dt that passes all limits

4. **Select integration method**
   ```bash
   bash examples/multiphase-field/run_integration_selector.sh
   ```
   → Get recommendation for (implicit, explicit, IMEX)

5. **Check matrix properties**
   ```bash
   bash examples/multiphase-field/run_matrix_condition_coupled.sh
   ```
   → Assess condition number and guide preconditioner choice

6. **Run comprehensive preflight**
   ```bash
   bash examples/multiphase-field/run_full_preflight.sh
   ```
   → Verify all checks before production run

## Output Interpretation

### Stability Check
```
CFL_limit_diffusion:  0.25 (safe, dt_allowed ~ 1e-5 s)
Fourier_limit:        0.1  (safe)
Reaction_rate_limit:  0.01 (CRITICAL – dt should be < 5e-6 s)
```
→ Reaction rate is bottleneck; dt = 1e-5 s is too aggressive

### Integration Recommendation
```
stiffness: high
recommended: BDF2 or IMEX-RK (implicit-explicit Runge-Kutta)
notes: "Strong stiffness detected. Use implicit for stability."
```
→ Switch from explicit RK4 to implicit BDF or IMEX splitting

### Matrix Condition
```
condition_number: 1.2e7
diagnosis: "moderately ill-conditioned"
action: "Use preconditioner (ILU, algebraic multigrid) for iterative solver"
```
→ If condition > 10⁶, expect slow convergence without preconditioner

## Related Core Skills

- **numerical-stability**: CFL, Fourier, reaction rate checks; stability criteria catalog
- **numerical-integration**: Integrator selection, IMEX splitting, error control
- **linear-solvers**: Matrix conditioning, preconditioner guidance, solver selection
- **nonlinear-solvers**: Newton convergence, Jacobian diagnostics (for implicit schemes)
- **time-stepping**: Checkpoint and output scheduling for long-time integration

## Scripts in examples/multiphase-field/

| Script | Purpose | Output |
|--------|---------|--------|
| `run_full_preflight.sh` | Run all checks in sequence | Stability, integrator, matrix, error norms |
| `run_stability_precheck.sh` | CFL/Fourier/reaction checks (aggressive dt) | Expected violations on tight limits |
| `run_stability_adjusted.sh` | Stability with reduced, safe dt | All checks pass |
| `run_integration_selector.sh` | Integrator recommendation for stiff system | Recommended method and alternatives |
| `run_error_norm_multifield.sh` | Error norm across multi-field state vector | Scaled error, step acceptance criterion |
| `run_adaptive_step_reject.sh` | Adaptive controller with step rejection | Step acceptance/rejection decisions |
| `run_matrix_condition_coupled.sh` | Condition number of coupled implicit operator | Diagnosis and preconditioner guidance |

## Example Data Files

- `coupled_matrix.txt` – A sample coupled operator block (diffusion + coupling terms)

## Limitations and Notes

- **Parameters are illustrative**: Adjust to match your physical system (material, geometry, timescales)
- **2D domain assumed**: For 3D, scale dx and adjust CFL limits accordingly
- **Single-phase coupling**: Assumes moderate coupling; very stiff coupling may need fully implicit or specially tailored IMEX
- **Linear stability only**: This example focuses on linear stability and implicit-matrix properties. Nonlinear effects (solution blow-up, bifurcation) are not addressed
- **No adaptive mesh**: Assumes uniform grid; adaptive refinement may change stability bounds

## Pre-Simulation Checklist

- [ ] Understand your phase-field model (Allen-Cahn, Cahn-Hilliard, other)
- [ ] Identify all coupled equations and their stiffness timescales
- [ ] Set reasonable domain size and mesh resolution
- [ ] Run `run_full_preflight.sh` to identify critical limits
- [ ] Adjust dt to pass all stability checks
- [ ] Select integrator based on stiffness and preconditioner availability
- [ ] Confirm matrix condition number is acceptable for your solver
- [ ] Run a short test simulation with diagnostics enabled
- [ ] Verify convergence with finer mesh or tighter tolerances

## References

- `../numerical-stability/SKILL.md` – Stability criteria and CFL/Fourier/reaction limits
- `../numerical-integration/SKILL.md` – Integrator selection and IMEX splitting
- `../linear-solvers/SKILL.md` – Matrix conditioning and solver selection
- `../nonlinear-solvers/SKILL.md` – Convergence analysis and Jacobian diagnostics
- `../time-stepping/SKILL.md` – Time step planning and checkpointing

## Version History

- **v1.0.0** (2024-12-24): Initial example with 7 diagnostic scripts for multiphase-field systems
