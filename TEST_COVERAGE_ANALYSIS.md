# Test Coverage Analysis

## Current State

The codebase has **zero automated tests**. There are no test files, no test
framework configured, and no test dependencies declared. Validation currently
relies solely on the `evaluate.py` scoring engine running during the optimization
loop — if a design breaks constraints or doesn't improve weight, it's discarded.

This works for the optimization workflow but leaves critical logic unverified
in isolation. Regressions in the scoring engine, parsing functions, or
constraint checks would silently corrupt results.

## Recommended Test Framework

**pytest** — lightweight, no boilerplate, good for the mix of pure functions and
subprocess-based integration tests in this project. Add to `pyproject.toml`:

```toml
[project.optional-dependencies]
test = ["pytest>=8.0"]
```

## Priority Areas for Test Coverage

### 1. Growth Factor Functions (HIGH — `evaluate.py:54-176`)

These six pure functions are the core of the scoring model. They have
well-defined boundary conditions, piecewise linear behavior, and are easy to
test exhaustively. Bugs here silently corrupt every experiment result.

**Functions to test:**
- `sgr_base(weight_g)` — 9 weight brackets, boundary values
- `temperature_factor(effective_temp_c)` — 7 ranges including edge cases at 18, 22, 26, 30, 32, 34°C
- `dissolved_oxygen_factor(do_mg_l)` — 5 ranges, boundary at 2.0, 3.0, 5.0, 7.0
- `density_factor(density_kg_m3)` — 6 ranges, boundary at 5, 15, 25, 40, 60
- `water_quality_factor(tan_production, tan_removal)` — 6 ranges, zero-TAN edge case
- `turnover_factor(turnovers_per_hour)` — 6 ranges, boundary at 0.3, 0.5, 1.0, 2.5, 4.0

**Why:** These are pure functions with no side effects — ideal unit test targets.
Each has piecewise-linear logic with multiple boundary conditions where off-by-one
errors or wrong interpolation would be hard to catch manually.

**Example tests:**
- Verify return value is 1.0 at optimal input
- Verify return value is 0.0 at extreme/lethal input
- Verify monotonicity within expected ranges
- Verify exact boundary values (e.g., `temperature_factor(26)` should be 1.0)
- Verify output is always in [0, 1] range

### 2. Derived Parameter Calculations (HIGH — `evaluate.py:182-233`)

These functions translate raw design parameters into environmental conditions.
Incorrect computation here means the growth model receives wrong inputs.

**Functions to test:**
- `compute_effective_temp(params)` — additive model, test with various param combos
- `compute_do(params)` — complex model with aeration, biomass oxygen demand, clamping
- `compute_biofilter_capacity(params)` — multiplicative chain, verify dimensional analysis
- `compute_turnovers(params)` — simple ratio, test default params and edge cases

**Why:** `compute_do` in particular has non-trivial logic (saturation ceiling,
consumption drop, aeration efficiency) that should be validated against
expected dissolved oxygen values for known configurations.

### 3. Constraint Validation (HIGH — `evaluate.py:239-289`)

`validate_constraints` enforces hard engineering limits. A bug here could allow
physically impossible designs to be "kept" or reject valid ones.

**Tests needed:**
- Valid baseline design passes all constraints
- Structure oversized (length > 7620mm or width > 3657.6mm) fails
- Tank too large for structure width fails
- Gravity cascade violation detected (tank rim < biofilter top + 50)
- Pump TDH > 3.0m fails
- Lethal stocking density (>60 kg/m³ at 450g) fails
- Zero biofilter barrels fails
- Pump flow < 5 LPM fails
- Air pump < 5 LPM fails
- Combinations of multiple simultaneous constraint failures

### 4. Score Design Integration (MEDIUM — `evaluate.py:296-391`)

`score_design` orchestrates the 165-day simulation. Test the full pipeline
end-to-end with known parameter sets.

**Tests needed:**
- Baseline params produce weight in expected range (~300g)
- Optimal params produce weight near ~450g
- Degenerate params (zero fish, tiny tank) don't crash
- Output dict has all expected keys
- `surviving_count` matches `stocking_count * (1 - MORTALITY_RATE)`
- `constraints_pass` propagates correctly to result

### 5. Optimize.py Parsing Functions (MEDIUM — `optimize.py:104-244`)

Several string-parsing functions are fragile and have no validation.

**Functions to test:**
- `parse_run_log(log_content)` — extract weight and constraints from formatted output
- `extract_design_from_response(response)` — regex extraction of python code blocks
- `extract_description(response)` — extract DESCRIPTION line, tab/comma sanitization
- `get_best_weight()` — parse results.tsv for best kept weight

**Why:** These parse unstructured text (Claude API responses, log output).
Malformed input shouldn't crash the optimizer — it should return safe defaults.

**Edge cases to test:**
- Empty/missing log content
- Multiple code blocks in response (should take last)
- No code block in response (should return None)
- DESCRIPTION with tabs and commas gets sanitized
- results.tsv with mixed keep/discard rows
- results.tsv with malformed numbers

### 6. Git Helper Functions (LOW — `optimize.py:64-90`)

`git_commit`, `git_reset_last`, `get_git_hash` interact with git state.

**Tests needed (integration):**
- `git_commit` stages and commits design.py
- `git_reset_last` reverts the most recent commit
- `git_reset_last` handles single-commit repos gracefully

**Why:** Lower priority because these are thin wrappers around `git` commands,
but `git_reset_last` has fallback logic for single-commit repos that should be
verified.

## Suggested Test File Structure

```
tests/
├── conftest.py              # shared fixtures (baseline params, temp dirs)
├── test_growth_factors.py   # sgr_base, temperature_factor, etc.
├── test_derived_params.py   # compute_effective_temp, compute_do, etc.
├── test_constraints.py      # validate_constraints
├── test_score_design.py     # end-to-end scoring
└── test_optimize_parsing.py # parse_run_log, extract_design, etc.
```

## Impact Assessment

| Area | Risk if Untested | Effort to Add Tests | Priority |
|------|-----------------|---------------------|----------|
| Growth factor functions | Silent scoring corruption | Low (pure functions) | HIGH |
| Derived param calculations | Wrong environmental inputs | Low-Medium | HIGH |
| Constraint validation | Invalid designs kept/valid rejected | Low | HIGH |
| Score design integration | Wrong harvest predictions | Medium | MEDIUM |
| Optimize.py parsing | Crashes or lost experiments | Medium | MEDIUM |
| Git helpers | Failed commits, lost work | High (needs git fixtures) | LOW |
