# E45: Fixed B45 Scenario in the Fifth NCCR Bin

## Purpose

E45 is the fifth experiment in the new 8-bin `NCCR_total` study.

This experiment focuses on the following target region:

- `1.00 < NCCR_total <= 1.78`
- `CCR_data < IDR_image`
- `|CCR_data - IDR_image| / ((CCR_data + IDR_image)/2) >= 20%`

The role of E45 is to observe the behavior of `HEFT`, `DHEFT`, and `NHEFT`
in the early communication-dominant region of the new `0.1 < NCCR < 10` design,
while making image communication explicitly larger than traditional data communication.

## Design

### Scenario type

E45 is **not** a parameter sweep experiment.

It is a **fixed-scenario repeated-seed experiment**:

- one tuned property set: `b45.properties`
- many random seeds
- final statistics only on seeds that actually satisfy the B45 condition

### B45 condition

The analysis-side condition is:

- `1.00 < NCCR_total <= 1.78`
- `CCR_data < IDR_image`
- `|CCR_data - IDR_image| / ((CCR_data + IDR_image)/2) >= 20%`

So this series keeps `IDR_image` clearly larger than `CCR_data` using a
practical relative-gap rule.

### Position in the new 8-bin plan

E45 corresponds to the fifth bucket:

- `(1.00, 1.78]`

The full planned `NCCR_total` bins are:

1. `(0.10, 0.18]`
2. `(0.18, 0.32]`
3. `(0.32, 0.56]`
4. `(0.56, 1.00]`
5. `(1.00, 1.78]`
6. `(1.78, 3.16]`
7. `(3.16, 5.62]`
8. `(5.62, 10.00)`

The second wave (`E41-E48`) is designed under the common constraint:

- `CCR_data < IDR_image`
- relative gap `>= 20%`

## Why E45 exists

E45 is the image-dominant counterpart of the balanced `E3X` series.

It helps answer a more specific question:

1. keep the same 8-bin `NCCR_total` structure,
2. make image communication clearly larger than traditional data communication,
3. compare algorithm behavior bin by bin.

## Property Design

`b45.properties` is derived from the corresponding `E3X` profile, but shifted
so that:

- traditional data communication becomes smaller,
- image communication becomes larger,
- total `NCCR_total` stays in the same bucket,
- and `IDR_image` remains at least 20% larger than `CCR_data` under the
  analysis rule.

### Verified snapshot

With the current `b45.properties` and `random_seed=2503`, the project produced:

- `CCR_data = 0.6255`
- `IDR_image = 0.9703`
- `NCCR_total = 1.5958`
- `relative gap = 43.21%`

This means the current tuned profile falls into the intended target region:

- `1.00 < 1.5958 <= 1.78`
- `IDR_image > CCR_data`
- `relative gap = 43.21% >= 20%`


## Usage

### Normal run

```bash
python3 experiments/e45/run_experiment.py
```

### Dry run

```bash
E45_DRY_RUN=1 python3 experiments/e45/run_experiment.py
```

### Fewer seeds

```bash
E45_NUM_SEEDS=10 python3 experiments/e45/run_experiment.py
```

### Analyze one run

```bash
python3 experiments/e45/analyze_results.py run_YYYYMMDD_HHMMSS_150_100
```

## Important Counting Rule

E45 follows the same counting logic as the earlier fixed-scenario experiments:

1. `run_experiment.py` executes all selected seeds and stores all raw results.
2. `analyze_results.py` re-parses each run log.
3. Only runs that actually satisfy the B45 condition are counted in the final
   summary.

So even if some seeds drift outside the intended target region, they are still
kept in the raw outputs, but ignored by the final statistics.

## Outputs

Each run folder contains:

- `grid_e45_results.csv`
- `run_manifest.json`
- `b45_properties_snapshot.properties`
- `logs/run_seed_<seed>.log`

The analysis script produces:

- `grid_e45_summary.csv`
- `e45_seed_metrics_with_b45_flag.csv`
- `e45_nheft_loss_seeds_by_scenario.json`
- `e45_summary_table.png`
- `e45_robust_table.png`
- `e45_makespan_mean_comparison.png`
- `e45_makespan_boxplot.png`
- `e45_gain_histogram.png`
