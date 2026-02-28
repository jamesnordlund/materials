# Solver Decision Tree

Comprehensive decision guide for selecting linear solvers for Ax = b.

## Matrix Classification

### Key Properties to Determine

| Property | How to Check | Impact |
|----------|--------------|--------|
| Symmetric | A = Aᵀ | Enables CG, MINRES |
| Positive definite | All eigenvalues > 0 | Enables CG, Cholesky |
| Sparse | nnz/n² < 0.01 | Iterative preferred |
| Well-conditioned | κ(A) < 10⁶ | Standard methods work |
| Banded | Nonzeros near diagonal | Band solvers efficient |

### Quick Classification

```
Check symmetry: ||A - Aᵀ||_F / ||A||_F < ε
Check SPD: try Cholesky, if succeeds → SPD
Check sparsity: nnz / n² gives density
Check conditioning: estimate κ using power iteration or Lanczos
```

## Primary Decision Tree

```
START: Need to solve Ax = b
│
├─ Is n < 5000 and matrix dense?
│   └── YES → Use DIRECT solver
│       ├── Symmetric PD → Cholesky (LLᵀ)
│       ├── Symmetric indefinite → LDLᵀ (Bunch-Kaufman)
│       ├── Nonsymmetric → LU with pivoting
│       └── Least squares → QR or SVD
│
└── NO → Use ITERATIVE solver
    │
    ├─ Is matrix symmetric?
    │   │
    │   ├── YES → Is it positive definite?
    │   │   │
    │   │   ├── YES (SPD) → CG (Conjugate Gradient)
    │   │   │   ├── Elliptic PDE → AMG preconditioner
    │   │   │   ├── Banded structure → IC(0) or IC(k)
    │   │   │   └── General sparse → AMG or IC
    │   │   │
    │   │   └── NO/Unknown (symmetric indefinite)
    │   │       ├── Eigenvalues both signs → MINRES
    │   │       ├── Near-singular → SYMMLQ
    │   │       └── Preconditioner: SSOR, ICC, or SPD block diagonal
    │   │           (MINRES requires symmetric positive-definite preconditioner)
    │   │
    │   └── NO (nonsymmetric) → Is it nearly symmetric?
    │       │
    │       ├── YES (A ≈ Aᵀ) → BiCGSTAB
    │       │   ├── Smooth convergence needed → BiCGSTAB(ℓ)
    │       │   └── Preconditioner: ILUT or AMG
    │       │
    │       └── NO (strongly nonsymmetric) → GMRES
    │           ├── Memory limited → GMRES(m) restarted
    │           ├── Very nonsymmetric → Full GMRES if affordable
    │           └── Preconditioner: ILU(k), ILUT, or AMG
```

## Direct Solver Selection

### When to Use Direct

| Condition | Direct Recommended |
|-----------|-------------------|
| n < 5000 | Usually |
| Dense matrix | Yes |
| Multiple RHS | Yes (factor once) |
| Need exact solution | Yes |
| High accuracy required | Yes |
| Robustness critical | Yes |

### Direct Solver Types

| Matrix Type | Method | Complexity |
|-------------|--------|------------|
| General dense | LU with pivoting | O(n³) |
| Symmetric dense | LDLᵀ (Bunch-Kaufman) | O(n³/3) |
| SPD dense | Cholesky | O(n³/3) |
| Sparse | Sparse LU (SuperLU, UMFPACK) | Problem-dependent: O(N log N) (2D) to O(N^(4/3)) (3D) for nested dissection |
| Banded | Band LU/Cholesky | O(n × b²) |

**References:**
- Golub, G.H. & Van Loan, C.F. (2013). *Matrix Computations*, 4th ed., Section 4.2 (LDL^T factorization complexity: O(n³/3))
- George, A. & Liu, J.W. (1981). *Computer Solution of Large Sparse Positive Definite Systems*, Prentice-Hall (sparse complexity analysis)
- Davis, T.A. (2006). *Direct Methods for Sparse Linear Systems*, SIAM (sparse LU complexity ranges)

### Memory Considerations

| Method | Memory | Fill-in |
|--------|--------|---------|
| Dense LU | O(n²) | N/A |
| Sparse LU | O(n) to O(n²) | Depends on ordering |
| Cholesky | Half of LU | Less fill-in |
| Iterative | O(n) × k | No fill-in |

## Iterative Solver Details

### Conjugate Gradient (CG)

**Requirements:** A must be SPD

**Convergence:**
```
||e_k||_A ≤ 2 × ((√κ - 1)/(√κ + 1))^k × ||e_0||_A
```

| Condition Number | Iterations (to 10⁻⁶) |
|------------------|----------------------|
| κ = 10 | ~6 |
| κ = 100 | ~20 |
| κ = 1000 | ~60 |
| κ = 10⁶ | ~2000 |

**Breakdown:** CG is breakdown-free for SPD matrices.

### GMRES

**Requirements:** None (works for any nonsingular matrix)

**Properties:**
- Minimizes residual over Krylov subspace
- Optimal for nonsymmetric systems
- Memory: O(m × n) for m iterations

**Restart Strategy:**
```
GMRES(m): Restart after m iterations
├── m = 20-30: Typical for memory-limited
├── m = 50-100: Better convergence
└── m = n: Full GMRES (no restart)
```

**When GMRES stalls:**
- Increase restart parameter m
- Improve preconditioner
- Check for near-singularity

### BiCGSTAB

**Requirements:** Works for nonsymmetric, best if A ≈ Aᵀ

**Properties:**
- Lower memory than GMRES
- May have irregular convergence
- Two matrix-vector products per iteration

**Variants:**
| Variant | Properties |
|---------|------------|
| BiCGSTAB | Standard |
| BiCGSTAB(ℓ) | Smoother convergence, higher cost |
| IDR(s) | Alternative, can be faster |

### MINRES

**Requirements:** A symmetric (not necessarily PD)

**Properties:**
- Works for indefinite symmetric systems
- Minimizes residual (like GMRES for symmetric)
- Short recurrences (memory efficient)

**Use for:**
- Saddle-point systems
- Systems from variational problems
- Eigenvalue problems (shift-invert)

## Special Matrix Structures

### Saddle-Point Systems

```
[A   B ] [x]   [f]
[Bᵀ  -C] [y] = [g]
```

**Solvers:**
- Schur complement method
- Uzawa iteration
- Block preconditioned GMRES/MINRES

**Preconditioners:**
```
Block diagonal: [A⁻¹   0  ]
                [0    S⁻¹]

Block triangular: [A⁻¹  0 ]
                  [Bᵀ   S⁻¹]
```

Where S = C + BᵀA⁻¹B is the Schur complement.

### Banded Systems

For bandwidth b << n:

| Method | Cost | When to Use |
|--------|------|-------------|
| Band LU | O(nb²) | Direct, small b |
| Thomas (tridiag) | O(n) | b = 1 |
| Cyclic reduction | O(n log n) | Parallel |

### Block Systems

When A has natural block structure:

```
Block Jacobi: Solve diagonal blocks independently
Block Gauss-Seidel: Sequential block updates
Block ILU: Factor with block structure preserved
```

## Solver Selection by Application

### Elliptic PDEs (Laplacian-like)

| Grid | Recommended |
|------|-------------|
| Structured | CG + FFT or Multigrid |
| Unstructured | CG + AMG |
| Anisotropic | CG + line/plane smoothing |

### Parabolic PDEs (Heat equation)

| Implicit Method | Recommended |
|-----------------|-------------|
| Backward Euler | CG + IC/AMG (SPD) |
| Crank-Nicolson | CG + IC/AMG (SPD) |
| BDF | Same as above |

### Hyperbolic PDEs (Advection-dominated)

| Character | Recommended |
|-----------|-------------|
| Pure advection | GMRES + ILU (nonsymmetric) |
| Advection-diffusion | GMRES/BiCGSTAB + ILUT |
| High Péclet | Upwind + GMRES + strong ILU |

### Navier-Stokes

| Formulation | Recommended |
|-------------|-------------|
| Coupled velocity-pressure | Block preconditioned GMRES |
| Projection methods | Poisson: CG + AMG |
| SIMPLE-like | Momentum: BiCGSTAB, Pressure: CG |

### Phase-Field

| Equation | Recommended |
|----------|-------------|
| Allen-Cahn | CG + AMG (if implicit) |
| Cahn-Hilliard | GMRES + Block preconditioner (4th order) |
| Mixed form | CG + AMG for each block |

## Failure Modes and Remedies

### Common Problems

| Symptom | Cause | Solution |
|---------|-------|----------|
| No convergence | Poor preconditioner | Stronger preconditioner |
| Slow convergence | High condition number | Scale matrix, better preconditioner |
| Breakdown | Singular or near-singular | Check matrix, use pseudo-inverse |
| Oscillation | Loss of orthogonality | Increase GMRES restart |
| NaN/Inf | Overflow | Scale matrix |

### When All Else Fails

1. **Check the matrix**: Is it actually nonsingular?
2. **Scale rows/columns**: Equilibrate to unit row norms
3. **Try direct solver**: Even for large sparse, may work
4. **Regularize**: Add small diagonal for near-singular
5. **Reformulate problem**: Different discretization

## GPU-Accelerated Solvers

### When to Use GPU Solvers

GPU solvers provide significant speedup for:
- Large dense systems (cuSOLVER, cuBLAS)
- Sparse direct solves (cuDSS, cuSPARSE)
- Iterative solvers with GPU-friendly preconditioners (AmgX, MAGMA)
- Batched solves of many small systems (cuBLAS batched)

### NVIDIA CUDA Libraries

| Library | Type | Key Routines | Best For |
|---------|------|-------------|----------|
| **cuSOLVER** | Dense & sparse direct | LU, Cholesky, QR, sparse Cholesky | Single large solves |
| **cuSPARSE** | Sparse operations | SpMV, SpMM, ILU, IC | Building blocks for iterative |
| **cuDSS** | Sparse direct | Multifrontal LU/Cholesky | Large sparse direct solves |
| **AmgX** | Algebraic multigrid | AMG-preconditioned Krylov | Elliptic PDE solves at scale |
| **cuBLAS** | Dense BLAS | GEMM, TRSV, batched operations | Dense kernels, small batched |

### GPU Solver Selection

```
Is the system dense?
  YES → cuSOLVER (LU/Cholesky) or cuBLAS for batched small systems
  NO → Is sparse direct feasible (n < 10⁶)?
         YES → cuDSS (sparse multifrontal)
         NO → Iterative on GPU:
              SPD? → CG + AmgX (AMG preconditioner)
              General? → GMRES + cuSPARSE ILU/IC + AmgX
```

### GPU-Friendly Preconditioners

| Preconditioner | GPU Suitability | Notes |
|---------------|-----------------|-------|
| Jacobi / Block Jacobi | Excellent | Embarrassingly parallel |
| Polynomial (Chebyshev) | Excellent | Only needs SpMV |
| AMG (AmgX) | Very good | Optimized GPU implementation |
| ILU(0) / IC(0) | Moderate | Level-scheduled parallelism |
| ILUT | Poor | Inherently sequential; consider block variants |

### ML-Enhanced Preconditioners

Emerging approaches using machine learning for preconditioning:

| Approach | Description | Status (2024) |
|----------|-------------|---------------|
| Learned ILU | Train neural network to predict ILU factors | Research |
| Graph neural network preconditioner | GNN predicts sparsity pattern and values | Research |
| Neural operator as preconditioner | DeepONet/FNO approximate A⁻¹ | Research |
| Hybrid AMG-ML | ML-tuned AMG parameters | Early production |

**Note:** ML-enhanced preconditioners are not yet mature for production V&V-critical applications. They show promise for repeated solves with similar matrix structure (e.g., parameter sweeps).

### Practical GPU Considerations

| Factor | Guidance |
|--------|----------|
| Data transfer | Minimize CPU↔GPU transfers; keep matrix on GPU across solves |
| Memory | GPU memory is limited (~16-80 GB); plan for matrix + workspace |
| Precision | Mixed precision (FP32 solve + FP64 refinement) can 2× throughput |
| Batched | For many small systems (n < 1000), batched solvers are optimal |
| Multi-GPU | Needed for very large problems; adds communication complexity |

## Quick Reference Table

| Matrix Type | First Choice | Preconditioner | Backup |
|-------------|--------------|----------------|--------|
| SPD, elliptic | CG | AMG | CG + IC |
| SPD, general | CG | IC(k) | Cholesky |
| Sym. indef. | MINRES | SPD block diag, SSOR | GMRES |
| Nonsym., mild | BiCGSTAB | ILUT | GMRES |
| Nonsym., strong | GMRES(50) | ILU(k) | GMRES(100) |
| Saddle-point | Block GMRES | Schur approx | Uzawa |
| Dense | LU/Cholesky | - | - |
