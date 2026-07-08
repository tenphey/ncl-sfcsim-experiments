# E37: Fixed B37 Scenario in the Seventh NCCR Bin

## Purpose

E37 is the seventh experiment in the new 8-bin `NCCR_total` study.

This experiment focuses on the following target region:

- `3.16 < NCCR_total <= 5.62`
- `CCR_data ~= IDR_image`

The role of E37 is to observe the behavior of `HEFT`, `DHEFT`, and `NHEFT`
in the strong communication-dominant region above E36 in the new `0.1 < NCCR < 10` design,
while keeping traditional data communication and image communication roughly
balanced.

## Design

### Scenario type

E37 is **not** a parameter sweep experiment.

It is a **fixed-scenario repeated-seed experiment**:

- one tuned property set: `b37.properties`
- many random seeds
- final statistics only on seeds that actually satisfy the B37 condition

### B37 condition

The analysis-side condition is:

- `3.16 < NCCR_total <= 5.62`
- `|CCR_data - IDR_image| / ((CCR_data + IDR_image)/2) <= 10%`

So `CCR_data ~= IDR_image` is implemented as a practical **relative**
tolerance, not as exact equality and not as a fixed absolute gap.

### Position in the new 8-bin plan

E37 corresponds to the seventh bucket:

- `(3.16, 5.62]`

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

## Why E37 exists

Earlier experiments (`E21-E29`) already showed that `NCCR_total` and the
`CCR_data` / `IDR_image` relationship are useful for explaining when `NHEFT`
becomes stronger.

E37 continues the more systematic follow-up started from E31:

1. keep `CCR_data` and `IDR_image` approximately balanced,
2. divide `NCCR_total` into finer logarithmic bins,
3. compare algorithm behavior bin by bin.

This seventh bin is the next step after E36, so it helps show how algorithm
behavior changes once the system moves into a clearly strong communication-dominant region.

## Property Design

`b37.properties` is tuned from the low-communication balanced setting and aims
to push both:

- traditional data communication, and
- image communication

into a small but still non-trivial region, so that total `NCCR_total` stays in
the seventh bucket while `CCR_data` remains close to `IDR_image`.

### Verified snapshot

With the current `b37.properties` and `random_seed=2503`, the project produced:

- `CCR_data = 1.5942`
- `IDR_image = 1.6060`
- `NCCR_total = 3.2002`

This means the current tuned profile falls into the intended target region:

- `3.16 < 3.2002 <= 5.62`
- `|1.5942 - 1.6060| / ((1.5942 + 1.6060)/2) = 0.74% <= 10%`

## Usage

### Normal run

```bash
python3 experiments/e37/run_experiment.py
```

### Dry run

```bash
E37_DRY_RUN=1 python3 experiments/e37/run_experiment.py
```

### Fewer seeds

```bash
E37_NUM_SEEDS=10 python3 experiments/e37/run_experiment.py
```

### Analyze one run

```bash
python3 experiments/e37/analyze_results.py run_YYYYMMDD_HHMMSS_150_100
```

## Important Counting Rule

E37 follows the same counting logic as the earlier `E2X` fixed-scenario
experiments:

1. `run_experiment.py` executes all selected seeds and stores all raw results.
2. `analyze_results.py` re-parses each run log.
3. Only runs that actually satisfy the B37 condition are counted in the final
   summary.

So even if some seeds drift outside the intended target region, they are still
kept in the raw outputs, but ignored by the final statistics.

## Outputs

Each run folder contains:

- `grid_e37_results.csv`
- `run_manifest.json`
- `b37_properties_snapshot.properties`
- `logs/run_seed_<seed>.log`

The analysis script produces:

- `grid_e37_summary.csv`
- `e37_seed_metrics_with_b37_flag.csv`
- `e37_nheft_loss_seeds_by_scenario.json`
- `e37_summary_table.png`
- `e37_robust_table.png`
- `e37_makespan_mean_comparison.png`
- `e37_makespan_boxplot.png`
- `e37_gain_histogram.png`

## Expected Role in the Whole Study

E37 is not expected to be the strongest region for `NHEFT`.

Its main value is to provide a clean baseline for the new 8-bin experiment
series:

- strong communication-dominant `NCCR_total`,
- balanced `CCR_data` and `IDR_image`,
- repeated-seed evaluation under one fixed profile.

Later bin (`E38`) can then be compared against E37 to see how the
advantage of `NHEFT` changes as `NCCR_total` grows.
