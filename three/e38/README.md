# E38: Fixed B38 Scenario in the Eighth NCCR Bin

## Purpose

E38 is the eighth experiment in the new 8-bin `NCCR_total` study.

This experiment focuses on the following target region:

- `5.62 < NCCR_total <= 10.00`
- `CCR_data ~= IDR_image`

The role of E38 is to observe the behavior of `HEFT`, `DHEFT`, and `NHEFT`
in the highest communication-dominant region above E37 in the new `0.1 < NCCR < 10` design,
while keeping traditional data communication and image communication roughly
balanced.

## Design

### Scenario type

E38 is **not** a parameter sweep experiment.

It is a **fixed-scenario repeated-seed experiment**:

- one tuned property set: `b38.properties`
- many random seeds
- final statistics only on seeds that actually satisfy the B38 condition

### B38 condition

The analysis-side condition is:

- `5.62 < NCCR_total <= 10.00`
- `|CCR_data - IDR_image| / ((CCR_data + IDR_image)/2) <= 10%`

So `CCR_data ~= IDR_image` is implemented as a practical **relative**
tolerance, not as exact equality and not as a fixed absolute gap.

### Position in the new 8-bin plan

E38 corresponds to the eighth bucket:

- `(5.62, 10.00)`

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

## Why E38 exists

Earlier experiments (`E21-E29`) already showed that `NCCR_total` and the
`CCR_data` / `IDR_image` relationship are useful for explaining when `NHEFT`
becomes stronger.

E38 continues the more systematic follow-up started from E31:

1. keep `CCR_data` and `IDR_image` approximately balanced,
2. divide `NCCR_total` into finer logarithmic bins,
3. compare algorithm behavior bin by bin.

This eighth bin is the next step after E37, so it helps show how algorithm
behavior changes in the most communication-dominant region covered by the current 8-bin design.

## Property Design

`b38.properties` is tuned from the low-communication balanced setting and aims
to push both:

- traditional data communication, and
- image communication

into a small but still non-trivial region, so that total `NCCR_total` stays in
the eighth bucket while `CCR_data` remains close to `IDR_image`.

### Verified snapshot

With the current `b38.properties` and `random_seed=2503`, the project produced:

- `CCR_data = 2.8145`
- `IDR_image = 2.8273`
- `NCCR_total = 5.6418`

This means the current tuned profile falls into the intended target region:

- `5.62 < 5.6418 <= 10.00`
- `|2.8145 - 2.8273| / ((2.8145 + 2.8273)/2) = 0.45% <= 10%`

## Usage

### Normal run

```bash
python3 experiments/e38/run_experiment.py
```

### Dry run

```bash
E38_DRY_RUN=1 python3 experiments/e38/run_experiment.py
```

### Fewer seeds

```bash
E38_NUM_SEEDS=10 python3 experiments/e38/run_experiment.py
```

### Analyze one run

```bash
python3 experiments/e38/analyze_results.py run_YYYYMMDD_HHMMSS_150_100
```

## Important Counting Rule

E38 follows the same counting logic as the earlier `E2X` fixed-scenario
experiments:

1. `run_experiment.py` executes all selected seeds and stores all raw results.
2. `analyze_results.py` re-parses each run log.
3. Only runs that actually satisfy the B38 condition are counted in the final
   summary.

So even if some seeds drift outside the intended target region, they are still
kept in the raw outputs, but ignored by the final statistics.

## Outputs

Each run folder contains:

- `grid_e38_results.csv`
- `run_manifest.json`
- `b38_properties_snapshot.properties`
- `logs/run_seed_<seed>.log`

The analysis script produces:

- `grid_e38_summary.csv`
- `e38_seed_metrics_with_b38_flag.csv`
- `e38_nheft_loss_seeds_by_scenario.json`
- `e38_summary_table.png`
- `e38_robust_table.png`
- `e38_makespan_mean_comparison.png`
- `e38_makespan_boxplot.png`
- `e38_gain_histogram.png`

## Expected Role in the Whole Study

E38 is not expected to be the strongest region for `NHEFT`.

Its main value is to provide a clean baseline for the new 8-bin experiment
series:

- highest communication-dominant `NCCR_total`,
- balanced `CCR_data` and `IDR_image`,
- repeated-seed evaluation under one fixed profile.

As the final bucket in this first 8-bin series, E38 provides the high-end
anchor for comparing how the advantage of `NHEFT` changes as `NCCR_total`
grows.
