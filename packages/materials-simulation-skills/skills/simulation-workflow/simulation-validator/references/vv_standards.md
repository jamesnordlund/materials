# V&V Standards Reference

## Overview

This document maps the simulation-validator concepts and terminology to formal Verification and Validation (V&V) standards from ASME and NASA, providing a bridge between the practical validation protocol implemented in this skill and industry-standard V&V frameworks.

---

## Standard Mapping Table

### Simulation-Validator Stage → Formal V&V Standard Mapping

| Validation Stage | Package Component | ASME Standard | NASA Standard | Standard Activity |
|------------------|-------------------|---------------|---------------|-------------------|
| Pre-flight checks | `preflight_checker.py` | V&V 10-2006 Section 3.2 (Code Verification) | NASA-STD-7009A Section 3.2 (Verification Planning) | Input verification, parameter range checking |
| Pre-flight stability checks | `preflight_checker.py` | V&V 20-2009 Section 5.2 (Numerical Error Estimation) | NASA-STD-7009A Section 3.3 (Verification Methods) | Grid convergence assessment, discretization error |
| Runtime monitoring | `runtime_monitor.py` | V&V 40-2018 Section 6.3 (Model Form Uncertainty) | NASA-STD-7009A Section 4.4 (Uncertainty Quantification) | Solution monitoring, convergence tracking |
| Post-flight conservation checks | `result_validator.py` | V&V 20-2009 Section 4.3 (Validation Experiments) | NASA-STD-7009A Section 4.2 (Validation Evidence) | Physical conservation laws, mass/energy balance |
| Post-flight field validation | `result_validator.py` | V&V 20-2009 Section 4.4 (Validation Metrics) | NASA-STD-7009A Section 4.3 (Comparison Methods) | Bounds checking, statistical validation |
| Failure diagnosis | `failure_diagnoser.py` | V&V 10-2006 Appendix A (Error Sources) | NASA-STD-7009A Section 3.4 (Anomaly Resolution) | Root cause analysis, diagnostic patterns |

### Concept Mapping by Standard

#### ASME V&V 10-2006: Guide for Verification and Validation in Computational Solid Mechanics

**Scope:** Verification of computational solid mechanics models (also applicable to general PDEs).

| V&V 10 Concept | Package Implementation | Location |
|----------------|------------------------|----------|
| Code verification | Parameter validation, type checking | `preflight_checker.py` checks |
| Solution verification | Convergence monitoring, residual tracking | `runtime_monitor.py` alerts |
| Verification test problems | Reference solutions, analytical comparisons | `result_validator.py` bounds |
| Error quantification | Residual norms, conservation drift | `result_validator.py` metrics |

#### ASME V&V 20-2009: Standard for Verification and Validation in Computational Fluid Dynamics and Heat Transfer

**Scope:** Verification and validation specifically for CFD and heat transfer (relevant for phase-field, diffusion, heat equation solvers).

| V&V 20 Concept | Package Implementation | Location |
|----------------|------------------------|----------|
| Input uncertainty | Parameter range validation | `preflight_checker.py` --ranges |
| Discretization error | Grid resolution checks, CFL conditions | `preflight_checker.py` stability |
| Iterative convergence | Residual stagnation, divergence detection | `runtime_monitor.py` convergence |
| Validation hierarchy | Confidence scoring, multi-stage validation | `result_validator.py` confidence_score |
| Validation metrics | Field bounds, conservation checks | `result_validator.py` checks |

#### ASME V&V 40-2018: Assessing Credibility of Computational Modeling through Verification and Validation: Application to Medical Devices

**Scope:** Risk-informed V&V (applicable methodology for materials simulation where consequences matter).

| V&V 40 Concept | Package Implementation | Location |
|----------------|------------------------|----------|
| Question of Interest | User-defined validation checks | `result_validator.py` custom checks |
| Credibility factors | Confidence score calculation | `result_validator.py` confidence |
| Risk-based assessment | Severity levels (BLOCKER/WARNING) | `preflight_checker.py` status |
| Evidence documentation | JSON output, traceability | All scripts `--json` flag |

#### NASA-STD-7009A: Standard for Models and Simulations

**Scope:** NASA standard for M&S credibility assessment (broadly applicable to scientific computing).

| NASA-STD-7009A Concept | Package Implementation | Location |
|------------------------|------------------------|----------|
| Verification planning | Pre-flight checklist, required parameters | `preflight_checker.py` --required |
| Verification methods | Code verification via type/range checks | `preflight_checker.py` validation |
| Validation evidence | Post-run checks, conservation laws | `result_validator.py` checks |
| Uncertainty quantification | Statistical validation, bounds checking | `result_validator.py` field validation |
| M&S documentation | JSON outputs, status reports | All scripts --json |
| Anomaly resolution | Failure diagnosis, pattern matching | `failure_diagnoser.py` probable_causes |

---

## Terminology Crosswalk

### Package Term → Standard Term Mapping

| This Package | ASME V&V Standards | NASA-STD-7009A | Notes |
|--------------|-------------------|----------------|-------|
| Pre-flight checks | Code verification activities | Verification planning & input checks | Ensures code operates on valid inputs |
| Runtime monitoring | Solution verification | In-process monitoring | Tracks convergence during execution |
| Post-flight validation | Validation assessment | Validation evidence collection | Compares results to expected behavior |
| Blocker | Critical deficiency | Non-compliance | Prevents execution or invalidates results |
| Warning | Non-critical issue | Recommendation | Requires documentation but not blocking |
| Confidence score | Validation metric | Credibility assessment | Quantitative measure of result trustworthiness |
| Residual growth | Iterative convergence failure | Solution anomaly | Indicates divergence or instability |
| Conservation drift | Physical inconsistency | Model form error indicator | Violation of fundamental physics |
| Required parameters | Input specification | Model input requirements | Mandatory model inputs |
| Parameter ranges | Input bounds | Epistemic uncertainty bounds | Physically plausible parameter values |

### Standard Term → Package Component Mapping

| Standard Term | Standard | Package Implementation |
|---------------|----------|------------------------|
| Verification | V&V 10, V&V 20, NASA-STD-7009A | Pre-flight checks (Stage 1) + Runtime monitoring (Stage 2) |
| Validation | V&V 20, V&V 40, NASA-STD-7009A | Post-flight validation (Stage 3) |
| Code verification | V&V 10 Section 3 | `preflight_checker.py` parameter validation |
| Solution verification | V&V 10 Section 4, V&V 20 Section 5 | `runtime_monitor.py` convergence checks |
| Validation metric | V&V 20 Section 4.4 | `result_validator.py` field checks, conservation |
| Credibility assessment | V&V 40 Section 5 | `result_validator.py` confidence_score |
| Uncertainty quantification | V&V 20 Section 6, NASA-STD-7009A Section 4.4 | `result_validator.py` statistical validation |
| Model form error | V&V 40 Section 6.3 | Conservation drift detection |
| Numerical error | V&V 20 Section 5.2 | CFL/stability condition violations |

---

## Applicability Guidance

### When to Apply Each Standard

#### ASME V&V 10-2006: General Verification for All PDE-Based Simulations

**Apply when:**
- Running any computational solid mechanics, heat transfer, or PDE solver
- Need to verify code correctness (not just validate physics)
- Performing convergence studies or grid refinement
- Checking implementation of boundary conditions

**Key sections relevant to this package:**
- Section 3.2: Code verification → `preflight_checker.py`
- Section 4: Solution verification → `runtime_monitor.py`
- Appendix A: Error taxonomy → `failure_diagnoser.py` patterns

**Typical use cases:**
- Finite element analysis (FEA) for stress/strain
- Heat conduction problems
- Elastodynamics simulations

#### ASME V&V 20-2009: CFD and Heat Transfer Validation

**Apply when:**
- Simulating fluid flow, heat transfer, or phase transformation
- Working with Navier-Stokes, heat equation, Allen-Cahn, or Cahn-Hilliard equations
- Need to validate against experimental data or benchmark solutions

**Key sections relevant to this package:**
- Section 4.3-4.4: Validation experiments and metrics → `result_validator.py`
- Section 5.2: Numerical error estimation → stability checks
- Section 6: Uncertainty quantification → statistical validation

**Typical use cases:**
- Phase-field simulations (solidification, grain growth)
- Thermal diffusion problems
- Coupled heat and mass transfer

#### ASME V&V 40-2018: Risk-Informed V&V for High-Consequence Applications

**Apply when:**
- Simulation results inform critical decisions (e.g., material qualification, process optimization)
- Need to assess credibility in absence of complete validation data
- Must document evidence and reasoning for regulatory or quality purposes

**Key sections relevant to this package:**
- Section 5: Credibility assessment → confidence scoring
- Section 6: Model form uncertainty → conservation checks
- Section 7: Evidence documentation → JSON outputs

**Typical use cases:**
- Materials qualification for aerospace/medical/nuclear applications
- Process parameter optimization for manufacturing
- Predictive modeling with economic or safety consequences

#### NASA-STD-7009A: M&S Credibility for Space Systems (General Framework)

**Apply when:**
- Need a comprehensive, risk-based M&S credibility framework
- Working on NASA projects or contracts
- Want general-purpose V&V guidance beyond ASME domain-specific standards

**Key sections relevant to this package:**
- Section 3: Verification → pre-flight + runtime checks
- Section 4: Validation → post-flight validation
- Section 5: Risk-based credibility assessment → confidence scoring

**Typical use cases:**
- Space systems thermal/structural analysis
- Generic scientific computing requiring credibility assessment
- Any domain requiring documented M&S credibility evidence

---

## Cross-Standard Mapping: Three-Stage Validation

### Stage 1: Pre-flight (Verification Focus)

| Standard | Relevant Section | Activity |
|----------|-----------------|----------|
| V&V 10 | Section 3.2 | Code verification: input validation |
| V&V 20 | Section 5.2 | Discretization error assessment |
| V&V 40 | Section 7.2 | Evidence of input credibility |
| NASA-STD-7009A | Section 3.2 | Verification planning |

**Package implementation:** `preflight_checker.py --config --required --ranges`

### Stage 2: Runtime (Solution Verification Focus)

| Standard | Relevant Section | Activity |
|----------|-----------------|----------|
| V&V 10 | Section 4.1 | Solution verification via convergence |
| V&V 20 | Section 5.3 | Iterative convergence assessment |
| V&V 40 | Section 6.3 | Model form uncertainty monitoring |
| NASA-STD-7009A | Section 3.3 | In-process verification checks |

**Package implementation:** `runtime_monitor.py --log --residual-growth --dt-drop`

### Stage 3: Post-flight (Validation Focus)

| Standard | Relevant Section | Activity |
|----------|-----------------|----------|
| V&V 10 | Section 4.2 | Comparison to analytical/reference |
| V&V 20 | Section 4.4 | Validation metrics evaluation |
| V&V 40 | Section 5.1 | Credibility factor assessment |
| NASA-STD-7009A | Section 4.3 | Validation evidence comparison |

**Package implementation:** `result_validator.py --metrics --bound-min --bound-max --mass-tol`

---

## Standard-Compliant Documentation

### Mapping Package JSON Outputs to Standard Requirements

#### V&V 10 Evidence Requirements → Package Outputs

| V&V 10 Requirement | JSON Field | Script |
|--------------------|------------|--------|
| Input parameter documentation | config (user-provided) | `preflight_checker.py` |
| Verification test results | `report.status`, `report.blockers` | `preflight_checker.py` |
| Convergence metrics | `residual_stats`, `dt_stats` | `runtime_monitor.py` |
| Error quantification | `failed_checks`, `conservation_drift` | `result_validator.py` |

#### V&V 20 Validation Evidence → Package Outputs

| V&V 20 Requirement | JSON Field | Script |
|--------------------|------------|--------|
| Validation metrics | `checks`, `confidence_score` | `result_validator.py` |
| Comparison data | `field_stats`, `bound_violations` | `result_validator.py` |
| Uncertainty quantification | `statistical_checks` | `result_validator.py` |

#### V&V 40 Credibility Factors → Package Outputs

| V&V 40 Factor | JSON Field | Script |
|---------------|------------|--------|
| Input credibility | `report.status`, param validation | `preflight_checker.py` |
| Code verification evidence | blockers/warnings count | `preflight_checker.py` |
| Validation evidence | `checks`, `confidence_score` | `result_validator.py` |
| Model form credibility | conservation checks | `result_validator.py` |

#### NASA-STD-7009A M&S Documentation → Package Outputs

| NASA Requirement | JSON Field | Script |
|------------------|------------|--------|
| M&S inputs | config file (user-provided) | All scripts |
| Verification results | pre-flight + runtime status | Stage 1 + 2 |
| Validation results | post-flight checks | Stage 3 |
| Anomaly documentation | `probable_causes`, `recommended_fixes` | `failure_diagnoser.py` |

---

## Compliance Checklist

### Quick Reference: Using This Package for Standards Compliance

#### For ASME V&V 10 Compliance (Verification)

- [ ] Document all input parameters (config file)
- [ ] Run `preflight_checker.py` and record status
- [ ] Monitor convergence with `runtime_monitor.py` during execution
- [ ] Document any blockers or warnings and their resolution
- [ ] Retain JSON outputs for traceability

#### For ASME V&V 20 Compliance (CFD/Heat Transfer Validation)

- [ ] Complete V&V 10 verification activities (above)
- [ ] Define validation metrics (`--bound-min`, `--bound-max`, `--mass-tol`)
- [ ] Run `result_validator.py` on simulation outputs
- [ ] Calculate and record confidence score
- [ ] Document failed checks and corrective actions

#### For ASME V&V 40 Compliance (Risk-Informed Credibility)

- [ ] Identify Question of Interest (QoI) and define relevant checks
- [ ] Assess credibility factors (input, code, validation, model form)
- [ ] Use confidence score as quantitative credibility metric
- [ ] Document evidence and reasoning in traceability records
- [ ] Maintain JSON outputs as evidence artifacts

#### For NASA-STD-7009A Compliance (M&S Credibility)

- [ ] Develop verification plan (pre-flight checklist)
- [ ] Execute verification activities (Stage 1 + 2)
- [ ] Collect validation evidence (Stage 3)
- [ ] Perform uncertainty quantification (statistical validation)
- [ ] Document anomalies and resolutions (`failure_diagnoser.py`)
- [ ] Archive all JSON outputs and logs for audit trail

---

## References

### ASME Standards

- **ASME V&V 10-2006**: *Guide for Verification and Validation in Computational Solid Mechanics*. American Society of Mechanical Engineers.
- **ASME V&V 20-2009**: *Standard for Verification and Validation in Computational Fluid Dynamics and Heat Transfer*. American Society of Mechanical Engineers.
- **ASME V&V 40-2018**: *Assessing Credibility of Computational Modeling through Verification and Validation: Application to Medical Devices*. American Society of Mechanical Engineers.

### NASA Standards

- **NASA-STD-7009A** (2016): *Standard for Models and Simulations*. National Aeronautics and Space Administration. [Currently supported by this skill; see note below]
- **NASA-STD-7009B** (2024): *Standard for Models and Simulations* (Revision B). Updates to credibility assessment framework, enhanced uncertainty quantification requirements, and updated M&S lifecycle guidance. **Supersedes NASA-STD-7009A for all new projects as of 2024.**

**Note on Standard Version**: This skill was initially developed against NASA-STD-7009A (2016). For new projects (2024+), NASA-STD-7009B is the authoritative reference. The core validation concepts (verification planning, evidence collection, credibility assessment) remain consistent between versions; primary differences are in uncertainty quantification rigor and lifecycle documentation. Users requiring NASA-STD-7009B compliance should reference that standard directly and adjust uncertainty and documentation requirements accordingly.

### IEEE Standards

- **IEEE 1012-2024**: *Standard for System, Software, and Hardware Verification and Validation*. Institute of Electrical and Electronics Engineers. Most recent revision of the software V&V standard; applicable to computational models and simulation software. Expands scope to include system-level and hardware V&V alongside software.

### Additional Reading

- Oberkampf, W.L., & Roy, C.J. (2010). *Verification and Validation in Scientific Computing*. Cambridge University Press. (Comprehensive textbook bridging theory and standards)
- AIAA G-077-1998: *Guide for the Verification and Validation of Computational Fluid Dynamics Simulations*. (Precursor to ASME V&V 20)
- Roache, P.J. (2009). *Fundamentals of Verification and Validation*. Hermosa Publishers. (Definitive reference for GCI and Richardson extrapolation)

---

## Revision History

- **v1.0.0** (2026-02-08): Initial release. Comprehensive mapping of simulation-validator components to ASME V&V 10/20/40 and NASA-STD-7009A standards.
