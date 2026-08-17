# E27Y: Seventh NCCR Bucket, Image-Dominant / NHEFT Computation + DRT Gate

This experiment is the **scenario-conditioned extension of `four/e2`**.

It keeps the same paired comparison logic as `e2`:

- baseline `NHEFT`
- comp+DRT-gated `NHEFT` (`GHEFT` in the Java output)
- plus `HEFT` and `DHEFT` as reference algorithms

The difference is that this folder fixes the communication-condition target to:

```text
3.16 < NCCR_total <= 5.62 AND CCR_data < IDR_image
```

The parameter values are reused from:

```text
experiments/three/e47
```

so that the `four/` gate study can be tested under the same tuned seventh-bucket
scenario family already used in `three/`.

## Compared Variants

| Variant | `nheft_vcpu_eft_tolerance` | `comp gate` | `drt gate` | `irt gate` | Meaning |
|---|---:|---:|---:|---:|---|
| `baseline` | `0.0` | `0` | `0` | `0` | Current NHEFT behavior. The scheduler selects the globally minimum-EFT candidate. |
| `comp_drt` | `0.0` | `1` | `1` | `0` | NHEFT opens a new vCPU only when earlier EFT, shorter computation time, and earlier DRT all hold against the best already-used vCPU. |

## Base Configuration

By default, the runner reads the local scenario file:

```text
experiments/four/e27y/b27y.properties
```

The Java runtime is still resolved from:

```text
experiments/java_runtime.properties
```

For each Java invocation, the runner overrides only:

- `random_seed`
- `nheft_vcpu_eft_tolerance`
- `nheft_vcpu_open_requires_comp_advantage`
- `nheft_vcpu_open_requires_drt_advantage`
- `nheft_vcpu_open_requires_irt_advantage`
- `nheft_mode2_*` second-mode properties

This means the communication-condition parameters remain fixed to the local
seventh-bucket scenario, while the same seed is reused for both baseline and
comp+DRT-gated NHEFT.

## Run

From the simulator repository root:

Smoke test:

```bash
E27Y_NUM_SEEDS=1 E27Y_LIMIT_RUNS=1   experiments/.venv/bin/python   experiments/four/e27y/run_experiment.py
```

Full default experiment:

```bash
experiments/.venv/bin/python   experiments/four/e27y/run_experiment.py
```

Dry run:

```bash
E27Y_NUM_SEEDS=1 E27Y_LIMIT_RUNS=1 E27Y_DRY_RUN=1   experiments/.venv/bin/python   experiments/four/e27y/run_experiment.py
```

Useful overrides:

```bash
E27Y_NUM_SEEDS=20
E27Y_MASTER_SEED=151
E27Y_TIMEOUT=180
E27Y_BASE_PROPERTIES=/absolute/path/to/file.properties
```

If the process is stopped with `Ctrl+C`, completed CSV rows remain available.

## Analyze

Analyze the latest result folder:

```bash
experiments/.venv/bin/python   experiments/four/e27y/analyze_results.py
```

Analyze a specific result folder:

```bash
experiments/.venv/bin/python   experiments/four/e27y/analyze_results.py   run_YYYYMMDD_HHMMSS_151_1000
```

The analyzer reads the existing CSV only. It does not rerun Java.

The analysis uses the following scenario rule:

```text
3.16 < NCCR_total <= 5.62 AND CCR_data < IDR_image AND relative CCR/IDR gap >= 20%
```

Additional useful analysis override:

```bash
E27Y_MIN_REL_GAP_PCT=20   Minimum relative CCR/IDR gap during analysis.
```

As in `e1`, incomplete seeds are excluded from all paired summaries.
A seed is used only when both expected NHEFT variants are present.

## Output

Each execution creates:

```text
run_YYYYMMDD_HHMMSS_<master-seed>_<number-of-seeds>/
```

The directory contains:

- `e27y_results.csv`: long-format raw metrics, one row per `seed x variant`
- `logs/seed_<seed>.log`: complete Java output for the paired single-JVM run
- `run_manifest.json`: seeds, variants, progress, and execution status
- `base_properties_snapshot.properties`: local scenario-property snapshot
- `java_runtime_snapshot.properties`: Java runtime snapshot

The analysis script writes:

- `e27y_seed_variant_paired_metrics.csv`
- `e27y_variant_summary.csv`
- `e27y_reference_summary.csv`
- `e27y_complete_seed_report.csv`
- `makespan_vcpu_combined_line_bar.png`
- `delta_vs_baseline_nheft.png`
- `variant_summary_table.png`

## Interpretation

This folder is useful when we want to answer the following more specific
question:

- under this **one fixed seventh-bucket communication condition**, does the
  comp+DRT gate reduce vCPU usage while keeping more makespan
  benefit than DHEFT?

In other words, `e1` asks the general gate question, while `e27y` asks the
same question under one communication family already tuned in `three/`.
