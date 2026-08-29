# Experiments/Five

This directory contains a fresh 24-scenario data-generation set for the
comparison of the three download-aware schedulers used in the current study.

## Design

- 8 NCCR buckets: `(0.10, 0.18]` through `(5.62, 10.00]`
- 3 communication compositions per bucket: `x` balanced, `y` image-dominant, `z` data-dominant
- 500 shared random seeds for every scenario
- One Java invocation per seed
- Algorithms recorded together: DHEFT, NHEFT, and IRT-only-gated GHEFT

The balanced condition uses a relative CCR/IDR gap of at most 10% during later
analysis. The image-dominant and data-dominant conditions keep their directional
20% minimum gap. Raw generation does not filter rows; each run stores the
communication indicators so that filtering can be checked and reproduced later.

## Run

Run one scenario from the repository root:

```bash
experiments/.venv/bin/python experiments/five/e01x/run_experiment.py
```

Run all 24 scenarios sequentially:

```bash
experiments/.venv/bin/python experiments/five/run_all.py
```

For a smoke run without Java, use `--dry-run` or set `FIVE_LIMIT_RUNS`:

```bash
experiments/.venv/bin/python experiments/five/run_all.py --limit-runs 1 --dry-run
```

The shared seed list is stored in `seeds_500.json`. Each scenario creates a
directory named `run_<timestamp>_151_500`, containing its CSV, logs, property
snapshot, Java-runtime snapshot, and `run_manifest.json`.

The Java runtime is read from `experiments/java_runtime.properties`; the Java
project root therefore remains configurable without changing these scripts.
