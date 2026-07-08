# E51: Fixed B51 Scenario in the First NCCR Bin

## Purpose

E51 is the first experiment in the new 8-bin `NCCR_total` study.

This experiment focuses on the following target region:

- `0.10 < NCCR_total <= 0.18`
- `CCR_data > IDR_image`
- `|CCR_data - IDR_image| / ((CCR_data + IDR_image)/2) >= 20%`

The role of E51 is to observe the behavior of `HEFT`, `DHEFT`, and `NHEFT`
in the lowest region of the new `0.1 < NCCR < 10` design,
while making traditional data communication explicitly larger than image communication.

## Design

### Scenario type

E51 is **not** a parameter sweep experiment.

It is a **fixed-scenario repeated-seed experiment**:

- one tuned property set: `b51.properties`
- many random seeds
- final statistics only on seeds that actually satisfy the B51 condition

### B51 condition

The analysis-side condition is:

- `0.10 < NCCR_total <= 0.18`
- `CCR_data > IDR_image`
- `|CCR_data - IDR_image| / ((CCR_data + IDR_image)/2) >= 20%`

So this series keeps `CCR_data` clearly larger than `IDR_image` using a
practical relative-gap rule.

### Position in the new 8-bin plan

E51 corresponds to the first bucket:

- `(0.10, 0.18]`

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

## Why E51 exists

E51 is the data-dominant counterpart of the balanced `E3X` series.

It helps answer a more specific question:

1. keep the same 8-bin `NCCR_total` structure,
2. make traditional data communication clearly larger than image communication,
3. compare algorithm behavior bin by bin.

## Property Design

`b51.properties` is derived from the corresponding `E3X` profile, but shifted
so that:

- traditional data communication becomes larger,
- image communication becomes smaller,
- total `NCCR_total` stays in the same bucket,
- and `CCR_data` remains at least 20% larger than `IDR_image` under the
  analysis rule.

### Verified snapshot

With the current `b51.properties` and `random_seed=2503`, the project produced:

- `CCR_data = 0.0943`
- `IDR_image = 0.0723`
- `NCCR_total = 0.1666`
- `relative gap = 26.41%`

This means the current tuned profile falls into the intended target region:

- `0.10 < 0.1666 <= 0.18`
- `CCR_data > IDR_image`
- `relative gap = 26.41% >= 20%`


## Usage

### Normal run

```bash
python3 experiments/e51/run_experiment.py
```

### Dry run

```bash
E51_DRY_RUN=1 python3 experiments/e51/run_experiment.py
```

### Fewer seeds

```bash
E51_NUM_SEEDS=10 python3 experiments/e51/run_experiment.py
```

### Analyze one run

```bash
python3 experiments/e51/analyze_results.py run_YYYYMMDD_HHMMSS_150_100
```

## Important Counting Rule

E51 follows the same counting logic as the earlier fixed-scenario experiments:

1. `run_experiment.py` executes all selected seeds and stores all raw results.
2. `analyze_results.py` re-parses each run log.
3. Only runs that actually satisfy the B51 condition are counted in the final
   summary.

So even if some seeds drift outside the intended target region, they are still
kept in the raw outputs, but ignored by the final statistics.

## Outputs

Each run folder contains:

- `grid_e51_results.csv`
- `run_manifest.json`
- `b51_properties_snapshot.properties`
- `logs/run_seed_<seed>.log`

The analysis script produces:

- `grid_e51_summary.csv`
- `e51_seed_metrics_with_b51_flag.csv`
- `e51_nheft_loss_seeds_by_scenario.json`
- `e51_summary_table.png`
- `e51_robust_table.png`
- `e51_makespan_mean_comparison.png`
- `e51_makespan_boxplot.png`
- `e51_gain_histogram.png`
