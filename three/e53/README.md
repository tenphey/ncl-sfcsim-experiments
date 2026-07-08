# E53: Fixed B53 Scenario in the Third NCCR Bin

## Purpose

E53 is the third experiment in the new 8-bin `NCCR_total` study.

This experiment focuses on the following target region:

- `0.32 < NCCR_total <= 0.56`
- `CCR_data > IDR_image`
- `|CCR_data - IDR_image| / ((CCR_data + IDR_image)/2) >= 20%`

The role of E53 is to observe the behavior of `HEFT`, `DHEFT`, and `NHEFT`
in the low-to-moderate region of the new `0.1 < NCCR < 10` design,
while making traditional data communication explicitly larger than image communication.

## Design

### Scenario type

E53 is **not** a parameter sweep experiment.

It is a **fixed-scenario repeated-seed experiment**:

- one tuned property set: `b53.properties`
- many random seeds
- final statistics only on seeds that actually satisfy the B53 condition

### B53 condition

The analysis-side condition is:

- `0.32 < NCCR_total <= 0.56`
- `CCR_data > IDR_image`
- `|CCR_data - IDR_image| / ((CCR_data + IDR_image)/2) >= 20%`

So this series keeps `CCR_data` clearly larger than `IDR_image` using a
practical relative-gap rule.

### Position in the new 8-bin plan

E53 corresponds to the third bucket:

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

The third wave (`E51-E58`) is designed under the common constraint:

- `CCR_data > IDR_image`
- relative gap `>= 20%`

## Why E53 exists

E53 is the data-dominant counterpart of the balanced `E3X` series.

It helps answer a more specific question:

1. keep the same 8-bin `NCCR_total` structure,
2. make traditional data communication clearly larger than image communication,
3. compare algorithm behavior bin by bin.

## Property Design

`b53.properties` is derived from the corresponding `E3X` profile, but shifted
so that:

- traditional data communication becomes larger,
- image communication becomes smaller,
- total `NCCR_total` stays in the same bucket,
- and `CCR_data` remains at least 20% larger than `IDR_image` under the
  analysis rule.

### Verified snapshot

With the current `b53.properties` and `random_seed=2503`, the project produced:

- `CCR_data = 0.2478`
- `IDR_image = 0.1810`
- `NCCR_total = 0.4288`
- `relative gap = 31.16%`

This means the current tuned profile falls into the intended target region:

- `0.32 < 0.4288 <= 0.56`
- `CCR_data > IDR_image`
- `relative gap = 31.16% >= 20%`


## Usage

### Normal run

```bash
python3 experiments/e53/run_experiment.py
```

### Dry run

```bash
E53_DRY_RUN=1 python3 experiments/e53/run_experiment.py
```

### Fewer seeds

```bash
E53_NUM_SEEDS=10 python3 experiments/e53/run_experiment.py
```

### Analyze one run

```bash
python3 experiments/e53/analyze_results.py run_YYYYMMDD_HHMMSS_150_100
```

## Important Counting Rule

E53 follows the same counting logic as the earlier fixed-scenario experiments:

1. `run_experiment.py` executes all selected seeds and stores all raw results.
2. `analyze_results.py` re-parses each run log.
3. Only runs that actually satisfy the B53 condition are counted in the final
   summary.

So even if some seeds drift outside the intended target region, they are still
kept in the raw outputs, but ignored by the final statistics.

## Outputs

Each run folder contains:

- `grid_e53_results.csv`
- `run_manifest.json`
- `b53_properties_snapshot.properties`
- `logs/run_seed_<seed>.log`

The analysis script produces:

- `grid_e53_summary.csv`
- `e53_seed_metrics_with_b53_flag.csv`
- `e53_nheft_loss_seeds_by_scenario.json`
- `e53_summary_table.png`
- `e53_robust_table.png`
- `e53_makespan_mean_comparison.png`
- `e53_makespan_boxplot.png`
- `e53_gain_histogram.png`
