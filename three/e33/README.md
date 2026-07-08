# E33: Fixed B33 Scenario in the Third NCCR Bin

## Purpose

E33 is the third experiment in the new 8-bin `NCCR_total` study.

This experiment focuses on the following target region:

- `0.32 < NCCR_total <= 0.56`
- `CCR_data ~= IDR_image`

The role of E33 is to observe the behavior of `HEFT`, `DHEFT`, and `NHEFT`
in the lower-middle communication region just above E32 in the new `0.1 < NCCR < 10` design,
while keeping traditional data communication and image communication roughly
balanced.

## Design

### Scenario type

E33 is **not** a parameter sweep experiment.

It is a **fixed-scenario repeated-seed experiment**:

- one tuned property set: `b33.properties`
- many random seeds
- final statistics only on seeds that actually satisfy the B33 condition

### B33 condition

The analysis-side condition is:

- `0.32 < NCCR_total <= 0.56`
- `|CCR_data - IDR_image| <= 0.02`

So `CCR_data ~= IDR_image` is implemented as a practical absolute tolerance,
not as exact equality.

### Position in the new 8-bin plan

E33 corresponds to the third bucket:

- `(0.32, 0.56]`

The full planned `NCCR_total` bins are:

1. `(0.10, 0.18]`
2. `(0.18, 0.32]`
3. `(0.32, 0.56]`
4. `(0.56, 1.00]`
5. `(1.00, 1.78]`
6. `(1.78, 3.16]`
7. `(3.16, 5.62]`
8. `(5.62, 10.00)`

The first wave (`E31-E38`) is designed under the common constraint:

- `CCR_data ~= IDR_image`

## Why E33 exists

Earlier experiments (`E21-E29`) already showed that `NCCR_total` and the
`CCR_data` / `IDR_image` relationship are useful for explaining when `NHEFT`
becomes stronger.

E33 continues the more systematic follow-up started from E31:

1. keep `CCR_data` and `IDR_image` approximately balanced,
2. divide `NCCR_total` into finer logarithmic bins,
3. compare algorithm behavior bin by bin.

This third bin is the next step after E32, so it helps show how algorithm
behavior changes once `NCCR_total` moves from clearly low communication into a
higher but still moderate region.

## Property Design

`b33.properties` is tuned from the low-communication balanced setting and aims
to push both:

- traditional data communication, and
- image communication

into a small but still non-trivial region, so that total `NCCR_total` stays in
the third bucket while `CCR_data` remains close to `IDR_image`.

### Verified snapshot

With the current `b33.properties` and `random_seed=2503`, the project produced:

- `CCR_data = 0.2065`
- `IDR_image = 0.2263`
- `NCCR_total = 0.4328`

This means the current tuned profile falls into the intended target region:

- `0.32 < 0.4328 <= 0.56`
- `|0.2065 - 0.2263| = 0.0198 <= 0.02`

## Usage

### Normal run

```bash
python3 experiments/e33/run_experiment.py
```

### Dry run

```bash
E33_DRY_RUN=1 python3 experiments/e33/run_experiment.py
```

### Fewer seeds

```bash
E33_NUM_SEEDS=10 python3 experiments/e33/run_experiment.py
```

### Analyze one run

```bash
python3 experiments/e33/analyze_results.py run_YYYYMMDD_HHMMSS_150_100
```

## Important Counting Rule

E33 follows the same counting logic as the earlier `E2X` fixed-scenario
experiments:

1. `run_experiment.py` executes all selected seeds and stores all raw results.
2. `analyze_results.py` re-parses each run log.
3. Only runs that actually satisfy the B33 condition are counted in the final
   summary.

So even if some seeds drift outside the intended target region, they are still
kept in the raw outputs, but ignored by the final statistics.

## Outputs

Each run folder contains:

- `grid_e33_results.csv`
- `run_manifest.json`
- `b33_properties_snapshot.properties`
- `logs/run_seed_<seed>.log`

The analysis script produces:

- `grid_e33_summary.csv`
- `e33_seed_metrics_with_b33_flag.csv`
- `e33_nheft_loss_seeds_by_scenario.json`
- `e33_summary_table.png`
- `e33_robust_table.png`
- `e33_makespan_mean_comparison.png`
- `e33_makespan_boxplot.png`
- `e33_gain_histogram.png`

## Expected Role in the Whole Study

E33 is not expected to be the strongest region for `NHEFT`.

Its main value is to provide a clean baseline for the new 8-bin experiment
series:

- lower-middle `NCCR_total`,
- balanced `CCR_data` and `IDR_image`,
- repeated-seed evaluation under one fixed profile.

Later bins (`E34-E38`) can then be compared against E33 to see how the
advantage of `NHEFT` changes as `NCCR_total` grows.
