# E42X: Standalone GHEFT / DRT-Or-IRT Gate

This folder now runs **only GHEFT**.

It no longer recomputes shared baseline algorithms.
The shared communication scenario is read from:

```text
experiments/four/e02x/b02x.properties
```

That common scenario file should also be used by the shared baseline run
for the same bucket/composition.

## Gate Setting

This series enables the `DRT or IRT` opening rule for new-vCPU selection.

```text
tolerance = 0.0
comp gate = 0
drt gate  = 1
irt gate  = 1
gate logic = any
```

In other words, this folder is intended to measure the **GHEFT-only side**
of the same communication scenario, while the baseline `HEFT/DHEFT/NHEFT`
side should come from the corresponding common scenario run.

## Run

From the simulator repository root:

Smoke test:

```bash
E42X_NUM_SEEDS=1 E42X_LIMIT_RUNS=1   experiments/.venv/bin/python   experiments/four/e42x/run_experiment.py
```

Full default run:

```bash
experiments/.venv/bin/python   experiments/four/e42x/run_experiment.py
```

Dry run:

```bash
E42X_NUM_SEEDS=1 E42X_LIMIT_RUNS=1 E42X_DRY_RUN=1   experiments/.venv/bin/python   experiments/four/e42x/run_experiment.py
```

Optional override:

```bash
E42X_BASE_PROPERTIES=/absolute/path/to/file.properties
```

## Output

Each run creates:

```text
run_YYYYMMDD_HHMMSS_<master-seed>_<number-of-seeds>/
```

containing:

- `e42x_results.csv`
- `logs/seed_<seed>.log`
- `run_manifest.json`
- `base_properties_snapshot.properties`
- `java_runtime_snapshot.properties`

## Important Note

The existing `analyze_results.py` in this folder still belongs to the older
paired-baseline workflow.

After this refactor, the intended comparison is:

- shared baseline scenario run
- plus this standalone `GHEFT` scenario run

merged later at the analysis stage.
