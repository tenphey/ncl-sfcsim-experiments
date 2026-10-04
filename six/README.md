# Experiments/Six

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
ant regression_tests
experiments/.venv/bin/python experiments/six/e01x/run_experiment.py
```

Run all 24 scenarios sequentially:

```bash
experiments/.venv/bin/python experiments/six/run_all.py
```

For a smoke run without Java, use `--dry-run` or set `FIVE_LIMIT_RUNS`:

```bash
experiments/.venv/bin/python experiments/six/run_all.py --limit-runs 1 --dry-run
```

The shared seed list is stored in `seeds_500.json`. Each scenario creates a
directory named `run_<timestamp>_151_500`, containing its CSV, logs, property
snapshot, Java-runtime snapshot, and `run_manifest.json`.

## Correctness And Provenance (2026-10-04)

The corrected simulator validates each schedule before publishing its metrics.
This runner requires the expected revision and all three validation-pass markers,
as well as finite positive makespans/resource counts. A failure preserves its log
and raw row, then stops the scenario rather than continuing a potentially invalid batch.

Every real run freezes the compiled classes and dependency JARs in its output
directory. The manifest records their hashes, the Java-source and runner hashes,
Git revision/diff hash, JDK version, and an effective-properties snapshot. Older
compiled classes must be rebuilt before running. The existing `FIVE_*` environment
variable names are retained for compatibility; scenario parameters and shared
seed generation are unchanged. Microseconds prevent run-directory collisions.

Only DHEFT, baseline NHEFT, and IRT-gated GHEFT are run here. The unrelated random
clustering algorithm is explicitly disabled. `time_sec` remains whole-process time,
not the computational cost of one scheduler. The network model remains logical
host-pair/DC-pair slots, not an aggregate endpoint-egress constraint.

Formal analysis uses the latest complete, versioned batch with the requested
seed count, and rejects mixed compiled versions/dependencies, mismatched seed
sequences, duplicate seeds or incomplete/invalid paired records. Completion means
all candidate seeds finished successfully; it does not mean all satisfy the
scenario filter. Filtering and per-seed gain statistics remain unchanged;
display-only adjustments are recorded below.

```sh
experiments/.venv/bin/python experiments/six/analyze_results.py
```

The analysis writes `analysis_provenance.json` with its exact input directories.
Use `--allow-legacy-runs` only to inspect historical complete runs without the
new provenance; it does not make old results valid for the corrected simulator.
The read-only `check_valid_counts.py` remains usable during an ongoing run.

The Java runtime is read from `experiments/java_runtime.properties`; the Java
project root therefore remains configurable without changing these scripts.

## Plot Adjustment (2026-10-04)

- For `e3xyz_mean_makespan_vcpu_overview-low` only, increase the makespan-axis
  maximum from 1.35 to 1.8 times the largest plotted makespan. The zero baseline
  is retained; the lines and labels move toward the middle without changing data.
- `OVERVIEW_MAKESPAN_Y_MAX_FACTORS` in `analyze_results.py` controls this override.
  All other overview figures retain the original 1.35 factor. The vCPU axis,
  bars, figure dimensions and per-point annotation offsets remain unchanged.
- Regenerate only this PNG/PDF in `analysis_20261004_175024_500` from its existing
  bucket summary. No experiment or statistical analysis is rerun. All other
  files in that analysis directory remain byte-identical.
- Verify all seven overview variants: data and annotation offsets are unchanged;
  only the target makespan-axis limits differ. Visually check the regenerated
  PNG; its PDF retains embedded TrueType fonts. Paper assets are not updated.
