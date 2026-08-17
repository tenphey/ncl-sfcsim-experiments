# E1: NHEFT Computation-Advantage Gate

This experiment studies whether NHEFT can reduce vCPU usage by opening a new
vCPU only when the new vCPU is also computationally better than the best
already-used vCPU.

## Comparison

Every random seed is executed with two NHEFT settings:

| Variant | `nheft_vcpu_eft_tolerance` | `nheft_vcpu_open_requires_comp_advantage` | Meaning |
|---|---:|---:|---|
| `baseline` | `0.0` | `0` | Current NHEFT behavior. The scheduler selects the globally minimum-EFT candidate. |
| `comp_advantage` | `0.0` | `1` | NHEFT opens a new vCPU only when the new vCPU has both earlier EFT and shorter computation time than the best already-used vCPU. |

HEFT and DHEFT are also recorded from every Java invocation as reference
algorithms.

This experiment keeps `nheft_vcpu_eft_tolerance=0.0` on purpose.  The only
controlled change is whether the computation-advantage gate is enabled.

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

Both variants of one seed therefore use identical generated inputs.

## Run

The commands below assume the current directory is the simulator repository
root.

Small smoke test:

```bash
E1_NUM_SEEDS=1 E1_LIMIT_RUNS=2 \
  experiments/.venv/bin/python \
  experiments/four/e1_nheft_comp_advantage/run_experiment.py
```

Full default experiment, consisting of `50 x 2 = 100` Java runs:

```bash
experiments/.venv/bin/python \
  experiments/four/e1_nheft_comp_advantage/run_experiment.py
```

Dry run:

```bash
E1_NUM_SEEDS=1 E1_LIMIT_RUNS=2 E1_DRY_RUN=1 \
  experiments/.venv/bin/python \
  experiments/four/e1_nheft_comp_advantage/run_experiment.py
```

Useful overrides:

```bash
E1_NUM_SEEDS=20
E1_MASTER_SEED=151
E1_TIMEOUT=180
E1_BASE_PROPERTIES=/absolute/path/to/nheft.properties
E1_VARIANTS=baseline,comp_advantage
```

If the process is stopped with `Ctrl+C`, completed CSV rows remain available.

## Analyze

Analyze the latest result folder:

```bash
experiments/.venv/bin/python \
  experiments/four/e1_nheft_comp_advantage/analyze_results.py
```

Analyze a specific result folder:

```bash
experiments/.venv/bin/python \
  experiments/four/e1_nheft_comp_advantage/analyze_results.py \
  run_20260810_170000_151_50
```

The analyzer reads existing CSV data only. It does not rerun the simulator.
For each seed, the `comp_advantage` variant is compared with the same seed under
`baseline`, which is treated as the current NHEFT behavior.

If a run was stopped in the middle of a seed, the incomplete seed is excluded
from all averages and plots. A seed is used only when it has all expected E1
variants.

## Output

Each execution creates:

```text
run_YYYYMMDD_HHMMSS_<master-seed>_<number-of-seeds>/
```

The directory contains:

- `e1_comp_advantage_results.csv`: long-format raw metrics, one row per
  `seed x variant`
- `logs/<variant>/seed_*.log`: complete Java output for every invocation
- `run_manifest.json`: seeds, variants, progress, and execution status
- `nheft_base_snapshot.properties`: unchanged base-property snapshot
- `java_runtime_snapshot.properties`: Java runtime snapshot

Generated `run_*` and `analysis_*` directories are local experiment artifacts
and are ignored by Git.

The analysis script writes the following files under
`<result_folder>/analysis_<timestamp>/`:

- `e1_variant_summary.csv`: one summary row per NHEFT variant
- `e1_seed_variant_paired_metrics.csv`: per-seed paired metrics versus baseline
  NHEFT
- `e1_reference_summary.csv`: HEFT, DHEFT, and baseline NHEFT reference means
- `e1_complete_seed_report.csv`: complete/incomplete seed report
- `makespan_vcpu_combined_line_bar.png`: mixed makespan-line and vCPU-bar plot
- `delta_vs_baseline_nheft.png`: makespan cost and vCPU reduction versus
  baseline NHEFT
- `variant_summary_table.png`: compact summary table image
