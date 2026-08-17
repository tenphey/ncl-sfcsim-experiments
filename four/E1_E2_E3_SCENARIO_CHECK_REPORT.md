# E1/E2/E3 Scenario Check Report

This file is a cumulative adjustment/check report for the `e1`, `e2`, and `e3`
scenario-grid experiments under `experiments/four/`.

When experiment settings are changed in the future, including small parameter
adjustments, a new dated section should be appended to this report.

---

## Record: 2026-08-12

### Purpose

This note records the verification of the `e1`, `e2`, and `e3` scenario-grid
experiments under `experiments/four/`.

Checked series:

- `e1`: `e11-e18` with suffixes `x/y/z`
- `e2`: `e21-e28` with suffixes `x/y/z`
- `e3`: `e31-e38` with suffixes `x/y/z`

Total checked scenario directories:

- `e1`: 24
- `e2`: 24
- `e3`: 24
- overall: 72

### What Was Checked

For every scenario directory, the following items were verified:

1. The directory exists in the expected `8 buckets x 3 compositions` grid.
2. The local `b**.properties` file matches the intended:
   - NCCR bucket
   - communication composition (`x/y/z`)
3. `run_experiment.py` uses that directory's own local `b**.properties`.
4. `analyze_results.py` filters results strictly so that only runs satisfying
   the intended scenario condition are included in analysis output.

### Scenario Meaning

- `x`: `CCR ~= IDR`
- `y`: `CCR < IDR`
- `z`: `CCR > IDR`

NCCR buckets:

1. `(0.10, 0.18]`
2. `(0.18, 0.32]`
3. `(0.32, 0.56]`
4. `(0.56, 1.00]`
5. `(1.00, 1.78]`
6. `(1.78, 3.16]`
7. `(3.16, 5.62]`
8. `(5.62, 10.00]`

### Filtering Logic Confirmed

The `four/` scenario analyzers do not use the older `three/` style constant-only
format. Instead, each directory defines its own `filter_scenario_rows(ok)`
function and then keeps only:

- `filtered = scenario_ok[scenario_ok["scenario_match"]].copy()`

The scenario filters were confirmed to follow the intended logic:

- `x` scenarios:
  - target NCCR bucket
  - balanced condition using `|CCR_data - IDR_image| <= tolerance`
- `y` scenarios:
  - target NCCR bucket
  - `CCR_data < IDR_image`
  - relative gap threshold `>= 20%`
- `z` scenarios:
  - target NCCR bucket
  - `CCR_data > IDR_image`
  - relative gap threshold `>= 20%`

So the analyzers are not just plotting all successful runs. They are explicitly
screening out runs that fall outside the designed scenario condition.

### Result

Final verification summary:

- `e1`: `total=24`, `ok=24`, `bad=0`
- `e2`: `total=24`, `ok=24`, `bad=0`
- `e3`: `total=24`, `ok=24`, `bad=0`

### Conclusion

As of `2026-08-12`, the `e1`, `e2`, and `e3` scenario-grid experiments in
`experiments/four/` are consistent in the following sense:

- the scenario directories are complete,
- the local parameter files match the intended bucket and `x/y/z` class,
- the run scripts use the local parameter files,
- and the analysis scripts strictly keep only runs that satisfy the designed
  scenario condition.

This means the current `e1/e2/e3` 24-scenario matrix can be treated as
internally aligned at the level of:

- scenario naming
- scenario parameter targeting
- and scenario-based result filtering
