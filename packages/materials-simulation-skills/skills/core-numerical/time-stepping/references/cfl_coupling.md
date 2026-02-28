# CFL Coupling and Limits

Comprehensive guide for combining multiple stability constraints in time-dependent simulations.

## Fundamental Stability Limits

### Advection (CFL) Limit

For advection equation: ∂u/∂t + v·∇u = 0

```
dt_adv ≤ C_adv × dx / |v_max|

C_adv depends on scheme:
- First-order upwind: C_adv = 1.0
- Second-order central differences with RK2 or higher: C_adv ≈ 1.0
  (Note: FTCS (Forward Euler + Central Differences) is unconditionally unstable for advection; Strikwerda 2004, Ch. 3)
- Third-order upwind: C_adv ≈ 0.87
- Fourth-order central: C_adv ≈ 0.72
- WENO5: C_adv ≈ 0.5-1.0 (depends on smoothness)
```

### Diffusion (Fourier) Limit

For diffusion equation: ∂u/∂t = D∇²u

```
dt_diff ≤ C_diff × dx² / D

In 1D: C_diff = 0.5 (explicit Euler, e.g., FTCS)
In 2D: C_diff = 0.25 (explicit Euler)
In 3D: C_diff = 0.167 (explicit Euler)

Note: FTCS is conditionally stable for diffusion when dt ≤ dx²/(2D) in 1D;
it is unconditionally unstable for advection.
This is why FTCS is recommended for parabolic (diffusion) but not hyperbolic (advection) equations.

Higher-order time stepping:
- RK4: C_diff up to ~0.7/dim (factor of ~2.785 stability region for pure diffusion, divided by dimension)
- DuFort-Frankel: unconditionally stable
- Implicit: no limit (but accuracy limits apply)

**Note:** The RK4 diffusion limit comes from the intersection of the stability region of classical RK4 with the negative real axis.
```

### Reaction Limit

For stiff reactions: du/dt = R(u)

```
dt_react ≤ C_react / |λ_max|

Where λ_max is the largest eigenvalue of the reaction Jacobian.

For simple cases:
- First-order kinetics: λ = k (rate constant)
- Combustion: λ can be 10⁶ - 10¹² (very stiff!)
```

### Acoustic/Pressure Wave Limit

For compressible flow:

```
dt_acoustic ≤ dx / c

Where c = sound speed = sqrt(γP/ρ) or sqrt(K/ρ)
```

## Combining Multiple Limits

### Minimum Rule

The most conservative approach:

```
dt_limit = min(dt_adv, dt_diff, dt_react, dt_acoustic, ...)
dt = safety × dt_limit
```

**Safety factor:**
| Situation | Safety |
|-----------|--------|
| Conservative | 0.5 |
| Normal | 0.8 |
| Aggressive | 0.95 |
| Testing | 0.99 |

### Reciprocal Sum (More Conservative)

For coupled physics where limits interact:

```
1/dt_limit = 1/dt_adv + 1/dt_diff

Equivalent to: dt_limit = (dt_adv × dt_diff) / (dt_adv + dt_diff)
```

**Note:** This reciprocal sum is always strictly less than min(dt_adv, dt_diff) for positive values, because dt_adv + dt_diff > max(dt_adv, dt_diff), so (dt_adv × dt_diff) / (dt_adv + dt_diff) < min(dt_adv, dt_diff). This makes it MORE conservative than simply taking the minimum, accounting for additive interaction between stability constraints.

### Dimensional Coupling

In 2D/3D with different grid spacings:

```
1/dt_adv = |v_x|/dx + |v_y|/dy + |v_z|/dz

1/dt_diff = D × (1/dx² + 1/dy² + 1/dz²)
```

## Specific Physics Cases

### Advection-Diffusion

```
∂u/∂t + v·∇u = D∇²u

Two limits apply:
- CFL: dt ≤ dx / |v|
- Fourier: dt ≤ dx² / (2D)

Peclet number: Pe = |v| × L / D
- Pe >> 1: advection-dominated, CFL limits
- Pe << 1: diffusion-dominated, Fourier limits
- Pe ~ 1: both matter, use minimum
```

### Phase-Field with Diffusion

```
Allen-Cahn: ∂φ/∂t = M(ε²∇²φ - f'(φ))

Diffusion limit: dt ≤ dx² / (2Mε²)
Reaction limit: dt ≤ 1 / (M × max|f''(φ)|)

Interface width: W ~ ε
Resolution: dx ≤ W/3 for 3 points in interface
```

### Navier-Stokes (Incompressible)

```
Advection: dt_adv ≤ dx / |u_max|
Viscous: dt_visc ≤ dx² / (2ν)

Re = |u|L/ν
- High Re: dt_adv dominates
- Low Re: dt_visc may dominate (unusual for simulations)
```

### Elastodynamics

```
Wave speeds (distinguish by dimensionality):
- 1D bar wave speed: c_bar = sqrt(E/ρ)
- 3D P-wave (longitudinal) speed: c_p = sqrt((λ + 2μ)/ρ)
- 3D S-wave (shear) speed: c_s = sqrt(μ/ρ)

CFL: dt ≤ dx / c_max

For 3D elasticity, c_p > c_s, so P-wave speed typically limits the time step.
For explicit schemes, this is typically the limiting factor.

Reference: Graff (1975), Wave Motion in Elastic Solids, Ch. 1-2.
```

## Practical Computation

### Algorithm for dt Selection

```python
def compute_dt_limit(physics_params, grid):
    """Compute stable time step from all constraints."""
    limits = []

    # Advection
    if 'velocity' in physics_params:
        v_max = np.max(np.abs(physics_params['velocity']))
        dx_min = grid.min_spacing()
        dt_adv = 0.8 * dx_min / v_max
        limits.append(('advection', dt_adv))

    # Diffusion
    if 'diffusivity' in physics_params:
        D = physics_params['diffusivity']
        dx_min = grid.min_spacing()
        dim = grid.dimension
        dt_diff = 0.4 * dx_min**2 / (dim * D)
        limits.append(('diffusion', dt_diff))

    # Reaction
    if 'reaction_rate' in physics_params:
        k_max = physics_params['reaction_rate']
        dt_react = 0.5 / k_max
        limits.append(('reaction', dt_react))

    # Find limiting constraint
    dt_limit = min(dt for name, dt in limits)
    limiting = [name for name, dt in limits if dt == dt_limit][0]

    return dt_limit, limiting, limits
```

### Adaptive Recomputation

When to recompute dt:

| Event | Recompute? | Reason |
|-------|------------|--------|
| Start of simulation | Yes | Initial conditions |
| Each time step | Optional | If parameters change |
| Mesh refinement | Yes | dx changed |
| Material change | Yes | D, k changed |
| Large velocity change | Yes | CFL may change |

### Anisotropic Meshes

For grids with dx ≠ dy ≠ dz:

```
CFL (advection):
dt_adv ≤ 1 / (|v_x|/dx + |v_y|/dy + |v_z|/dz)

Fourier (diffusion):
dt_diff ≤ 0.5 / (D × (1/dx² + 1/dy² + 1/dz²))
```

**Critical:** Use the smallest spacing, not the average!

## Special Situations

### Locally Varying Properties

When D, v, or k vary in space:

```
Use maximum over all cells:
v_max = max over cells of |v(x)|
D_max = max over cells of D(x)
```

Or use local time stepping (more advanced).

### Implicit-Explicit (IMEX) Methods

When some terms are implicit:

```
Explicit part: CFL limit applies
Implicit part: No stability limit

Example (advection-diffusion):
- Implicit diffusion: removes dt_diff constraint
- Explicit advection: CFL still applies

dt ≤ dx / |v|  (only advection matters)
```

### Adaptive Mesh Refinement (AMR)

With multiple mesh levels:

```
Level 0: dx_0, dt_0 (coarse)
Level 1: dx_1 = dx_0/2, dt_1 = dt_0/2
Level 2: dx_2 = dx_0/4, dt_2 = dt_0/4
...

Subcycling: Fine levels take multiple steps per coarse step.
```

## Error-Based Adaptive Time Stepping

### Embedded Runge-Kutta Pairs

Embedded RK methods provide two solutions of different orders from the same function evaluations, enabling local error estimation without extra cost.

**Common Pairs:**

| Pair | Orders | Stages | FSAL | Reference |
|------|--------|--------|------|-----------|
| Heun-Euler | 2(1) | 2 | No | Simplest embedded pair |
| Bogacki-Shampine | 3(2) | 4 | Yes | MATLAB ode23 |
| Dormand-Prince | 5(4) | 7 | Yes | MATLAB ode45, scipy RK45 |
| DOP853 | 8(5,3) | 12 | Yes | High-accuracy problems |

**Error Estimate:**
```
err = ||y_high - y_low|| / (atol + rtol × ||y||)

Accept step if err ≤ 1
Reject step if err > 1
```

### PI/PID Step Size Controllers

Standard adaptive step control uses the error estimate to compute the next step size.

**Elementary Controller (I-controller):**
```
h_{n+1} = h_n × (tol / err_n)^(1/p)

where p = order of the lower-order method
```

**PI Controller (recommended):**
```
h_{n+1} = h_n × (tol / err_n)^β₁ × (tol / err_{n-1})^β₂

Typical parameters (Gustafsson 1991):
  β₁ = 0.7/p, β₂ = -0.4/p (for method of order p)
```

The PI controller uses history from the previous step to smooth step size changes and avoid oscillatory step size sequences.

**PID Controller:**
```
h_{n+1} = h_n × (err_{n-1}/err_n)^β₁ × (tol/err_n)^β₂ × (err_{n-1}/err_{n-2})^β₃

Typical: β₁ = 0.49/p, β₂ = 0.34/p, β₃ = 0.10/p
```

**Controller Selection Guide:**

| Controller | Smoothness | Robustness | When to Use |
|------------|------------|------------|-------------|
| I (elementary) | Poor | Good | Prototyping, simple problems |
| PI | Good | Very good | Default choice for production |
| PID | Very good | Excellent | Stiff problems, oscillatory error |

**Reference:** Gustafsson, K. (1991). Control-theoretic techniques for stepsize selection in explicit Runge-Kutta methods. *ACM Trans. Math. Softw.*, 17(4), 533-554.

### IMEX Time Step Selection

For IMEX methods treating stiff terms implicitly and non-stiff terms explicitly:

```
dt is limited by the EXPLICIT part only:
  dt ≤ CFL_explicit × dx / |v_explicit|

The implicit part has no stability restriction on dt,
but accuracy may degrade for very large dt.
```

**Practical guideline:** Start with the explicit CFL limit, then increase dt if accuracy permits. Monitor the implicit solver convergence - if it requires many iterations, dt may be too large for accuracy even though it's stable.

## Common Pitfalls

### Pitfall 1: Forgetting a Limit

```
Problem: Only checked CFL, forgot Fourier limit
Result: Instability when diffusion dominates
Fix: Always compute ALL relevant limits
```

### Pitfall 2: Using Average Instead of Minimum

```
Problem: dt = (dt_adv + dt_diff) / 2
Result: Too large dt, instability
Fix: dt = min(dt_adv, dt_diff)
```

### Pitfall 3: Ignoring Anisotropy

```
Problem: Used dx_avg instead of min(dx, dy, dz)
Result: dt too large in refined direction
Fix: Use minimum spacing in each limit formula
```

### Pitfall 4: Not Recomputing After Changes

```
Problem: Fixed dt throughout simulation
Result: Instability when parameters change
Fix: Recompute dt when physics changes significantly
```

## Diagnostics and Monitoring

### Courant Number Monitoring

```
C = v × dt / dx

Should be: C ≤ C_max (typically ~0.5-0.9)

If C > 1: Likely unstable
If C << 0.1: Inefficient, could use larger dt
```

### Fourier Number Monitoring

```
F = D × dt / dx²

Should be: F ≤ F_max (typically ~0.25-0.5 in 2D)

If F > 0.5/dim: Likely unstable (explicit)
If F << 0.01: Very conservative, check if needed
```

### Stability Margin

```
margin = dt_limit / dt_used

Healthy: margin ≥ 1.1 (10% safety)
Warning: margin = 1.0-1.1 (borderline)
Danger: margin < 1.0 (unstable!)
```

## Quick Reference

### Common Limits Table

| Physics | Limit Formula | Typical C |
|---------|---------------|-----------|
| Advection | C × dx / v | 0.5-0.9 |
| Diffusion (1D) | C × dx² / D | 0.5 |
| Diffusion (2D) | C × dx² / D | 0.25 |
| Diffusion (3D) | C × dx² / D | 0.167 |
| Sound waves | dx / c | 0.9 |
| Stiff reaction | 1 / λ_max | 0.1-0.5 |
| Phase-field | dx² / (Mε²) | 0.1-0.25 |

### Combined Example

```
Problem: 2D advection-diffusion with reaction
v = 1.0 m/s, D = 0.01 m²/s, k = 100 /s
dx = 0.01 m

dt_adv = 0.8 × 0.01 / 1.0 = 0.008 s
dt_diff = 0.25 × 0.01² / 0.01 = 0.0025 s
dt_react = 0.5 / 100 = 0.005 s

dt_limit = min(0.008, 0.0025, 0.005) = 0.0025 s
Limiting factor: diffusion
```
