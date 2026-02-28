# Sweep Strategies

Guidance for designing effective parameter sweeps.

## Method Selection Guide

### Grid (Full Factorial)

**When to use**:
- Low dimension (1-3 parameters)
- Need exact corner values
- Reproducible, deterministic coverage
- Want to visualize response surfaces

**Limitations**:
- Exponential growth: `n^d` configurations
- Inefficient for high dimensions
- May miss optimal in center regions

**Example**:
```bash
# 2D grid: 5 x 5 = 25 runs
--params "dt:1e-4:1e-2:5,kappa:0.1:1.0:5" --method grid
```

### Linspace (Uniform Sampling)

**When to use**:
- Same as grid (equivalent for regular spacing)
- Preferred terminology for 1D sweeps
- Want evenly spaced samples

**Example**:
```bash
# 1D sweep: 10 evenly spaced dt values
--params "dt:1e-4:1e-2:10" --method linspace
```

### Latin Hypercube Sampling (LHS)

**When to use**:
- High dimension (4+ parameters)
- Limited budget
- Space-filling coverage important
- Don't need exact corner values

**Properties**:
- Each parameter range divided into n equal intervals
- Exactly one sample per interval per dimension
- Good space-filling with O(n) samples

**Example**:
```bash
# 4D LHS: 20 samples covering 4 parameters
--params "dt:1e-4:1e-2,kappa:0.1:1.0,M:1e-6:1e-4,W:0.5:2.0" \
    --method lhs --samples 20
```

### Sobol Sequences

Sobol low-discrepancy sequences provide more uniform space coverage than LHS, especially for sensitivity analysis.

**When to use**:
- Need to compute Sobol sensitivity indices
- Deterministic, reproducible quasi-random coverage
- Incremental sampling (powers of 2 preferred)

**Example**:
```bash
# Use with parameter-optimization DOE generator
python doe_generator.py --method sobol --params 4 --budget 64
```

### Halton Sequences

Halton sequences are quasi-random sequences based on different prime bases per dimension.

**When to use**:
- Low to moderate dimensions (2-10)
- Need to add points incrementally (any count, not just powers of 2)
- Simpler alternative to Sobol

**Limitations**:
- Correlation increases in high dimensions (d > 10)
- Use scrambled Halton for better uniformity

```python
from scipy.stats import qmc
sampler = qmc.Halton(d=4, scramble=True, seed=42)
points = sampler.random(n=50)
```

### Quasi-Random vs LHS Comparison

| Property | LHS | Sobol | Halton |
|----------|-----|-------|--------|
| Deterministic | No (random) | Yes | Yes |
| Space-filling | Good | Excellent | Good |
| Incremental | Hard to extend | Powers of 2 | Any count |
| Sensitivity analysis | Indirect | Direct (Saltelli) | Indirect |
| Best dimensions | 3-20 | 2-15 | 2-10 |
| Efficiency gain over random | ~2-5× | ~5-10× | ~3-7× |

## Dimension vs Budget Guidelines

| Dimension | Grid (n=5) | Recommended | Method |
|-----------|------------|-------------|--------|
| 1 | 5 | 10-20 | linspace |
| 2 | 25 | 20-50 | grid |
| 3 | 125 | 30-100 | grid or LHS |
| 4 | 625 | 40-200 | LHS |
| 5 | 3,125 | 50-300 | LHS |
| 10 | 9.7M | 100-1000 | LHS |

**Rule of thumb**: For LHS, use at least `10 * d` samples where `d` is dimension.

## Adaptive Strategies

### Two-Stage Refinement

1. **Coarse sweep**: Cover full range with few points
2. **Fine sweep**: Zoom into promising region

```bash
# Stage 1: Coarse
--params "dt:1e-5:1e-1:5" --output-dir coarse_sweep

# Stage 2: Fine (after identifying dt ~ 1e-3 is best)
--params "dt:5e-4:2e-3:10" --output-dir fine_sweep
```

### Importance Sampling

Focus samples in high-importance regions:
- Near boundaries/constraints
- Around known optima
- In high-curvature regions

## Parameter Scaling

### Linear vs Logarithmic

Use **logarithmic** scaling when:
- Parameter spans orders of magnitude
- Physical effect is proportional to log(parameter)
- Examples: dt, tolerance, learning rate

```python
# Convert log sweep to linear sweep_generator input
import numpy as np
log_values = np.logspace(-4, -2, 5)  # [1e-4, 3e-4, 1e-3, 3e-3, 1e-2]
```

### Normalized Space

For optimization, normalize all parameters to [0, 1]:
- Improves optimizer behavior
- Makes distance metrics meaningful
- Required for some surrogate models

## Handling Constraints

### Parameter Constraints

Some parameter combinations may be invalid:
- Diffusion stability (dimension-dependent):
  - 1D: `dt < dx^2 / (2*D)`
  - 2D: `dt < dx^2 / (4*D)`
  - 3D: `dt < dx^2 / (6*D)`
- `kappa + M < max_value`

**Approach 1**: Generate, then filter
```python
configs = generate_sweep(...)
valid = [c for c in configs if is_valid(c)]
```

**Approach 2**: Constrained sampling
- Rejection sampling
- Constrained LHS algorithms

## Reproducibility Checklist

- [ ] Set random seed for LHS: `--seed 42`
- [ ] Record exact parameter bounds
- [ ] Save manifest.json with all settings
- [ ] Version control base configuration
- [ ] Document any post-filtering
