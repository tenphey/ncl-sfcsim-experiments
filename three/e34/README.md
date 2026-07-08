# E34: Fixed B34 Scenario in the Fourth NCCR Bin

## Purpose

E34 is the fourth experiment in the new 8-bin `NCCR_total` study.

This experiment focuses on the following target region:

- `0.56 < NCCR_total <= 1.00`
- `CCR_data ~= IDR_image`

The role of E34 is to observe the behavior of `HEFT`, `DHEFT`, and `NHEFT`
around the communication-computation balance region just above E33 in the new `0.1 < NCCR < 10` design,
while keeping traditional data communication and image communication roughly
balanced.

## Design

### Scenario type

E34 is **not** a parameter sweep experiment.

It is a **fixed-scenario repeated-seed experiment**:

- one tuned property set: `b34.properties`
- many random seeds
- final statistics only on seeds that actually satisfy the B34 condition

### B34 condition

The analysis-side condition is:

- `0.56 < NCCR_total <= 1.00`
- `|CCR_data - IDR_image| / ((CCR_data + IDR_image)/2) <= 10%`

So `CCR_data ~= IDR_image` is implemented as a practical **relative**
tolerance, not as exact equality and not as a fixed absolute gap.

### Position in the new 8-bin plan

E34 corresponds to the fourth bucket:

- `(0.56, 1.00]`

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

## Why E34 exists

Earlier experiments (`E21-E29`) already showed that `NCCR_total` and the
`CCR_data` / `IDR_image` relationship are useful for explaining when `NHEFT`
becomes stronger.

E34 continues the more systematic follow-up started from E31:

1. keep `CCR_data` and `IDR_image` approximately balanced,
2. divide `NCCR_total` into finer logarithmic bins,
3. compare algorithm behavior bin by bin.

This fourth bin is the next step after E33, so it helps show how algorithm
behavior changes when `NCCR_total` approaches the balance point near `1.0`.

## Property Design

`b34.properties` is tuned from the low-communication balanced setting and aims
to push both:

- traditional data communication, and
- image communication

into a small but still non-trivial region, so that total `NCCR_total` stays in
the fourth bucket while `CCR_data` remains close to `IDR_image`.

### Verified snapshot

With the current `b34.properties` and `random_seed=2503`, the project produced:

- `CCR_data = 0.4029`
- `IDR_image = 0.4380`
- `NCCR_total = 0.8409`

This means the current tuned profile falls into the intended target region:

- `0.56 < 0.8409 <= 1.00`
- `|0.4029 - 0.4380| / ((0.4029 + 0.4380)/2) = 8.35% <= 10%`

Note:

- the fixed-seed snapshot is mainly for sanity checking the NCCR bucket,
- the `CCR_data ~= IDR_image` judgment for the experiment is based on the
  percentage rule inside `analyze_results.py`,
- the final experiment statistics are still determined by `analyze_results.py`,
  which filters all seeds using the same B34 rule.

## Usage

### Normal run

```bash
python3 experiments/e34/run_experiment.py
```

### Dry run

```bash
E34_DRY_RUN=1 python3 experiments/e34/run_experiment.py
```

### Fewer seeds

```bash
E34_NUM_SEEDS=10 python3 experiments/e34/run_experiment.py
```

### Analyze one run

```bash
python3 experiments/e34/analyze_results.py run_YYYYMMDD_HHMMSS_150_100
```

## Important Counting Rule

E34 follows the same counting logic as the earlier `E2X` fixed-scenario
experiments:

1. `run_experiment.py` executes all selected seeds and stores all raw results.
2. `analyze_results.py` re-parses each run log.
3. Only runs that actually satisfy the B34 condition are counted in the final
   summary.

So even if some seeds drift outside the intended target region, they are still
kept in the raw outputs, but ignored by the final statistics.

## Outputs

Each run folder contains:

- `grid_e34_results.csv`
- `run_manifest.json`
- `b34_properties_snapshot.properties`
- `logs/run_seed_<seed>.log`

The analysis script produces:

- `grid_e34_summary.csv`
- `e34_seed_metrics_with_b34_flag.csv`
- `e34_nheft_loss_seeds_by_scenario.json`
- `e34_summary_table.png`
- `e34_robust_table.png`
- `e34_makespan_mean_comparison.png`
- `e34_makespan_boxplot.png`
- `e34_gain_histogram.png`

## Expected Role in the Whole Study

E34 is not expected to be the strongest region for `NHEFT`.

Its main value is to provide a clean baseline for the new 8-bin experiment
series:

- balanced-borderline `NCCR_total`,
- balanced `CCR_data` and `IDR_image`,
- repeated-seed evaluation under one fixed profile.

Later bins (`E35-E38`) can then be compared against E34 to see how the
advantage of `NHEFT` changes as `NCCR_total` grows.
