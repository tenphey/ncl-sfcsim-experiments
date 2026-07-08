# E36: Fixed B36 Scenario in the Sixth NCCR Bin

## Purpose

E36 is the sixth experiment in the new 8-bin `NCCR_total` study.

This experiment focuses on the following target region:

- `1.78 < NCCR_total <= 3.16`
- `CCR_data ~= IDR_image`

The role of E36 is to observe the behavior of `HEFT`, `DHEFT`, and `NHEFT`
in the moderate communication-dominant region above E35 in the new `0.1 < NCCR < 10` design,
while keeping traditional data communication and image communication roughly
balanced.

## Design

### Scenario type

E36 is **not** a parameter sweep experiment.

It is a **fixed-scenario repeated-seed experiment**:

- one tuned property set: `b36.properties`
- many random seeds
- final statistics only on seeds that actually satisfy the B36 condition

### B36 condition

The analysis-side condition is:

- `1.78 < NCCR_total <= 3.16`
- `|CCR_data - IDR_image| / ((CCR_data + IDR_image)/2) <= 10%`

So `CCR_data ~= IDR_image` is implemented as a practical **relative**
tolerance, not as exact equality and not as a fixed absolute gap.

### Position in the new 8-bin plan

E36 corresponds to the sixth bucket:

- `(1.78, 3.16]`

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

## Why E36 exists

Earlier experiments (`E21-E29`) already showed that `NCCR_total` and the
`CCR_data` / `IDR_image` relationship are useful for explaining when `NHEFT`
becomes stronger.

E36 continues the more systematic follow-up started from E31:

1. keep `CCR_data` and `IDR_image` approximately balanced,
2. divide `NCCR_total` into finer logarithmic bins,
3. compare algorithm behavior bin by bin.

This sixth bin is the next step after E35, so it helps show how algorithm
behavior changes as the system moves deeper into the communication-dominant region.

## Property Design

`b36.properties` is tuned from the low-communication balanced setting and aims
to push both:

- traditional data communication, and
- image communication

into a small but still non-trivial region, so that total `NCCR_total` stays in
the sixth bucket while `CCR_data` remains close to `IDR_image`.

### Verified snapshot

With the current `b36.properties` and `random_seed=2503`, the project produced:

- `CCR_data = 0.9101`
- `IDR_image = 0.9274`
- `NCCR_total = 1.8375`

This means the current tuned profile falls into the intended target region:

- `1.78 < 1.8375 <= 3.16`
- `|0.9101 - 0.9274| / ((0.9101 + 0.9274)/2) = 1.88% <= 10%`

## Usage

### Normal run

```bash
python3 experiments/e36/run_experiment.py
```

### Dry run

```bash
E36_DRY_RUN=1 python3 experiments/e36/run_experiment.py
```

### Fewer seeds

```bash
E36_NUM_SEEDS=10 python3 experiments/e36/run_experiment.py
```

### Analyze one run

```bash
python3 experiments/e36/analyze_results.py run_YYYYMMDD_HHMMSS_150_100
```

## Important Counting Rule

E36 follows the same counting logic as the earlier `E2X` fixed-scenario
experiments:

1. `run_experiment.py` executes all selected seeds and stores all raw results.
2. `analyze_results.py` re-parses each run log.
3. Only runs that actually satisfy the B36 condition are counted in the final
   summary.

So even if some seeds drift outside the intended target region, they are still
kept in the raw outputs, but ignored by the final statistics.

## Outputs

Each run folder contains:

- `grid_e36_results.csv`
- `run_manifest.json`
- `b36_properties_snapshot.properties`
- `logs/run_seed_<seed>.log`

The analysis script produces:

- `grid_e36_summary.csv`
- `e36_seed_metrics_with_b36_flag.csv`
- `e36_nheft_loss_seeds_by_scenario.json`
- `e36_summary_table.png`
- `e36_robust_table.png`
- `e36_makespan_mean_comparison.png`
- `e36_makespan_boxplot.png`
- `e36_gain_histogram.png`

## Expected Role in the Whole Study

E36 is not expected to be the strongest region for `NHEFT`.

Its main value is to provide a clean baseline for the new 8-bin experiment
series:

- moderate communication-dominant `NCCR_total`,
- balanced `CCR_data` and `IDR_image`,
- repeated-seed evaluation under one fixed profile.

Later bins (`E37-E38`) can then be compared against E36 to see how the
advantage of `NHEFT` changes as `NCCR_total` grows.
