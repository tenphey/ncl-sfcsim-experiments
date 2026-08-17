# E08X: Shared Baseline Scenario Run

This folder runs the **common baseline algorithms only**:

- `HEFT`
- `DHEFT`
- `NHEFT`

It does **not** run `GHEFT`.

This directory is intended to provide the shared baseline side for the gated
scenario-conditioned experiments in `experiments/four`.

## Base Configuration

The runner reads the local shared scenario file:

```text
experiments/four/e08x/b08x.properties
```

During execution, the runner forces the baseline algorithm switches:

```text
run_heft = 1
run_dheft = 1
run_nheft = 1
run_nheft_mode2 = 0
nheft_mode2_enabled = 0
nheft_vcpu_eft_tolerance = 0.0
nheft_vcpu_open_requires_comp_advantage = 0
nheft_vcpu_open_requires_drt_advantage = 0
nheft_vcpu_open_requires_irt_advantage = 0
nheft_vcpu_open_gate_logic = all
```

## Run

From the simulator repository root:

Smoke test:

```bash
E08X_NUM_SEEDS=1 E08X_LIMIT_RUNS=1   experiments/.venv/bin/python   experiments/four/e08x/run_experiment.py
```

Full default run:

```bash
experiments/.venv/bin/python   experiments/four/e08x/run_experiment.py
```

Dry run:

```bash
E08X_NUM_SEEDS=1 E08X_LIMIT_RUNS=1 E08X_DRY_RUN=1   experiments/.venv/bin/python   experiments/four/e08x/run_experiment.py
```

Optional override:

```bash
E08X_BASE_PROPERTIES=/absolute/path/to/file.properties
```

## Output

Each run creates:

```text
run_YYYYMMDD_HHMMSS_<master-seed>_<number-of-seeds>/
```

containing:

- `e08x_results.csv`
- `logs/seed_<seed>.log`
- `run_manifest.json`
- `base_properties_snapshot.properties`
- `java_runtime_snapshot.properties`

## Important Note

This baseline run is designed to be merged later with the corresponding gated
experiment result, for example:

- `e08x` as the common baseline side
- `e1/e2/e3/e4` scenario-conditioned GHEFT side for the same bucket/composition
