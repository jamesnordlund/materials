# Design of Experiments (DOE) Methods

## Overview

Design of Experiments (DOE) creates sample points in parameter space to efficiently explore simulation behavior. The goal is to maximize information gained per simulation run.

## Method Comparison

| Method | Sample Count | Space Coverage | Best Dimension | Deterministic |
|--------|--------------|----------------|----------------|---------------|
| LHS | User-defined | Good | 3-20 | No (random) |
| Sobol | User-defined | Excellent | 2-15 | Yes |
| Factorial | k^d (levels^dim) | Complete | 1-3 | Yes |

---

## Latin Hypercube Sampling (LHS)

### How It Works

LHS divides each parameter range into `n` equal intervals, then places exactly one sample in each interval per dimension. This ensures no two samples share the same row or column in any 2D projection.

```
Example: 5 samples in 2D

    1.0 |     x     |     |     | x   |
    0.8 |  x  |     |     |     |     |
    0.6 |     |     |     | x   |     |
    0.4 |     |     | x   |     |     |
    0.2 |     | x   |     |     |     |
        +-----+-----+-----+-----+-----+
          0.2   0.4   0.6   0.8   1.0
```

### When to Use

- General parameter exploration
- Moderate dimensions (3-20 parameters)
- Unknown response surface shape
- Limited simulation budget

### When to Avoid

- Need exact corner/edge coverage
- Very low dimensions where factorial is feasible
- Reproducibility required (use fixed seed)

### Sample Size Recommendations

| Dimension | Minimum Samples | Recommended |
|-----------|-----------------|-------------|
| 2-3 | 10 | 20-30 |
| 4-6 | 20 | 40-60 |
| 7-10 | 30 | 60-100 |
| 11-20 | 50 | 100-200 |

---

## Sobol Sequences (Quasi-Random)

### How It Works

Sobol sequences are low-discrepancy sequences that fill space more uniformly than random sampling. Points are generated deterministically using bit operations on direction numbers.

```
Example: Sobol vs Random in 2D (16 points)

Sobol (uniform fill)        Random (clusters/gaps)
+---+---+---+---+          +---+---+---+---+
| x |   | x |   |          |   | x |   | x |
+---+---+---+---+          +---+---+---+---+
|   | x |   | x |          | x |   |   |   |
+---+---+---+---+          +---+---+---+---+
| x |   | x |   |          |   | x | x | x |
+---+---+---+---+          +---+---+---+---+
|   | x |   | x |          |   |   | x |   |
+---+---+---+---+          +---+---+---+---+
```

### When to Use

- Sensitivity analysis (Sobol indices)
- Need uniform coverage guarantees
- Reproducible experiments
- Sequential sampling (can add points incrementally)

### When to Avoid

- Very high dimensions (>15, curse of dimensionality)
- Need stratified random sampling

### Sample Size Recommendations

For Sobol sensitivity analysis using the Saltelli estimator, total evaluations depend on whether second-order indices are computed:
- **First-order and total indices only**: `N * (d + 2)` samples
- **With second-order indices**: `N * (2d + 2)` samples

Where:
- `N` = base sample size (64, 128, 256, 512, 1024)
- `d` = number of parameters

| Dimension | Base N | Total (1st/total only) | Total (with 2nd-order) |
|-----------|--------|------------------------|------------------------|
| 3 | 64 | 320 | 512 |
| 5 | 128 | 896 | 1536 |
| 10 | 256 | 3072 | 5632 |

**Note**: SALib's `saltelli.sample()` defaults to computing second-order indices (`calc_second_order=True`), which uses the `N * (2d + 2)` formula. Set `calc_second_order=False` to use the smaller `N * (d + 2)` sample size.

---

## Full Factorial Design

### How It Works

Factorial designs test all combinations of discrete parameter levels. For `k` levels across `d` dimensions, this produces `k^d` samples.

```
Example: 3 levels, 2 dimensions = 9 samples

    High  | x   x   x |
          |           |
    Med   | x   x   x |
          |           |
    Low   | x   x   x |
          +-----------+
            L   M   H
```

### When to Use

- Low dimensions (1-3 parameters)
- Need exact corner coverage
- Testing parameter interactions
- Screening designs

### When to Avoid

- High dimensions (exponential growth)
- Continuous parameters with smooth response
- Limited budget

### Sample Count Growth

| Dimension | 2 Levels | 3 Levels | 5 Levels |
|-----------|----------|----------|----------|
| 2 | 4 | 9 | 25 |
| 3 | 8 | 27 | 125 |
| 4 | 16 | 81 | 625 |
| 5 | 32 | 243 | 3125 |

---

## Halton Sequences

### How It Works

Halton sequences are another class of low-discrepancy (quasi-random) sequences, based on the Van der Corput sequence in different prime bases for each dimension. For dimension d, the i-th point uses the radical-inverse function in the d-th prime base.

```
Example: First 8 Halton points in 2D (bases 2, 3)

    1.0 |       x       |
    0.8 |   x       x   |
    0.6 |       x       |
    0.4 |   x       x   |
    0.2 | x       x     |
        +---+---+---+---+
          0.2 0.4 0.6 0.8
```

### When to Use

- Low to moderate dimensions (2-10 parameters)
- Need deterministic, reproducible sampling
- Sequential sampling (can add points one at a time without regenerating)
- Simpler implementation than Sobol

### Halton vs Sobol

| Property | Halton | Sobol |
|----------|--------|-------|
| Dimensions | Best for 2-10 | Best for 2-15 |
| Correlation | Degrades in high d | Better uniformity in high d |
| Extensibility | Trivially add points | Powers of 2 preferred |
| Scrambling | Owen scrambling | Digital shift/scramble |
| Implementation | `scipy.stats.qmc.Halton` | `scipy.stats.qmc.Sobol` |

### Sample Code

```python
from scipy.stats import qmc
sampler = qmc.Halton(d=3, scramble=True, seed=42)
samples = sampler.random(n=64)
# Scale to parameter bounds
lower = [0.001, 0.1, 1.0]
upper = [0.01, 1.0, 100.0]
scaled = qmc.scale(samples, lower, upper)
```

**Reference:** Halton, J.H. (1960). On the efficiency of certain quasi-random sequences of points in evaluating multi-dimensional integrals. *Numerische Mathematik*, 2(1), 84-90.

---

## Multi-Objective Optimization (NSGA-II)

For problems with multiple conflicting objectives (e.g., minimize simulation error AND minimize computational cost), Pareto-optimal solutions are needed.

### NSGA-II Algorithm

Non-dominated Sorting Genetic Algorithm II:

1. Generate initial population
2. Evaluate all objectives for each individual
3. Non-dominated sorting: rank individuals by Pareto dominance
4. Crowding distance: diversity metric within each rank
5. Selection, crossover, mutation to create offspring
6. Combine parent and offspring, select best by rank then crowding distance
7. Repeat until convergence

### When to Use

- Two or more conflicting objectives
- Want a set of trade-off solutions (Pareto front)
- Moderate evaluation budgets (100-10,000)
- Discrete or continuous parameters

### Libraries

| Library | Multi-Objective Support | Notes |
|---------|------------------------|-------|
| pymoo | NSGA-II, NSGA-III, MOEA/D | Recommended for multi-objective |
| Optuna | Built-in NSGA-II | Easy integration |
| platypus | NSGA-II, MOEA/D, IBEA | Research-oriented |
| DEAP | NSGA-II via custom setup | Flexible but more setup |

**Reference:** Deb, K. et al. (2002). A fast and elitist multiobjective genetic algorithm: NSGA-II. *IEEE Trans. Evol. Comput.*, 6(2), 182-197.

---

## Decision Flowchart

```
START
  |
  v
Is d <= 3 AND need corner coverage?
  |
  +-- YES --> FACTORIAL
  |
  +-- NO --> Is sensitivity analysis the goal?
               |
               +-- YES --> SOBOL
               |
               +-- NO --> LHS
```

## Implementation Notes

The `doe_generator.py` script in this skill:
- LHS: True Latin Hypercube with random permutations (uses only random module)
- Sobol: Full low-discrepancy sequences via scipy.stats.qmc.Sobol with scrambling
- R-sequence: Golden-ratio quasi-random sampling (uses only math module)
- Factorial: Full grid with level interpolation
- Dependencies: numpy, scipy (for Sobol method)
