# E21X: First NCCR Bucket, Balanced CCR/IDR / NHEFT DRT-Only Gate

This experiment is the first concrete `x`-family scenario under the current
`four/e2` series plan.

Under the latest plan in
[`../QUICK_LOOKUP.md`](/Users/tengfeisun/Developer/2026/with-downloadscheduling2022-t/experiments/four/QUICK_LOOKUP.md),
the `e2` series means:

- `DRT` only

So `e21x` means:

- first `NCCR` bucket: `0.10 < NCCR_total <= 0.18`
- balanced communication composition: `CCR_data ~= IDR_image`
- gate rule: `DRT` only

It keeps the same paired comparison logic as the other `four/` runs:

- baseline `NHEFT`
- DRT-only-gated `NHEFT` (`GHEFT` in the Java output)
- plus `HEFT` and `DHEFT` as reference algorithms

The difference is that this folder fixes the communication-condition target to:

```text
0.10 < NCCR_total <= 0.18 AND CCR_data ~= IDR_image
```

The parameter values are reused from:

```text
experiments/three/e31
```

so that the `four/` gate study can be tested under the same tuned first-bucket
scenario family already used in `three/`.

## Compared Variants

| Variant | `nheft_vcpu_eft_tolerance` | `comp gate` | `drt gate` | `irt gate` | Meaning |
|---|---:|---:|---:|---:|---|
| `baseline` | `0.0` | `0` | `0` | `0` | Current NHEFT behavior. The scheduler selects the globally minimum-EFT candidate. |
| `drt_only` | `0.0` | `0` | `1` | `0` | NHEFT opens a new vCPU only when earlier EFT and earlier DRT both hold against the best already-used vCPU. |

## Base Configuration

By default, the runner reads the local scenario file:

```text
experiments/four/e21x/b21x.properties
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
first-bucket scenario, while the same seed is reused for both baseline and
DRT-only-gated NHEFT.

## Run

From the simulator repository root:

Smoke test:

```bash
E21X_NUM_SEEDS=1 E21X_LIMIT_RUNS=1   experiments/.venv/bin/python   experiments/four/e21x/run_experiment.py
```

Full default experiment:

```bash
experiments/.venv/bin/python   experiments/four/e21x/run_experiment.py
```

Dry run:

```bash
E21X_NUM_SEEDS=1 E21X_LIMIT_RUNS=1 E21X_DRY_RUN=1   experiments/.venv/bin/python   experiments/four/e21x/run_experiment.py
```

Useful overrides:

```bash
E21X_NUM_SEEDS=20
E21X_MASTER_SEED=151
E21X_TIMEOUT=180
E21X_BASE_PROPERTIES=/absolute/path/to/file.properties
```

If the process is stopped with `Ctrl+C`, completed CSV rows remain available.

## Analyze

Analyze the latest result folder:

```bash
experiments/.venv/bin/python   experiments/four/e21x/analyze_results.py
```

Analyze a specific result folder:

```bash
experiments/.venv/bin/python   experiments/four/e21x/analyze_results.py   run_YYYYMMDD_HHMMSS_151_1000
```

The analyzer reads the existing CSV only. It does not rerun Java.

The analysis uses the following scenario rule:

```text
0.10 < NCCR_total <= 0.18 AND |CCR_data - IDR_image| <= 0.02
```

Additional useful analysis override:

```bash
E21X_ABS_TOL=0.02   Balanced CCR/IDR absolute tolerance during analysis.
```

As in `e1`, incomplete seeds are excluded from all paired summaries.
A seed is used only when both expected NHEFT variants are present.

## Output

Each execution creates:

```text
run_YYYYMMDD_HHMMSS_<master-seed>_<number-of-seeds>/
```

The directory contains:

- `e21x_results.csv`: long-format raw metrics, one row per `seed x variant`
- `logs/seed_<seed>.log`: complete Java output for the paired single-JVM run
- `run_manifest.json`: seeds, variants, progress, and execution status
- `base_properties_snapshot.properties`: local scenario-property snapshot
- `java_runtime_snapshot.properties`: Java runtime snapshot

The analysis script writes:

- `e21x_seed_variant_paired_metrics.csv`
- `e21x_variant_summary.csv`
- `e21x_reference_summary.csv`
- `e21x_complete_seed_report.csv`
- `makespan_vcpu_combined_line_bar.png`
- `delta_vs_baseline_nheft.png`
- `variant_summary_table.png`

## Interpretation

This folder is useful when we want to answer the following more specific
question:

- under this **one fixed first-bucket communication condition**, does the
  DRT-only gate reduce vCPU usage while keeping more makespan
  benefit than DHEFT?

In other words, this folder is the first scenario-level test for the current
`e2` series definition.
