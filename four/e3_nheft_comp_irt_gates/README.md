# E3: NHEFT IRT-Only Gates

This experiment studies whether NHEFT can reduce vCPU usage by opening a new
vCPU only when the candidate has earlier EFT and simultaneously satisfies the
computation-time and IRT advantage gates against the best already-used vCPU.

## Comparison

Every random seed is executed with two NHEFT settings:

| Variant | `nheft_vcpu_eft_tolerance` | `comp gate` | `drt gate` | `irt gate` | Meaning |
|---|---:|---:|---:|---:|---|
| `baseline` | `0.0` | `0` | `0` | `0` | Current NHEFT behavior. The scheduler selects the globally minimum-EFT candidate. |
| `irt_only` | `0.0` | `1` | `0` | `1` | NHEFT opens a new vCPU only when earlier EFT, shorter computation time, and earlier IRT all hold against the best already-used vCPU. |

HEFT and DHEFT are also recorded from every Java invocation as reference
algorithms.

This experiment keeps `nheft_vcpu_eft_tolerance=0.0` on purpose. The only
controlled change is whether the IRT-only opening gates are enabled together.

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
- `nheft_vcpu_open_requires_comp_advantage`
- `nheft_vcpu_open_requires_drt_advantage`
- `nheft_vcpu_open_requires_irt_advantage`

Both variants of one seed therefore use identical generated inputs.

## Run

The commands below assume the current directory is the simulator repository
root.

Small smoke test:

```bash
E3_NUM_SEEDS=1 E3_LIMIT_RUNS=2 \
  experiments/.venv/bin/python \
  experiments/four/e3_nheft_irt_only_gates/run_experiment.py
```

Full default experiment, consisting of `1000 x 2 = 2000` Java runs:

```bash
experiments/.venv/bin/python \
  experiments/four/e3_nheft_irt_only_gates/run_experiment.py
```

Dry run:

```bash
E3_NUM_SEEDS=1 E3_LIMIT_RUNS=2 E3_DRY_RUN=1 \
  experiments/.venv/bin/python \
  experiments/four/e3_nheft_irt_only_gates/run_experiment.py
```

Useful overrides:

```bash
E3_NUM_SEEDS=20
E3_MASTER_SEED=151
E3_TIMEOUT=180
E3_BASE_PROPERTIES=/absolute/path/to/nheft.properties
E3_VARIANTS=baseline,irt_only
```

If the process is stopped with `Ctrl+C`, completed CSV rows remain available.

## Analyze

Analyze the latest result folder:

```bash
experiments/.venv/bin/python \
  experiments/four/e3_nheft_irt_only_gates/analyze_results.py
```

Analyze a specific result folder:

```bash
experiments/.venv/bin/python \
  experiments/four/e3_nheft_irt_only_gates/analyze_results.py \
  run_20260810_170000_151_50
```

The analyzer reads existing CSV data only. It does not rerun the simulator.
For each seed, the `irt_only` variant is compared with the same seed under
`baseline`, which is treated as the current NHEFT behavior.

If a run was stopped in the middle of a seed, the incomplete seed is excluded
from all averages and plots. A seed is used only when it has all expected E3
variants.

## Output

Each execution creates:

```text
run_YYYYMMDD_HHMMSS_<master-seed>_<number-of-seeds>/
```

The directory contains:

- `e3_irt_only_results.csv`: long-format raw metrics, one row per
  `seed x variant`
- `logs/<variant>/seed_*.log`: complete Java output for every invocation
- `run_manifest.json`: seeds, variants, progress, and execution status
- `nheft_base_snapshot.properties`: unchanged base-property snapshot
- `java_runtime_snapshot.properties`: Java runtime snapshot

Generated `run_*` and `analysis_*` directories are local experiment artifacts
and are ignored by Git.

The analysis script writes the following files under
`<result_folder>/analysis_<timestamp>/`:

- `e3_seed_variant_paired_metrics.csv`: per-seed paired metrics versus baseline
  NHEFT
- `e3_variant_summary.csv`: one summary row per NHEFT variant
- `e3_reference_summary.csv`: HEFT, DHEFT, and baseline NHEFT reference means
- `e3_complete_seed_report.csv`: complete/incomplete seed report
- `makespan_vcpu_combined_line_bar.png`: mixed makespan-line and vCPU-bar plot
- `delta_vs_baseline_nheft.png`: makespan cost and vCPU reduction versus
  baseline NHEFT
- `variant_summary_table.png`: compact summary table image
