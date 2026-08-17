# E0: NHEFT vCPU EFT-Tolerance Sweep

This experiment generates paired data for studying whether NHEFT can reduce
its vCPU usage while preserving makespan performance.

## Comparison

Every random seed is executed with the following tolerance values:

```text
0.0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0
```

- `tolerance=0.0` is the original NHEFT behavior and always selects the
  globally minimum-EFT candidate.
- `tolerance>0.0` may select an already-used vCPU when its EFT is within the
  configured relative tolerance of the global minimum.
- HEFT and DHEFT are recorded as additional reference algorithms.

The tolerance applies to each local task-placement decision. It is not a bound
on the final makespan difference.

## Base Configuration

By default, the runner reads:

```text
<project_root>/nheft.properties
```

`project_root` and the Java runtime are read from:

```text
experiments/java_runtime.properties
```

For each Java invocation, the runner overrides only:

- `random_seed`
- `nheft_vcpu_eft_tolerance`

All tolerance variants of one seed therefore use identical generated inputs.

## Run

The commands below assume the current directory is the simulator repository
root.

Small smoke test:

```bash
E0_NUM_SEEDS=1 E0_LIMIT_RUNS=2 \
  experiments/.venv/bin/python \
  experiments/four/e0_nheft_vcpu_tolerance/run_experiment.py
```

Full default experiment, consisting of `500 x 11 = 5500` Java runs:

```bash
experiments/.venv/bin/python \
  experiments/four/e0_nheft_vcpu_tolerance/run_experiment.py
```

Dry run:

```bash
E0_NUM_SEEDS=1 E0_LIMIT_RUNS=2 E0_DRY_RUN=1 \
  experiments/.venv/bin/python \
  experiments/four/e0_nheft_vcpu_tolerance/run_experiment.py
```

If the process is stopped with `Ctrl+C`, completed CSV rows remain available.

## Analyze

Analyze the latest result folder:

```bash
experiments/.venv/bin/python \
  experiments/four/e0_nheft_vcpu_tolerance/analyze_results.py
```

Analyze a specific result folder:

```bash
experiments/.venv/bin/python \
  experiments/four/e0_nheft_vcpu_tolerance/analyze_results.py \
  run_20260810_151839_151_1
```

The analyzer reads existing CSV data only. It does not rerun the simulator.
For each seed, every tolerance variant is compared with the same seed at
`tolerance=0.0`, which is treated as the original NHEFT baseline.
If a run was stopped in the middle of a seed, the incomplete seed is excluded
from all averages and plots. A seed is used only when it has all observed
tolerance values in the result CSV.

## Output

Each execution creates:

```text
run_YYYYMMDD_HHMMSS_<master-seed>_<number-of-seeds>/
```

The directory contains:

- `e0_tolerance_results.csv`: long-format raw metrics, one row per
  `seed x tolerance`
- `logs/tolerance_*/seed_*.log`: complete Java output for every invocation
- `run_manifest.json`: seeds, tolerance grid, progress, and execution status
- `nheft_base_snapshot.properties`: unchanged base-property snapshot
- `java_runtime_snapshot.properties`: Java runtime snapshot

Generated `run_*` and `analysis_*` directories are local experiment artifacts
and are ignored by Git.

The analysis script writes the following files under
`<result_folder>/analysis_<timestamp>/`:

- `e0_tolerance_summary.csv`: one summary row per tolerance value
- `e0_seed_tolerance_paired_metrics.csv`: per-seed paired metrics versus
  `tolerance=0.0`
- `e0_reference_summary.csv`: HEFT, DHEFT, and original NHEFT reference means
- `e0_complete_seed_report.csv`: complete/incomplete seed report
- `makespan_by_tolerance.png`
- `vcpu_by_tolerance.png`
- `relative_tradeoff_vs_original.png`
- `makespan_vcpu_tradeoff.png`
- `makespan_vcpu_combined_line_bar.png`
- `tolerance_summary_table.png`
