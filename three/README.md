# Three: Condition-Based Experiments (`e31-e58`)

This directory contains the structured condition-based experiments used to
compare `HEFT`, `DHEFT`, and `NHEFT` under different communication settings.

Each experiment is defined by:

- an `NCCR_total` bucket
- a relation between `CCR_data` and `IDR_image`

## Experiment Matrix

### `NCCR_total` buckets

1. `(0.10, 0.18]`
2. `(0.18, 0.32]`
3. `(0.32, 0.56]`
4. `(0.56, 1.00]`
5. `(1.00, 1.78]`
6. `(1.78, 3.16]`
7. `(3.16, 5.62]`
8. `(5.62, 10.00]`

### Families

- `e31-e38`: `CCR_data ~= IDR_image`
- `e41-e48`: `CCR_data < IDR_image`
- `e51-e58`: `CCR_data > IDR_image`

## Directory Mapping

### `e31-e38`

- `e31` -> `(0.10, 0.18]`
- `e32` -> `(0.18, 0.32]`
- `e33` -> `(0.32, 0.56]`
- `e34` -> `(0.56, 1.00]`
- `e35` -> `(1.00, 1.78]`
- `e36` -> `(1.78, 3.16]`
- `e37` -> `(3.16, 5.62]`
- `e38` -> `(5.62, 10.00]`

### `e41-e48`

- `e41` -> `(0.10, 0.18]`
- `e42` -> `(0.18, 0.32]`
- `e43` -> `(0.32, 0.56]`
- `e44` -> `(0.56, 1.00]`
- `e45` -> `(1.00, 1.78]`
- `e46` -> `(1.78, 3.16]`
- `e47` -> `(3.16, 5.62]`
- `e48` -> `(5.62, 10.00]`

### `e51-e58`

- `e51` -> `(0.10, 0.18]`
- `e52` -> `(0.18, 0.32]`
- `e53` -> `(0.32, 0.56]`
- `e54` -> `(0.56, 1.00]`
- `e55` -> `(1.00, 1.78]`
- `e56` -> `(1.78, 3.16]`
- `e57` -> `(3.16, 5.62]`
- `e58` -> `(5.62, 10.00]`

## Per-Experiment Structure

Each experiment directory usually contains:

- `run_experiment.py`
- `analyze_results.py`
- `bXX.properties`
- `run_YYYYMMDD_.../` result directories

The common workflow is:

1. run a batch of seeds
2. analyze the generated `run_*` directory
3. optionally aggregate multiple experiments at the family level

## Running One Experiment

The commands below assume that the current working directory is the repository
root.

### Example: `e31`

Run a small batch:

```bash
E31_NUM_SEEDS=5 python3 experiments/three/e31/run_experiment.py
```

Dry run:

```bash
E31_DRY_RUN=1 python3 experiments/three/e31/run_experiment.py
```

After execution, the script prints:

```text
RESULT_DIR=/.../experiments/three/e31/run_YYYYMMDD_HHMMSS_151_500
```

Use the printed path directly. Do not infer the directory name from
`E31_NUM_SEEDS`, because the current run-directory suffix follows the script
template and may still contain the default seed-count marker.

Analyze that result:

```bash
python3 experiments/three/e31/analyze_results.py run_YYYYMMDD_HHMMSS_151_500
```

The argument may be either:

- the basename of the `run_*` directory
- the full path to the `run_*` directory

### Example: `e41`

```bash
E41_NUM_SEEDS=5 python3 experiments/three/e41/run_experiment.py
python3 experiments/three/e41/analyze_results.py run_YYYYMMDD_HHMMSS_151_500
```

### Example: `e51`

```bash
E51_NUM_SEEDS=5 python3 experiments/three/e51/run_experiment.py
python3 experiments/three/e51/analyze_results.py run_YYYYMMDD_HHMMSS_151_500
```

## Filtering Rule

These experiments are target-condition experiments.

This means that a batch run may execute many seeds, but only a subset of those
seeds will satisfy the intended condition after log parsing.

The standard rule is:

1. `run_experiment.py` executes all sampled seeds
2. `analyze_results.py` parses `CCR_data`, `IDR_image`, and `NCCR_total` from logs
3. only qualified seeds are included in final statistics

Therefore:

- the number of executed seeds is not always equal to the number of qualified samples
- final summary tables and plots are based on qualified samples only

## Family-Level Aggregation

Three family-level aggregation scripts are provided:

- [`analyze_e3x.py`](/Users/tengfeisun/Developer/2026/with-downloadscheduling2022-t/experiments/three/analyze_e3x.py): aggregates `e31-e38`
- [`analyze_e4x.py`](/Users/tengfeisun/Developer/2026/with-downloadscheduling2022-t/experiments/three/analyze_e4x.py): aggregates `e41-e48`
- [`analyze_e5x.py`](/Users/tengfeisun/Developer/2026/with-downloadscheduling2022-t/experiments/three/analyze_e5x.py): aggregates `e51-e58`

Combined aggregation across all three families is available at:

- [`analyze_e345x.py`](/Users/tengfeisun/Developer/2026/with-downloadscheduling2022-t/experiments/three/analyze_e345x.py)

Typical commands:

```bash
python3 experiments/three/analyze_e3x.py
python3 experiments/three/analyze_e4x.py
python3 experiments/three/analyze_e5x.py
python3 experiments/three/analyze_e345x.py
```

These scripts read existing experiment outputs. They do not rerun the Java
simulator.
