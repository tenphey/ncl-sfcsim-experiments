# E43: Fixed B43 Scenario in the Third NCCR Bin

## Purpose

E43 is the third experiment in the new 8-bin `NCCR_total` study.

This experiment focuses on the following target region:

- `0.32 < NCCR_total <= 0.56`
- `CCR_data < IDR_image`
- `|CCR_data - IDR_image| / ((CCR_data + IDR_image)/2) >= 20%`

The role of E43 is to observe the behavior of `HEFT`, `DHEFT`, and `NHEFT`
in the low-to-moderate region of the new `0.1 < NCCR < 10` design,
while making image communication explicitly larger than traditional data communication.

## Design

### Scenario type

E43 is **not** a parameter sweep experiment.

It is a **fixed-scenario repeated-seed experiment**:

- one tuned property set: `b43.properties`
- many random seeds
- final statistics only on seeds that actually satisfy the B43 condition

### B43 condition

The analysis-side condition is:

- `0.32 < NCCR_total <= 0.56`
- `CCR_data < IDR_image`
- `|CCR_data - IDR_image| / ((CCR_data + IDR_image)/2) >= 20%`

So this series keeps `IDR_image` clearly larger than `CCR_data` using a
practical relative-gap rule.

### Position in the new 8-bin plan

E43 corresponds to the third bucket:

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

The second wave (`E41-E48`) is designed under the common constraint:

- `CCR_data < IDR_image`
- relative gap `>= 20%`

## Why E43 exists

E43 is the image-dominant counterpart of the balanced `E3X` series.

It helps answer a more specific question:

1. keep the same 8-bin `NCCR_total` structure,
2. make image communication clearly larger than traditional data communication,
3. compare algorithm behavior bin by bin.

## Property Design

`b43.properties` is derived from the corresponding `E3X` profile, but shifted
so that:

- traditional data communication becomes smaller,
- image communication becomes larger,
- total `NCCR_total` stays in the same bucket,
- and `IDR_image` remains at least 20% larger than `CCR_data` under the
  analysis rule.

### Verified snapshot

With the current `b43.properties` and `random_seed=2503`, the project produced:

- `CCR_data = 0.1868`
- `IDR_image = 0.2488`
- `NCCR_total = 0.4356`
- `relative gap = 28.47%`

This means the current tuned profile falls into the intended target region:

- `0.32 < 0.4356 <= 0.56`
- `IDR_image > CCR_data`
- `relative gap = 28.47% >= 20%`


## Usage

### Normal run

```bash
python3 experiments/e43/run_experiment.py
```

### Dry run

```bash
E43_DRY_RUN=1 python3 experiments/e43/run_experiment.py
```

### Fewer seeds

```bash
E43_NUM_SEEDS=10 python3 experiments/e43/run_experiment.py
```

### Analyze one run

```bash
python3 experiments/e43/analyze_results.py run_YYYYMMDD_HHMMSS_150_100
```

## Important Counting Rule

E43 follows the same counting logic as the earlier fixed-scenario experiments:

1. `run_experiment.py` executes all selected seeds and stores all raw results.
2. `analyze_results.py` re-parses each run log.
3. Only runs that actually satisfy the B43 condition are counted in the final
   summary.

So even if some seeds drift outside the intended target region, they are still
kept in the raw outputs, but ignored by the final statistics.

## Outputs

Each run folder contains:

- `grid_e43_results.csv`
- `run_manifest.json`
- `b43_properties_snapshot.properties`
- `logs/run_seed_<seed>.log`

The analysis script produces:

- `grid_e43_summary.csv`
- `e43_seed_metrics_with_b43_flag.csv`
- `e43_nheft_loss_seeds_by_scenario.json`
- `e43_summary_table.png`
- `e43_robust_table.png`
- `e43_makespan_mean_comparison.png`
- `e43_makespan_boxplot.png`
- `e43_gain_histogram.png`
