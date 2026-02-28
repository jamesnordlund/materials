---
name: multiphase-field-imex
description: Advanced example demonstrating IMEX (implicit-explicit) splitting for multiphase-field problems. Use for strong stiffness/non-stiffness coupling, operator splitting error estimates, combining diffusion (implicit) and reaction (explicit) terms.
allowed-tools: Read, Bash, Write, Grep, Glob
---

# Multiphase-Field IMEX Splitting Example

## Goal

Provide a specialized example for IMEX (implicit-explicit) time integration of multiphase-field systems where stiff and non-stiff terms are cleanly separable, with practical guidance on splitting error estimation and scheme selection.

## Problem Overview

IMEX schemes are ideal for multiphase-field systems with **mixed stiffness**:

- **Diffusive (slow, stiff)**: Cahn-Hilliard-type gradients, implicit treatment for stability
- **Reaction (variable)**: Allen-Cahn potential, free-energy driving forces
  - When stiff (fast relaxation): implicit treatment required
  - When moderate: explicit treatment acceptable if coupled weakly
- **Coupling**: Typically moderate to strong between order parameters

### Splitting Strategy

```
∂u/∂t = STIFF(u) + NONSTIFF(u)
       = [diffusion + high-order gradients] + [reaction/potential terms]
       ≈ implicit          ≈ explicit
```

A first-order Godunov (simple) split:
```
u^(n+1) = EXPLICIT(dt) ∘ IMPLICIT(dt) [u^(n)]
```

Higher-order (Strang) splitting:
```
u^(n+1) = IMPLICIT(dt/2) ∘ EXPLICIT(dt) ∘ IMPLICIT(dt/2) [u^(n)]
```

## What This Example Demonstrates

### 1. Operator Splitting and Commutator Error
When you split ∂u/∂t = A(u) + B(u), the error is dominated by:
- **Splitting error**: Local ~ O(dt²) for Strang, O(dt) for Godunov
- **Commutator error**: [A, B] measures how much operators interfere
- **Combined error**: Often >> splitting error alone when coupling is strong

**Script**: `run_splitting_error.sh`
- Estimates commutator norm from coupled field dynamics
- Recommends substep refinement if error exceeds tolerance
- Suggests switching to higher-order split (Strang) or fully implicit if needed

### 2. IMEX Scheme Configuration
Deciding what to treat implicitly vs explicitly:

**Implicit candidates** (stiff):
- Diffusive terms (heat equation, Cahn-Hilliard)
- High-order gradient operators (4th order Laplacian, etc.)
- Stiff coupling operators

**Explicit candidates** (non-stiff or moderate):
- Reaction and potential terms (Allen-Cahn)
- Weak source terms
- Lower-order coupling

**Script**: `run_imex_split.sh`
- Demonstrates a concrete multiphase-field IMEX scheme
- Illustrates implicit solve for diffusion, explicit update for reaction
- Shows how to couple the two parts

### 3. When IMEX Beats Fully Implicit

| Scenario | Fully Implicit | IMEX | Winner |
|----------|----------------|------|--------|
| Most terms stiff, few non-stiff | Many Newton iters | Few, fast explicit steps | IMEX |
| All terms coupled and stiff | Required | Loses accuracy (splitting error) | Fully implicit |
| Weak coupling, stiff+non-stiff | Expensive linear solves | One implicit, one explicit | IMEX |
| High accuracy needed (TOL < 1e-8) | Robust if converges | Error from splitting | Fully implicit |

**Action**: Use IMEX when coupling is weak-to-moderate and stiffness is mostly in one term. Use fully implicit for strong coupling or high accuracy.

## Workflow

1. **Characterize stiffness structure**
   - Which terms are stiff? (typically diffusion)
   - Which are non-stiff? (typically reaction)
   - How strongly are they coupled?

2. **Choose splitting strategy**
   - **Godunov (1st order)**: Simplest, O(dt) error, use if coupling is weak
   - **Strang (2nd order)**: More accurate, O(dt²) error, standard choice
   - **Higher-order (3rd+)**: Rare; only if very tight accuracy needed

   Run `run_imex_split.sh` to see concrete example of Strang splitting.

3. **Estimate splitting error**
   ```bash
   bash examples/multiphase-field-imex/run_splitting_error.sh
   ```
   → Check if commutator-based error estimate is within tolerance

4. **Plan substeps**
   - If splitting error is large, refine by using multiple substeps per dt
   - E.g., dt → [dt/2, dt, dt/2] for Strang instead of single full step

5. **Decide implicit vs IMEX vs fully implicit**
   - If splitting error acceptable AND coupling moderate: use IMEX
   - If splitting error too large OR coupling very strong: switch to fully implicit
   - Reference: `multiphase-field` skill (fully implicit example)

## Output Interpretation

### Splitting Error Estimate
```
scheme: "strang"
dt: 1e-4
commutator_norm: 50.0  (rough measure of [A, B])
error_estimate: 5e-6   (≈ commutator × dt²)
target_error: 1e-6
substeps_required: 3   (split 5e-6 error into 3 equal parts)
recommendation: "Use 2–3 Strang substeps per dt or switch to implicit scheme"
```

→ If error_estimate << target: IMEX is safe
→ If error_estimate ≈ target: Monitor carefully or refine substeps
→ If error_estimate >> target: Use fully implicit or higher-order splitting

### IMEX Scheme Details
```
Step 1: Implicit (dt/2)
  ∂u/∂t = DIFFUSION(u)
  Solve: (I - dt/2 * L) u_half = u_n

Step 2: Explicit (dt)
  ∂u/∂t = REACTION(u_half)
  u_temp = u_half + dt * REACTION(u_half)

Step 3: Implicit (dt/2)
  ∂u/∂t = DIFFUSION(u_temp)
  Solve: (I - dt/2 * L) u_{n+1} = u_temp
```

→ Typical cost: 2 implicit solves (expensive) + 1 explicit step (cheap)
→ Total cost often < 5–10 Newton iterations for a fully implicit scheme

## When to Use IMEX vs Alternatives

### IMEX is best when:
- Stiffness localizes to one term (e.g., diffusion) or a few
- Non-stiff terms are expensive to handle implicitly (e.g., nonlinear reactions)
- Coupling is moderate (commutator error manageable)
- You want fast, stable explicit-like integration with implicit stability

### Use fully implicit when:
- Coupling is strong (all terms interact tightly)
- Target accuracy is very high (TOL < 1e-8)
- Stiffness is distributed across multiple terms
- You can afford 10–50 Newton iterations per step

### Use explicit when:
- No stiff terms (CFL limit is acceptable)
- Solution is smooth and dt can be aggressive
- Memory is extremely limited

## Key Insights

### Commutator and Error Growth
The error from splitting [A(u), B(u)] = A(B(u)) - B(A(u)) grows like:
```
error ≈ C * ||[A, B]|| * dt² (Strang)
```

If [A, B] is small (operators commute), error is negligible even for large dt.
If [A, B] is large (strong coupling), error dominates and you need finer dt or higher-order scheme.

**Action**: Check commutator norm with `run_splitting_error.sh`. If > 100, consider fully implicit.

### Substep Refinement
Instead of one big IMEX step, split into k substeps:
```
dt_sub = dt / k
for i in 1:k:
  u = IMEX_step(u, dt_sub)
```

Cost: k× expensive (k implicit solves), but error reduces by dt^(p+1), where p is order (1 for Godunov, 2 for Strang).
→ Often 2–3 substeps are enough to recover accuracy.

### Preconditioner Synergy
IMEX implicit solves (one term only) are often cheaper to precondition than fully implicit:
- Simpler operator structure (e.g., just Laplacian, not Laplacian + coupling)
- Better conditioning (fewer competing timescales)
- Fewer nonlinear Newton iterations (solving simpler problem)

**Action**: If IMEX linear solves are slow, try ILU or AMG preconditioner specifically for the implicit term alone.

## Example Scenario

**Allen-Cahn + Cahn-Hilliard coupling** (typical phase-field system):

```
∂φ/∂t = -Mφ ∇²(δF/δφ) + noise    [Cahn-Hilliard, conserved]
∂ψ/∂t = -Mψ (δF/δψ)              [Allen-Cahn, non-conserved]
```

**IMEX split**:
- Implicit: ∇⁴ (4th order, stiff diffusion in Cahn-Hilliard)
- Explicit: δF/δφ, δF/δψ (potential, nonlinear, moderate cost)

**Benefit**: Avoid Newton iteration on full nonlinear system; use linear solver for diffusion, explicit potential update.

## Related Core Skills

- **numerical-integration**: Integrator selection, general IMEX framework, error control
- **numerical-stability**: Stability region of IMEX schemes (linear stability analysis)
- **linear-solvers**: Efficient solve of implicit diffusion operator
- **nonlinear-solvers**: Newton iterations for implicit part (if nonlinear)
- **multiphase-field**: Fully implicit reference; comparison of cost vs accuracy

## Scripts in examples/multiphase-field-imex/

| Script | Purpose | Output |
|--------|---------|--------|
| `run_imex_split.sh` | Concrete Strang-split IMEX scheme for multiphase fields | Demonstrates integrated workflow |
| `run_splitting_error.sh` | Estimate commutator error, recommend substeps | Error estimate, advice on refinement |

## Example Data Files

None (scripts are self-contained with illustrative parameters).

## Limitations and Notes

- **Linear analysis**: Stability and error estimates assume linear operators. Nonlinear effects may amplify error
- **Commutator estimate**: Uses rough lower bound; actual error may be higher if nonlinearity is strong
- **Moderate coupling assumption**: Works well for weak-to-moderate coupling. Strong coupling may need fully implicit
- **No adaptive substep control**: Fixed substep count; true adaptive schemes adjust k based on error monitor

## Pre-IMEX Workflow Checklist

- [ ] Identify stiff vs non-stiff terms in your model
- [ ] Verify coupling is weak-to-moderate (not all terms fully coupled)
- [ ] Estimate commutator norm (or run `run_splitting_error.sh`)
- [ ] Compare splitting error vs target tolerance
- [ ] Plan number of IMEX substeps (typically 1–3 per physical dt)
- [ ] Confirm implicit operator can be solved efficiently (condition number, preconditioner)
- [ ] Run `run_splitting_error.sh` to validate choice before production
- [ ] Consider benchmark: compare IMEX vs fully implicit on short test problem

## References

- `../numerical-integration/references/imex_guidelines.md` – IMEX framework and scheme options
- `../numerical-integration/references/splitting_catalog.md` – Operator splitting methods and their orders
- `../numerical-stability/SKILL.md` – Linear stability regions of schemes
- `../linear-solvers/SKILL.md` – Efficient implicit solve strategies
- `multiphase-field/SKILL.md` – Fully implicit alternative for comparison

## Version History

- **v1.0.0** (2024-12-24): Initial example with IMEX splitting and error estimation for multiphase-field systems
