# E42: Fixed B42 Scenario in the Second NCCR Bin

## Purpose

E42 is the second experiment in the new 8-bin `NCCR_total` study.

This experiment focuses on the following target region:

- `0.18 < NCCR_total <= 0.32`
- `CCR_data < IDR_image`
- `|CCR_data - IDR_image| / ((CCR_data + IDR_image)/2) >= 20%`

The role of E42 is to observe the behavior of `HEFT`, `DHEFT`, and `NHEFT`
in the low region of the new `0.1 < NCCR < 10` design,
while making image communication explicitly larger than traditional data communication.

## Design

### Scenario type

E42 is **not** a parameter sweep experiment.

It is a **fixed-scenario repeated-seed experiment**:

- one tuned property set: `b42.properties`
- many random seeds
- final statistics only on seeds that actually satisfy the B42 condition

### B42 condition

The analysis-side condition is:

- `0.18 < NCCR_total <= 0.32`
- `CCR_data < IDR_image`
- `|CCR_data - IDR_image| / ((CCR_data + IDR_image)/2) >= 20%`

So this series keeps `IDR_image` clearly larger than `CCR_data` using a
practical relative-gap rule.

### Position in the new 8-bin plan

E42 corresponds to the second bucket:

- `(0.18, 0.32]`

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

## Why E42 exists

E42 is the image-dominant counterpart of the balanced `E3X` series.

It helps answer a more specific question:

1. keep the same 8-bin `NCCR_total` structure,
2. make image communication clearly larger than traditional data communication,
3. compare algorithm behavior bin by bin.

## Property Design

`b42.properties` is derived from the corresponding `E3X` profile, but shifted
so that:

- traditional data communication becomes smaller,
- image communication becomes larger,
- total `NCCR_total` stays in the same bucket,
- and `IDR_image` remains at least 20% larger than `CCR_data` under the
  analysis rule.

### Verified snapshot

With the current `b42.properties` and `random_seed=2503`, the project produced:

- `CCR_data = 0.0983`
- `IDR_image = 0.1356`
- `NCCR_total = 0.2339`
- `relative gap = 31.89%`

This means the current tuned profile falls into the intended target region:

- `0.18 < 0.2339 <= 0.32`
- `IDR_image > CCR_data`
- `relative gap = 31.89% >= 20%`


## Usage

### Normal run

```bash
python3 experiments/e42/run_experiment.py
```

### Dry run

```bash
E42_DRY_RUN=1 python3 experiments/e42/run_experiment.py
```

### Fewer seeds

```bash
E42_NUM_SEEDS=10 python3 experiments/e42/run_experiment.py
```

### Analyze one run

```bash
python3 experiments/e42/analyze_results.py run_YYYYMMDD_HHMMSS_150_100
```

## Important Counting Rule

E42 follows the same counting logic as the earlier fixed-scenario experiments:

1. `run_experiment.py` executes all selected seeds and stores all raw results.
2. `analyze_results.py` re-parses each run log.
3. Only runs that actually satisfy the B42 condition are counted in the final
   summary.

So even if some seeds drift outside the intended target region, they are still
kept in the raw outputs, but ignored by the final statistics.

## Outputs

Each run folder contains:

- `grid_e42_results.csv`
- `run_manifest.json`
- `b42_properties_snapshot.properties`
- `logs/run_seed_<seed>.log`

The analysis script produces:

- `grid_e42_summary.csv`
- `e42_seed_metrics_with_b42_flag.csv`
- `e42_nheft_loss_seeds_by_scenario.json`
- `e42_summary_table.png`
- `e42_robust_table.png`
- `e42_makespan_mean_comparison.png`
- `e42_makespan_boxplot.png`
- `e42_gain_histogram.png`
