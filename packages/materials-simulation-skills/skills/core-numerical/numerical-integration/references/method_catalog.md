# Method Catalog

Comprehensive reference for time integration methods in ODE/PDE simulations.

## Explicit Methods (Non-Stiff)

### Runge-Kutta Family

| Method | Order | Stages | Error Est. | Best For |
|--------|-------|--------|------------|----------|
| Euler | 1 | 1 | No | Prototyping only |
| RK2 (Heun) | 2 | 2 | No | Simple problems |
| RK4 (Classical) | 4 | 4 | No | Fixed-step, smooth |
| RK45 (Dormand-Prince) | 5(4) | 7 (FSAL) | Yes | General adaptive |
| DOP853 | 8(5,3) | 12 | Yes | High accuracy |

#### RK45 (Dormand-Prince)
- **Default choice** for non-stiff problems
- 7 stages with FSAL (First Same As Last), giving 6 function evaluations per accepted step
- Embedded 4th-order method for error estimation
- Recommended tolerances: rtol=1e-3, atol=1e-6

#### DOP853
- 8th-order with 5th and 3rd-order error estimates
- Excellent for high-precision requirements
- More expensive per step but fewer steps needed
- Use when rtol < 1e-6 is required

### Adams-Bashforth (Multi-step)

| Order | Points | Formula |
|-------|--------|---------|
| 1 | 1 | y_{n+1} = y_n + h*f_n |
| 2 | 2 | y_{n+1} = y_n + h*(3f_n - f_{n-1})/2 |
| 3 | 3 | y_{n+1} = y_n + h*(23f_n - 16f_{n-1} + 5f_{n-2})/12 |
| 4 | 4 | y_{n+1} = y_n + h*(55f_n - 59f_{n-1} + 37f_{n-2} - 9f_{n-3})/24 |

**Advantages:**
- Only one function evaluation per step
- Efficient for smooth, non-stiff problems

**Disadvantages:**
- Requires startup procedure
- Less robust for discontinuous forcing
- Needs variable-step modification for adaptivity

## Implicit Methods (Stiff)

### BDF (Backward Differentiation Formulas)

| Order | Stability | Formula |
|-------|-----------|---------|
| BDF1 | A-stable | y_{n+1} = y_n + h*f_{n+1} |
| BDF2 | A-stable | (3y_{n+1} - 4y_n + y_{n-1})/2 = h*f_{n+1} |
| BDF3 | A(α)-stable | (11y_{n+1} - 18y_n + 9y_{n-1} - 2y_{n-2})/6 = h*f_{n+1} |
| BDF4 | A(α)-stable | Higher order, smaller stability region |
| BDF5 | A(α)-stable | Use only for mildly stiff |
| BDF6 | A(α)-stable (α ≈ 17.8°) | Usable for mildly stiff problems with eigenvalues near negative real axis; narrow stability wedge limits applicability |

**Note on BDF6:** While BDF6 has the smallest stability region of the BDF family, it is A(α)-stable with α ≈ 17.8 degrees and can be used effectively for mildly stiff problems where eigenvalues are concentrated near the negative real axis. For highly stiff problems or eigenvalues far from the real axis, use lower-order BDF or L-stable methods (Hairer & Wanner (1996), "Solving Ordinary Differential Equations II: Stiff and Differential-Algebraic Problems," Springer, Section V.2).

**When to use:**
- Large eigenvalue spread (> 100)
- Chemistry with fast/slow reactions
- Diffusion-dominated problems

**Considerations:**
- Requires nonlinear solver (Newton)
- Jacobian needed (analytical or numerical)
- Order reduction near stability boundary

### Radau IIA

| Order | Stages | Properties |
|-------|--------|------------|
| Radau IIA-3 | 2 | L-stable, 3rd order |
| Radau IIA-5 | 3 | L-stable, 5th order |

**Properties:**
- L-stable (strong damping of stiff modes)
- Excellent for very stiff problems
- Superconvergent at endpoints

**Use when:**
- BDF order reduction is problematic
- DAE (differential-algebraic) systems
- Very stiff chemistry

### Rosenbrock Methods

**Characteristics:**
- Linearly implicit (one Jacobian factorization per step)
- No nonlinear iteration needed
- Excellent for moderate stiffness

| Method | Order | Stages |
|--------|-------|--------|
| ROS2 | 2 | 2 |
| ROS3P | 3 | 3 |
| ROS4 | 4 | 4 |
| RODAS | 4 | 6 |

**Advantages over BDF:**
- No iteration convergence issues
- Fixed number of Jacobian evaluations
- Better for time-varying Jacobians

## Structure-Preserving Methods

### Symplectic Integrators

For Hamiltonian systems: dp/dt = -∂H/∂q, dq/dt = ∂H/∂p

| Method | Order | Type |
|--------|-------|------|
| Symplectic Euler | 1 | Explicit |
| Störmer-Verlet | 2 | Explicit |
| Ruth's 3rd order | 3 | Explicit |
| Forest-Ruth | 4 | Explicit |

**Use for:**
- Long-time molecular dynamics
- Orbital mechanics
- Oscillatory systems with energy conservation

**Properties:**
- Exactly conserve symplectic structure
- Near-conservation of Hamiltonian for exponentially long times
- Time-reversible (symmetric methods)

### Geometric Integrators

| Property | Methods |
|----------|---------|
| Volume-preserving | Implicit midpoint, Gauss-Legendre |
| Energy-preserving | Discrete gradient methods |
| Momentum-preserving | Variational integrators |

## Strong Stability Preserving (SSP) Methods

SSP methods preserve nonlinear stability properties (e.g., TVD, positivity) of the forward Euler method under a modified time step restriction.

### SSP Runge-Kutta

| Method | Order | Stages | SSP Coefficient | Effective CFL |
|--------|-------|--------|-----------------|---------------|
| SSP-RK(2,2) | 2 | 2 | 1.0 | 1.0 × Euler CFL |
| SSP-RK(3,3) | 3 | 3 | 1.0 | 1.0 × Euler CFL |
| SSP-RK(5,4) | 4 | 5 | 1.508 | 1.508 × Euler CFL |
| SSP-RK(10,4) | 4 | 10 | 6.0 | 6.0 × Euler CFL |

**SSP-RK(3,3) (Shu-Osher form):**
```
u⁽¹⁾ = u^n + Δt F(u^n)
u⁽²⁾ = 3/4 u^n + 1/4 u⁽¹⁾ + 1/4 Δt F(u⁽¹⁾)
u^{n+1} = 1/3 u^n + 2/3 u⁽²⁾ + 2/3 Δt F(u⁽²⁾)
```

**When to use:**
- Hyperbolic conservation laws with shocks
- Problems requiring TVD or positivity preservation
- Combined with WENO or TVD spatial discretizations

**Reference:** Gottlieb, S., Shu, C.-W., & Tadmor, E. (2001). Strong stability-preserving high-order time discretization methods. *SIAM Review*, 43(1), 89-112.

### SSP Multi-step

SSP versions of Adams-Bashforth and BDF methods exist but have more restrictive SSP coefficients than SSP-RK. Generally prefer SSP-RK for SSP applications.

## Exponential Integrators

For problems of the form du/dt = Lu + N(u) where L is a stiff linear operator.

### Core Idea

Solve the linear part exactly using the matrix exponential, and treat the nonlinear part with polynomial approximation.

### Common Methods

| Method | Order | Type | Key Feature |
|--------|-------|------|-------------|
| ETD-Euler | 1 | Single-step | Simplest exponential method |
| ETD-RK2 (Cox-Matthews) | 2 | Multi-stage | Good balance of cost/accuracy |
| ETD-RK4 (Cox-Matthews) | 4 | Multi-stage | High accuracy, 4 φ-function evaluations |
| ETDRK4 (Kassam-Trefethen) | 4 | Multi-stage | Contour integral for numerical stability |

### φ-Functions

Exponential integrators use φ-functions:
```
φ₀(z) = e^z
φ₁(z) = (e^z - 1) / z
φ₂(z) = (e^z - 1 - z) / z²
```

### When to Use

- Stiff linear part with moderate nonlinearity (reaction-diffusion, Allen-Cahn)
- Spectral or pseudo-spectral spatial discretizations (diagonal L in Fourier space)
- Problems where implicit solvers for L are expensive

**Reference:** Hochbruck, M. & Ostermann, A. (2010). Exponential integrators. *Acta Numerica*, 19, 209-286.

## Energy-Stable SAV Methods

The Scalar Auxiliary Variable (SAV) approach reformulates energy-dissipative PDEs to enable unconditionally energy-stable, linear implicit schemes.

### Classical SAV

Introduce auxiliary variable r(t) = √(E[φ] + C) where E is the nonlinear energy functional. The reformulated system is linear in (φ, r) at each time step.

### Modern Variants

| Variant | Key Feature | Reference |
|---------|-------------|-----------|
| SAV (Shen et al. 2018) | Original formulation, requires C > 0 | Shen, Xu, Yang (2018) |
| E-SAV (2020) | Exponential SAV, removes positivity constraint | Liu & Li (2020) |
| R-SAV / Relaxed SAV (2022) | Relaxation step improves accuracy | Jiang et al. (2022) |
| gPAV (2024) | Generalized positive auxiliary variable | Yang & Ju (2024) |

### When to Use

- Phase-field models (Cahn-Hilliard, Allen-Cahn, phase-field crystal)
- Gradient flow problems requiring unconditional energy stability
- Large time steps where implicit-explicit methods may violate energy dissipation

**Reference:** Shen, J., Xu, J., & Yang, J. (2018). The scalar auxiliary variable (SAV) approach for gradient flows. *J. Comput. Phys.*, 353, 407-416.

## IMEX Methods

For problems with mixed stiff/non-stiff terms: du/dt = f_stiff(u) + f_nonstiff(u)

### Common IMEX-RK Schemes

| Scheme | Implicit | Explicit | Order |
|--------|----------|----------|-------|
| IMEX-Euler | BE | FE | 1 |
| IMEX-SSP2 | Trapezoid | SSP-RK2 | 2 |
| IMEX-ARK2 | SDIRK | ERK | 2 |
| IMEX-ARK4 | SDIRK | ERK | 4 |

### IMEX-BDF

| Order | Properties |
|-------|------------|
| SBDF1 | BE + AB1 extrapolation |
| SBDF2 | BDF2 + AB2 extrapolation |
| SBDF3 | BDF3 + AB3 extrapolation |

## Selection Guide

### Quick Decision Table

| Stiffness | Accuracy | Smoothness | Recommended |
|-----------|----------|------------|-------------|
| Non-stiff | Moderate | Smooth | RK45 |
| Non-stiff | High | Smooth | DOP853 |
| Non-stiff | Low | Smooth | Adams-Bashforth |
| Stiff | Moderate | Any | BDF |
| Very stiff | Any | Any | Radau IIA |
| Moderate stiff | Any | Jacobian available | Rosenbrock |
| Mixed | Any | Split possible | IMEX |
| Hamiltonian | Long-time | Oscillatory | Symplectic |

### Cost Comparison

| Method | f evals/step | Jacobian evals | Linear solves |
|--------|--------------|----------------|---------------|
| RK45 | 6 | 0 | 0 |
| BDF2 | 1 + Newton | 1 per few steps | 1 per Newton |
| Radau5 | 3 + Newton | 1 per step | 3 per Newton |
| Rosenbrock4 | 4 | 1 | 4 |

## Stability Regions

### Explicit Methods
- RK4: Extends to Re(λh) ≈ -2.8 on real axis
- RK45: Similar to RK4
- Adams-Bashforth: Smaller regions, decreasing with order

### Implicit Methods
- BDF1-2: A-stable (entire left half-plane)
- BDF3-5: A(α)-stable (wedge-shaped regions)
- Radau: L-stable (A-stable + stiff decay)

## Implementation Notes

### Jacobian Handling
1. **Analytical**: Most accurate, requires code derivation
2. **Automatic differentiation**: Accurate, some overhead
3. **Numerical (finite difference)**: Simple, may be inaccurate for stiff
4. **Jacobian-free (GMRES)**: For very large systems

### Step Size Limits
- Minimum dt: Floating-point precision, typically 1e-15 * t_current
- Maximum dt: Physical time scale or output frequency
- Safety factor: Typically 0.8-0.9 for adaptive methods
