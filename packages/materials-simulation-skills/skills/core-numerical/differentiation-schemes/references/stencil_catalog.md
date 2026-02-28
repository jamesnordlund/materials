# Stencil Catalog

Comprehensive reference for finite difference stencil coefficients.

## First Derivative Stencils

### Central Differences

Symmetric stencils, no directional bias.

**2nd Order (3-point):**
```
Offsets: [-1, 0, +1]
Coefficients: [-1/2, 0, 1/2] / dx

f'(x) ≈ (f(x+dx) - f(x-dx)) / (2dx)
Error: O(dx²)
```

**4th Order (5-point):**
```
Offsets: [-2, -1, 0, +1, +2]
Coefficients: [1/12, -2/3, 0, 2/3, -1/12] / dx

f'(x) ≈ (-f(x+2dx) + 8f(x+dx) - 8f(x-dx) + f(x-2dx)) / (12dx)
Error: O(dx⁴)
```

**6th Order (7-point):**
```
Offsets: [-3, -2, -1, 0, +1, +2, +3]
Coefficients: [-1/60, 3/20, -3/4, 0, 3/4, -3/20, 1/60] / dx
Error: O(dx⁶)
```

### Forward Differences (One-Sided)

For left boundaries or upwind schemes.

**1st Order (2-point):**
```
Offsets: [0, +1]
Coefficients: [-1, 1] / dx

f'(x) ≈ (f(x+dx) - f(x)) / dx
Error: O(dx)
```

**2nd Order (3-point):**
```
Offsets: [0, +1, +2]
Coefficients: [-3/2, 2, -1/2] / dx

f'(x) ≈ (-3f(x) + 4f(x+dx) - f(x+2dx)) / (2dx)
Error: O(dx²)
```

**3rd Order (4-point):**
```
Offsets: [0, +1, +2, +3]
Coefficients: [-11/6, 3, -3/2, 1/3] / dx
Error: O(dx³)
```

**4th Order (5-point):**
```
Offsets: [0, +1, +2, +3, +4]
Coefficients: [-25/12, 4, -3, 4/3, -1/4] / dx
Error: O(dx⁴)
```

### Backward Differences (One-Sided)

For right boundaries (mirror of forward).

**1st Order (2-point):**
```
Offsets: [-1, 0]
Coefficients: [-1, 1] / dx
```

**2nd Order (3-point):**
```
Offsets: [-2, -1, 0]
Coefficients: [1/2, -2, 3/2] / dx
```

## Second Derivative Stencils

### Central Differences

**2nd Order (3-point):**
```
Offsets: [-1, 0, +1]
Coefficients: [1, -2, 1] / dx²

f''(x) ≈ (f(x+dx) - 2f(x) + f(x-dx)) / dx²
Error: O(dx²)
```

**4th Order (5-point):**
```
Offsets: [-2, -1, 0, +1, +2]
Coefficients: [-1/12, 4/3, -5/2, 4/3, -1/12] / dx²

f''(x) ≈ (-f(x+2dx) + 16f(x+dx) - 30f(x) + 16f(x-dx) - f(x-2dx)) / (12dx²)
Error: O(dx⁴)
```

**6th Order (7-point):**
```
Offsets: [-3, -2, -1, 0, +1, +2, +3]
Coefficients: [1/90, -3/20, 3/2, -49/18, 3/2, -3/20, 1/90] / dx²
Error: O(dx⁶)
```

### One-Sided Second Derivative

**2nd Order Forward (4-point):**
```
Offsets: [0, +1, +2, +3]
Coefficients: [2, -5, 4, -1] / dx²
Error: O(dx²)
```

**2nd Order Backward (4-point):**
```
Offsets: [-3, -2, -1, 0]
Coefficients: [-1, 4, -5, 2] / dx²
Error: O(dx²)
```

## Higher Derivative Stencils

### Third Derivative

**2nd Order Central (5-point):**
```
Offsets: [-2, -1, 0, +1, +2]
Coefficients: [-1/2, 1, 0, -1, 1/2] / dx³
Error: O(dx²)
```

**4th Order Central (7-point):**
```
Offsets: [-3, -2, -1, 0, +1, +2, +3]
Coefficients: [1/8, -1, 13/8, 0, -13/8, 1, -1/8] / dx³
Error: O(dx⁴)
```

### Fourth Derivative

**2nd Order Central (5-point):**
```
Offsets: [-2, -1, 0, +1, +2]
Coefficients: [1, -4, 6, -4, 1] / dx⁴
Error: O(dx²)
```

**4th Order Central (7-point):**
```
Offsets: [-3, -2, -1, 0, +1, +2, +3]
Coefficients: [-1/6, 2, -13/2, 28/3, -13/2, 2, -1/6] / dx⁴
Error: O(dx⁴)
```

## Mixed and Cross Derivatives

### First Cross Derivative (∂²f/∂x∂y)

**2nd Order (4-point):**
```
f_xy ≈ (f(x+dx,y+dy) - f(x+dx,y-dy) - f(x-dx,y+dy) + f(x-dx,y-dy)) / (4 dx dy)

Stencil (in 2D):
    [+1]      [-1]
       [0]
    [-1]      [+1]
```

**4th Order:**
```
Uses 12 points in a wider pattern
Error: O(dx⁴ + dy⁴)
```

## Compact (Padé) Schemes

Higher accuracy with smaller stencils by solving implicit system.

### 4th Order Compact First Derivative

```
α f'_{i-1} + f'_i + α f'_{i+1} = (a/dx)(f_{i+1} - f_{i-1})

where α = 1/4, a = 3/4
```

Requires solving tridiagonal system for f'.

### 6th Order Compact First Derivative

```
α f'_{i-1} + f'_i + α f'_{i+1} = (a/dx)(f_{i+1} - f_{i-1}) + (b/dx)(f_{i+2} - f_{i-2})

where α = 1/3, a = 14/9, b = 1/9
```

**Notation Convention:** We follow Lele's notation throughout. The tridiagonal system coefficients (α on the left-hand side, a and b on the right-hand side) are exactly as specified in Lele (1992), Table 1, for the 6th-order centered scheme. The solution procedure involves solving a tridiagonal linear system for the derivative values at all grid points.

**Reference:** Lele, S. K. "Compact finite difference schemes with spectral-like resolution," *J. Comput. Phys.* **103**(1), 16-42 (1992), Table 1.

### Advantages of Compact Schemes

| Property | Explicit | Compact |
|----------|----------|---------|
| Stencil width | Wide | Narrow |
| Operations | O(n) | O(n) but solve required |
| Spectral resolution | Good | Excellent |
| Boundary handling | Simple | Requires closure |

## Upwind Schemes

For advection-dominated problems with u > 0.

### First-Order Upwind

```
u > 0: f'(x) ≈ (f(x) - f(x-dx)) / dx  (backward)
u < 0: f'(x) ≈ (f(x+dx) - f(x)) / dx  (forward)
```

Stable but highly diffusive.

### Second-Order Upwind

```
u > 0: f'(x) ≈ (3f(x) - 4f(x-dx) + f(x-2dx)) / (2dx)
u < 0: f'(x) ≈ (-3f(x) + 4f(x+dx) - f(x+2dx)) / (2dx)
```

Less diffusive, may oscillate.

### Third-Order Upwind (QUICK)

```
f'(x) ≈ (2f(x+dx) + 3f(x) - 6f(x-dx) + f(x-2dx)) / (6dx)
```

Good balance of accuracy and stability.

## Stencil Properties Summary

### First Derivative

| Order | Points | Width | Coefficients Sum |
|-------|--------|-------|------------------|
| 2 central | 3 | 2dx | 0 |
| 4 central | 5 | 4dx | 0 |
| 6 central | 7 | 6dx | 0 |
| 1 one-sided | 2 | dx | 0 |
| 2 one-sided | 3 | 2dx | 0 |

### Second Derivative

| Order | Points | Width | Coefficients Sum |
|-------|--------|-------|------------------|
| 2 central | 3 | 2dx | 0 |
| 4 central | 5 | 4dx | 0 |
| 6 central | 7 | 6dx | 0 |

### Stability Properties

| Scheme | Dispersion | Dissipation |
|--------|------------|-------------|
| Central | Low | None |
| Upwind | Moderate | High |
| Compact | Very low | None |
| WENO | Low | Adaptive |

## Summation-by-Parts (SBP) Operators

SBP operators are finite difference operators that satisfy a discrete analogue of integration by parts, enabling provable energy stability when paired with Simultaneous Approximation Terms (SATs) for boundary conditions.

### Structure

An SBP first-derivative operator D₁ satisfies:

```
H D₁ + D₁ᵀ H = E

where:
  H = positive-definite diagonal (or block-diagonal) norm matrix
  E = boundary quadrature matrix (E = diag(-1, 0, ..., 0, 1) for 1D)
```

### Key Properties

| Property | Benefit |
|----------|---------|
| Energy stability | Provable bounds on solution growth |
| Conservation | Discrete conservation for linear/nonlinear problems |
| High order | 2p interior order with p-order boundary closures |
| Multi-block | Natural coupling via SATs at interfaces |

### Common SBP Operators

| Interior Order | Boundary Order | Stencil Width | Reference |
|---------------|----------------|---------------|-----------|
| 2 | 1 | 3 | Kreiss & Scherer (1974) |
| 4 | 2 | 5 | Strand (1994) |
| 6 | 3 | 7 | Strand (1994) |
| 8 | 4 | 9 | Mattsson (2003) |

### When to Use SBP-SAT

- Long-time simulations requiring provable stability
- Multi-block or overset grid configurations
- Hyperbolic or advection-dominated PDEs
- Problems where energy estimates are critical (aeroelasticity, electromagnetics)

**References:**
- Svärd, M. & Nordström, J. (2014). Review of summation-by-parts schemes for initial-boundary-value problems. *J. Comput. Phys.*, 268, 17-38.
- Fernández, D.C.D.R., Hicken, J.E., & Zingg, D.W. (2014). Review of summation-by-parts operators with simultaneous approximation terms. *Comput. Fluids*, 95, 171-196.

## Nonuniform Grid Stencils

For grids with variable spacing, standard uniform stencils do not apply directly. Two main approaches exist.

### Fornberg's Algorithm

Computes finite difference weights for arbitrary node locations. Given nodes x₀, x₁, ..., xₙ, Fornberg's algorithm produces weights for any derivative order at any evaluation point.

```python
def fornberg_weights(z, x, m):
    """Compute FD weights for derivative order m at point z using nodes x.

    Reference: Fornberg, B. (1988). Generation of finite difference
    formulas on arbitrarily spaced grids. Math. Comp., 51(184), 699-706.
    """
    n = len(x) - 1
    c = [[0.0] * (m + 1) for _ in range(n + 1)]
    c[0][0] = 1.0
    c1 = 1.0
    for i in range(1, n + 1):
        c2 = 1.0
        for j in range(i):
            c3 = x[i] - x[j]
            c2 *= c3
            for k in range(min(i, m), 0, -1):
                c[i][k] = (c1 * (k * c[i-1][k-1] - (x[i-1] - z) * c[i-1][k])) / c2
            c[i][0] = -c1 * (x[i-1] - z) * c[i-1][0] / c2
            for k in range(min(i, m), 0, -1):
                c[j][k] = ((x[i] - z) * c[j][k] - k * c[j][k-1]) / c3
            c[j][0] = (x[i] - z) * c[j][0] / c3
        c1 = c2
    return [c[j][m] for j in range(n + 1)]
```

### Coordinate Transformation

Map nonuniform physical grid to uniform computational grid:

```
ξ = ξ(x)  (mapping function)
df/dx = (dξ/dx) × df/dξ
d²f/dx² = (dξ/dx)² × d²f/dξ² + (d²ξ/dx²) × df/dξ
```

Apply standard uniform stencils in ξ-space, then transform back.

**When to prefer each approach:**
| Approach | Best For |
|----------|----------|
| Fornberg weights | Arbitrary node placement, unstructured 1D |
| Coordinate transform | Smoothly varying grids, structured meshes |
| SBP on nonuniform | When energy stability proofs are needed |

## Implementation Notes

### Applying Stencils

```python
def apply_stencil(f, coeffs, offsets, dx):
    """Apply finite difference stencil."""
    result = np.zeros_like(f)
    for c, o in zip(coeffs, offsets):
        result += c * np.roll(f, -o)
    return result / dx

# Example: 4th-order central first derivative
coeffs = [1/12, -2/3, 0, 2/3, -1/12]
offsets = [-2, -1, 0, 1, 2]
df_dx = apply_stencil(f, coeffs, offsets, dx)
```

### Boundary Treatment

Interior stencils don't work at boundaries:

```
For central 4th-order (needs ±2 points):
  x = 0: use forward stencil
  x = dx: use biased stencil
  x = 2dx to x = (n-3)dx: central stencil
  x = (n-2)dx: use biased stencil
  x = (n-1)dx: use backward stencil
```

### Verification

Taylor expansion verification:

```
f(x+dx) = f(x) + dx f'(x) + dx²/2 f''(x) + dx³/6 f'''(x) + ...

Substitute into stencil, verify leading error term.
```

Grid refinement verification:

```
Run with dx, dx/2, dx/4
Error should decrease as dx^p for order p
```
