# E12Y: Second NCCR Bucket, Image-Dominant / NHEFT Computation-Advantage Gate

This experiment is the **scenario-conditioned extension of `four/e1`**.

It keeps the same paired comparison logic as `e1`:

- baseline `NHEFT`
- computation-gated `NHEFT` (`GHEFT` in the Java output)
- plus `HEFT` and `DHEFT` as reference algorithms

The difference is that this folder fixes the communication-condition target to:

```text
0.18 < NCCR_total <= 0.32 AND CCR_data < IDR_image
```

The parameter values are reused from:

```text
experiments/three/e42
```

so that the `four/` gate study can be tested under the same tuned second-bucket
scenario family already used in `three/`.

## Compared Variants

| Variant | `nheft_vcpu_eft_tolerance` | `nheft_vcpu_open_requires_comp_advantage` | Meaning |
|---|---:|---:|---|
| `baseline` | `0.0` | `0` | Current NHEFT behavior. The scheduler selects the globally minimum-EFT candidate. |
| `comp_advantage` | `0.0` | `1` | Open a new vCPU only when the new vCPU has both earlier EFT and shorter computation time than the best already-used vCPU. |

## Base Configuration

By default, the runner reads the local scenario file:

```text
experiments/four/e12y/b12y.properties
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
second-bucket scenario, while the same seed is reused for both baseline and
comp-gated NHEFT.

## Run

From the simulator repository root:

Smoke test:

```bash
E12Y_NUM_SEEDS=1 E12Y_LIMIT_RUNS=1   experiments/.venv/bin/python   experiments/four/e12y/run_experiment.py
```

Full default experiment:

```bash
experiments/.venv/bin/python   experiments/four/e12y/run_experiment.py
```

Dry run:

```bash
E12Y_NUM_SEEDS=1 E12Y_LIMIT_RUNS=1 E12Y_DRY_RUN=1   experiments/.venv/bin/python   experiments/four/e12y/run_experiment.py
```

Useful overrides:

```bash
E12Y_NUM_SEEDS=20
E12Y_MASTER_SEED=151
E12Y_TIMEOUT=180
E12Y_BASE_PROPERTIES=/absolute/path/to/file.properties
```

If the process is stopped with `Ctrl+C`, completed CSV rows remain available.

## Analyze

Analyze the latest result folder:

```bash
experiments/.venv/bin/python   experiments/four/e12y/analyze_results.py
```

Analyze a specific result folder:

```bash
experiments/.venv/bin/python   experiments/four/e12y/analyze_results.py   run_YYYYMMDD_HHMMSS_151_1000
```

The analyzer reads the existing CSV only. It does not rerun Java.

The analysis uses the following scenario rule:

```text
0.18 < NCCR_total <= 0.32 AND CCR_data < IDR_image AND relative CCR/IDR gap >= 20%
```

Additional useful analysis override:

```bash
E12Y_MIN_REL_GAP_PCT=20   Minimum relative CCR/IDR gap during analysis.
```

As in `e1`, incomplete seeds are excluded from all paired summaries.
A seed is used only when both expected NHEFT variants are present.

## Output

Each execution creates:

```text
run_YYYYMMDD_HHMMSS_<master-seed>_<number-of-seeds>/
```

The directory contains:

- `e12y_results.csv`: long-format raw metrics, one row per `seed x variant`
- `logs/seed_<seed>.log`: complete Java output for the paired single-JVM run
- `run_manifest.json`: seeds, variants, progress, and execution status
- `base_properties_snapshot.properties`: local scenario-property snapshot
- `java_runtime_snapshot.properties`: Java runtime snapshot

The analysis script writes:

- `e12y_seed_variant_paired_metrics.csv`
- `e12y_variant_summary.csv`
- `e12y_reference_summary.csv`
- `e12y_complete_seed_report.csv`
- `makespan_vcpu_combined_line_bar.png`
- `delta_vs_baseline_nheft.png`
- `variant_summary_table.png`

## Interpretation

This folder is useful when we want to answer the following more specific
question:

- under this **one fixed second-bucket communication condition**, does the
  computation-advantage gate reduce vCPU usage while keeping more makespan
  benefit than DHEFT?

In other words, `e1` asks the general gate question, while `e12y` asks the
same question under one communication family already tuned in `three/`.
