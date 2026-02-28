# Preconditioner Catalog

Comprehensive reference for preconditioners in iterative linear solvers.

## Preconditioner Fundamentals

### Purpose

Transform Ax = b into M⁻¹Ax = M⁻¹b where M⁻¹A has better conditioning.

**Goals:**
- Cluster eigenvalues away from zero
- Reduce condition number κ(M⁻¹A)
- Make M⁻¹ cheap to apply

### Application Modes

| Mode | System Solved | When to Use |
|------|---------------|-------------|
| Left | M⁻¹Ax = M⁻¹b | Most common |
| Right | AM⁻¹y = b, x = M⁻¹y | Preserves residual meaning |
| Split | L⁻¹AR⁻¹y = L⁻¹b | Symmetric preconditioning |

### Key Trade-offs

| Factor | Cheap Precond. | Expensive Precond. |
|--------|----------------|-------------------|
| Setup cost | Low | High |
| Apply cost | Low | High |
| Iterations | Many | Few |
| Total time | May be optimal | May be optimal |

## Incomplete Factorization Family

### Incomplete Cholesky (IC)

For SPD matrices: A ≈ LLᵀ where L is sparse.

**IC(0)** - Zero fill-in:
- Same sparsity pattern as lower triangle of A
- Cheap, often effective
- May fail for indefinite or poorly scaled

**IC(k)** - Level-k fill:
- Allow fill-in up to k levels from original pattern
- More robust, higher cost
- k = 1 or 2 often sufficient

**Modified IC (MIC) and Diagonal Shift**:
- Add dropped fill entries back to diagonal (row sum preservation)
- Better for M-matrices (e.g., Laplacian) and matrices that are nearly singular
- **When IC(0) fails**: If IC(0) breaks down (zero or negative pivot), add diagonal shift:
  ```
  M = L L^T + δD  where D = diag(A)
  ```
  - Start with δ = 1e-3 × ||A||_F
  - Increase δ if breakdown persists
  - This is called "Modified IC with Compensation" or "IC with Diagonal Shift"
- **MATLAB equivalent**: `ichol(A, struct('droptol', 0, 'diagcomp', 1e-3))`

### Incomplete LU (ILU)

For general matrices: A ≈ LU where L, U are sparse.

**ILU(0)** - Zero fill-in:
```
Pattern(L + U) = Pattern(A)
Cheap, first try for nonsymmetric
```

**ILU(k)** - Level-k fill:
```
Allow fill paths up to k edges
k = 1: moderate fill
k = 2: substantial fill
```

**ILUT** - Threshold-based:
```
Parameters: τ (drop tolerance), p (max fill per row)
Drop if |entry| < τ × ||row||
Keep at most p entries per row
```

| Parameter | Effect |
|-----------|--------|
| τ small | More fill, better approximation |
| τ large | Less fill, weaker preconditioner |
| p small | Limit memory, may reduce quality |
| p large | Better quality, more memory |

**Typical values:**
```
τ = 1e-4 to 1e-2
p = 10 to 50 (or 2× to 5× original nnz/row)
```

### Choosing IC vs ILU Parameters

| Symptom | Adjustment |
|---------|------------|
| Convergence too slow | Increase k or decrease τ |
| Too much memory | Increase τ or decrease p |
| Factorization fails | Add diagonal shift, try different ordering |
| Negative pivot (IC) | Matrix not SPD, use ILU |

## Algebraic Multigrid (AMG)

### When to Use

| Good for | Poor for |
|----------|----------|
| Elliptic PDEs | Highly nonsymmetric |
| Diffusion-dominated | Pure advection |
| Smooth error | Oscillatory error |
| Large systems | Small systems (overhead) |

### AMG Components

**Coarsening:**
- Classical (Ruge-Stüben): Strength-based C/F splitting
- Aggregation: Group nodes into aggregates
- Smoothed aggregation: SA-AMG, good for elasticity

**Interpolation:**
- Direct: Use strong connections
- Standard: Include weak connections
- Extended+i: For harder problems

**Smoothing:**
- Jacobi: Simple, parallelizable
- Gauss-Seidel: Better smoothing, less parallel
- Polynomial: Good for GPU

### AMG Tuning

| Parameter | Effect |
|-----------|--------|
| Strong threshold | Lower = more connections = slower coarsening |
| Coarsening ratio | 2:1 to 4:1 typical |
| Max levels | 10-20 typical |
| Smoother | Jacobi (parallel) vs GS (sequential) |
| Cycles | V-cycle (cheap) vs W-cycle (robust) |

### AMG for Nonsymmetric

Some AMG can handle mildly nonsymmetric:
- Use symmetric part for coarsening
- May need more smoothing
- Verify convergence experimentally

## Specialized Preconditioners

### Jacobi and Block Jacobi

**Point Jacobi:** M = diag(A)
```
Simple, parallel, weak
Use as smoother in multigrid
```

**Block Jacobi:** M = block_diag(A)
```
Blocks from natural structure (elements, nodes)
Stronger than point Jacobi
Embarrassingly parallel
```

### Gauss-Seidel

**Forward/Backward GS:**
```
M = L + D (forward) or D + U (backward)
Stronger than Jacobi
Sequential, hard to parallelize
```

**Symmetric GS (SSOR):**
```
Apply forward then backward
Good smoother for symmetric problems
Parameter ω (relaxation): typically 1.0
```

### SSOR (Symmetric SOR)

For SPD systems, the SSOR preconditioner is (Saad 2003, Eq. 10.7):
```
M = (ω/(2-ω)) × (D/ω + L) × D⁻¹ × (D/ω + U)
ω: overrelaxation parameter (0 < ω < 2)
ω = 1: Symmetric Gauss-Seidel
ω optimal ≈ 2/(1 + sin(πh)) for model problem

where D = diag(A), L = strict lower triangle, U = strict upper triangle
```

**Reference:** Saad, Y. (2003). *Iterative Methods for Sparse Linear Systems*, 2nd ed., SIAM, Eq. 10.7.

### Polynomial Preconditioners

Approximate M⁻¹ ≈ p(A) for some polynomial p.

**Neumann series:**
```
M⁻¹ ≈ I + (I - A) + (I - A)² + ...
Requires ρ(I - A) < 1
```

**Chebyshev:**
```
Optimal polynomial for given eigenvalue bounds
Requires [λ_min, λ_max] estimates
Good for GPU (only matrix-vector products)
```

## Block Preconditioners

### For Saddle-Point Systems

```
K = [A   B ]    x = [u]    b = [f]
    [Bᵀ  -C]        [p]        [g]
```

**Block Diagonal:**
```
P = [Â   0 ]
    [0   Ŝ ]

Â ≈ A (e.g., AMG for A)
Ŝ ≈ S = C + BᵀA⁻¹B (Schur complement)
```

**Block Triangular:**
```
P = [Â   0 ]    or    P = [Â   B]
    [Bᵀ  -Ŝ]              [0  -Ŝ]
```

### Schur Complement Approximations

| Approximation | Formula | Use Case |
|---------------|---------|----------|
| Mass matrix | Ŝ = M_p (pressure mass) | Stokes |
| BFBt | Ŝ = B diag(A)⁻¹ Bᵀ | General |
| LSC | Ŝ = (B Bᵀ)(B A Bᵀ)⁻¹(B Bᵀ) | Navier-Stokes |
| PCD | Convection-diffusion-reaction | Navier-Stokes |

### Field-Split Preconditioners

For multi-physics with fields u₁, u₂, ...:
```
Multiplicative: Solve u₁, then u₂ using updated u₁
Additive: Solve each independently, sum corrections
```

## Domain Decomposition Preconditioners

Domain decomposition (DD) methods partition the computational domain into subdomains and construct preconditioners by combining local subdomain solves with interface coupling. These methods are particularly effective for parallel computing and large-scale problems.

**References:**
- Toselli, A. & Widlund, O. (2005). *Domain Decomposition Methods - Algorithms and Theory*, Springer Series in Computational Mathematics, Vol. 34.
- Smith, B., Bjørstad, P., & Gropp, W. (1996). *Domain Decomposition: Parallel Multilevel Methods for Elliptic Partial Differential Equations*, Cambridge University Press.

### Schwarz Methods

Domain decomposition preconditioners based on overlapping subdomain decompositions.

#### Additive Schwarz Method (ASM)

Solve independently on overlapping subdomains and sum corrections.

**Algorithm:**
```
Given: Domain Ω decomposed into N overlapping subdomains Ωᵢ
For each subdomain i:
  Solve Aᵢuᵢ = fᵢ locally on Ωᵢ
Combine: u = Σᵢ Rᵢᵀuᵢ
```

Where Rᵢ is a restriction operator to subdomain i.

**Key Parameters:**
- **Overlap δ**: Number of layers of elements/nodes shared between subdomains
  - δ = 0: No overlap, domain decomposition only at interfaces
  - δ = 1-3: Typical practical values
  - Larger δ: Better convergence, higher communication cost

**Characteristics:**
- Embarrassingly parallel (independent subdomain solves)
- Convergence rate independent of number of subdomains with sufficient overlap
- Iteration count increases as number of subdomains increases (needs coarse grid)

**When to Use:**
- Distributed memory parallel systems
- Problems with natural domain partitioning
- Combined with coarse grid correction for scalability

**Typical Convergence:**
```
With overlap δ = 1: iteration count ∝ O(N^(1/2)) subdomains without coarse grid
With coarse grid: iteration count ≈ constant as N increases
```

#### Multiplicative Schwarz Method (MSM)

Solve sequentially on overlapping subdomains, each using updated solution.

**Algorithm:**
```
For i = 1 to N:
  Solve Aᵢuᵢ = fᵢ on Ωᵢ using current iterate
  Update global solution u with uᵢ
```

**Advantages over Additive:**
- Stronger preconditioner (more information propagation)
- Typically requires fewer iterations
- Can use smaller overlap for same convergence

**Disadvantages:**
- Sequential dependency (less parallel)
- Harder to implement efficiently on distributed systems
- May require careful subdomain ordering

**When to Use:**
- Shared-memory parallel systems (OpenMP)
- Strong coupling between subdomains
- When iteration count is the bottleneck
- As smoother in multilevel methods

### Balancing Domain Decomposition by Constraints (BDDC)

Non-overlapping DD method with carefully chosen coarse degrees of freedom.

**Core Idea:**
```
Decompose unknowns into:
  - Interior: Fully within one subdomain
  - Interface: Shared between subdomains
  - Primal: Coarse dofs enforcing continuity constraints

Primal variables form coarse problem for global coupling.
```

**Constraint Selection:**
- **Vertex constraints**: Values at subdomain corners
- **Edge/Face averages**: For higher-order elements or 3D
- **Rigid body modes**: For elasticity problems

**Characteristics:**
- One-level preconditioner (no recursive coarsening)
- Scalable: condition number bound independent of subdomain count
- κ(M⁻¹A) ≤ C(1 + log(H/h))² where H = subdomain size, h = element size
- Excellent for structured grids and elasticity

**When to Use:**
- Structural mechanics and elasticity
- Moderate to large scale (10³-10⁶ subdomains)
- When subdomain problems can be factored once
- Prefer spectral bounds over iteration count

**Implementation Notes:**
- Requires local dense Schur complements on interfaces
- Setup cost higher than Schwarz methods
- Apply cost dominated by local subdomain solves

**Typical Performance:**
```
Elasticity: 20-40 iterations independent of subdomain count
Laplace: 10-30 iterations with log²(H/h) dependence
```

### Finite Element Tearing and Interconnecting (FETI)

Non-overlapping DD using Lagrange multipliers to enforce interface compatibility.

**Core Idea:**
```
"Tear" domain at subdomain interfaces
Apply Dirichlet conditions on each subdomain
Enforce continuity via Lagrange multipliers λ

Solve dual problem for λ, then recover primal unknowns u
```

**Variants:**
- **FETI-1**: Original method, one Lagrange multiplier per interface dof
- **FETI-DP** (Dual-Primal): Combines FETI with primal coarse space (like BDDC)
- **FETI-2**: Two multipliers per interface (more general)

**Characteristics:**
- Solves dual problem (smaller than primal for many subdomains)
- Each subdomain solve is independent with Dirichlet BC
- Requires handling "floating" subdomains (no boundary conditions)
- Coarse problem: subdomain rigid body modes or corner constraints

**When to Use:**
- Large number of subdomains (10³-10⁶)
- Structural mechanics (elasticity, contact, fracture)
- Problems with varying material properties across subdomains
- When dual problem is significantly smaller than primal

**Advantages:**
- Natural for problems with local Neumann BC or contact
- Handles heterogeneous coefficients well
- Robust for nearly incompressible materials

**Disadvantages:**
- More complex implementation than Schwarz
- Requires careful handling of null spaces (floating subdomains)
- Setup cost for coarse problem

**Typical Performance:**
```
FETI-DP for elasticity: 15-50 iterations, weakly dependent on subdomain count
Convergence bound: κ(F⁻¹S) ≤ C(1 + log(H/h))²
```

### Domain Decomposition Selection Guide

| Method | Best For | Parallel Efficiency | Setup Cost | Iteration Count |
|--------|----------|-------------------|------------|-----------------|
| Additive Schwarz | Shared-memory, moderate scale | High | Low | Moderate (needs coarse grid) |
| Multiplicative Schwarz | Strong coupling, smoother | Low | Low | Low |
| BDDC | Elasticity, structured grids | High | Moderate | Low |
| FETI/FETI-DP | Large scale, heterogeneous | High | Moderate | Low |

### Combining DD with Local Preconditioners

Domain decomposition typically uses a local preconditioner for each subdomain:

| Local Precond. | DD Method | Use Case |
|----------------|-----------|----------|
| Direct (LU) | ASM, BDDC, FETI | Small subdomains (< 10⁴ dofs) |
| ILU | ASM | Large subdomains, nonsymmetric |
| IC | ASM | Large subdomains, SPD |
| AMG | ASM (two-level) | Very large subdomains |

**Two-Level DD:**
```
Preconditioner M⁻¹ = M₀⁻¹ + Σᵢ Rᵢᵀ Aᵢ⁻¹ Rᵢ
where M₀⁻¹ is a coarse grid correction
```

The coarse problem couples all subdomains and is essential for scalability.

### Practical Recommendations

**For beginners:**
- Start with one-level additive Schwarz (ASM) with overlap δ = 1-2
- Use direct solvers on each subdomain if feasible
- Add coarse grid correction if iteration count grows with subdomain count

**For production:**
- BDDC for elasticity on structured or semi-structured meshes
- FETI-DP for elasticity with complex geometry or contact
- Two-level ASM for general PDEs with AMG or ILU local solves

**For extreme scale (10⁵-10⁶ cores):**
- Three-level methods (local, intermediate, coarse)
- BDDC or FETI-DP with algebraically constructed coarse spaces
- Careful tuning of coarse problem solver

## Preconditioner Selection Guide

### By Matrix Type

| Matrix | First Choice | Alternative |
|--------|--------------|-------------|
| SPD, diffusion | AMG | IC(k) |
| SPD, elasticity | SA-AMG | IC(k) |
| SPD, general | IC(0) | AMG |
| Nonsymmetric, mild | ILU(0) | ILUT |
| Nonsymmetric, advection | ILUT (strong) | Stream-wise ILU |
| Saddle-point | Block diagonal/triangular | Uzawa |
| Dense | - (direct solver) | - |

### By Problem Size

| Size | Recommendation |
|------|----------------|
| n < 1000 | Direct solver |
| n = 1000-10000 | ILU/IC or AMG |
| n = 10000-1M | AMG (if applicable) |
| n > 1M | AMG, domain decomposition |

### By Available Resources

| Resource | Recommendation |
|----------|----------------|
| Single core | Sequential GS, ILU |
| Multi-core | Block Jacobi, AMG |
| GPU | Polynomial, Block Jacobi |
| Distributed | Domain decomposition + local precond. |

## Troubleshooting

### Preconditioner Fails to Build

| Error | Cause | Fix |
|-------|-------|-----|
| Zero pivot | Singular or structurally singular | Reorder, add diagonal shift |
| Negative pivot (IC) | Not SPD | Use ILU, check matrix |
| Out of memory | Too much fill | Increase τ, reduce p or k |

### Poor Convergence Despite Preconditioner

| Symptom | Cause | Fix |
|---------|-------|-----|
| Slow decay | Weak preconditioner | Strengthen (lower τ, higher k) |
| Stagnation | Unfavorable eigenvalue distribution | Try different preconditioner |
| Oscillation | Near-singular modes | Check matrix, regularize |

### Parameter Tuning Strategy

1. **Start simple:** ILU(0) or IC(0)
2. **Monitor:** iteration count, residual curve
3. **Adjust:** If slow, strengthen preconditioner
4. **Balance:** Setup time vs iteration time
5. **Validate:** Check solution accuracy

## Implementation Notes

### Setup vs Apply Cost

| Preconditioner | Setup | Apply | When Setup Dominates |
|----------------|-------|-------|----------------------|
| Jacobi | O(n) | O(n) | Never |
| ILU(0) | O(nnz) | O(nnz) | Many solves |
| AMG | O(n log n) | O(n) | Few solves |

### Reusing Preconditioners

When matrix changes slightly:
```
Same pattern: May reuse structure, update values
Small changes: Lag preconditioner (update every k solves)
Large changes: Rebuild preconditioner
```

### Quality Metrics

| Metric | Good Value |
|--------|------------|
| Fill ratio (nnz(LU)/nnz(A)) | 2-10 for ILU |
| Operator complexity (AMG) | 1.2-2.0 |
| Convergence factor | < 0.3 |
| Iterations | < 50 typically |
