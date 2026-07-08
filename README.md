# Experiments

This directory contains automated experiment scripts for the
[`with-downloadscheduling`](https://github.com/ncl-teu/ncl_sfcsim/tree/with-downloadscheduling)
branch of `ncl_sfcsim`.

The simulator itself is implemented in Java under the repository root. The
files in `experiments/` provide:

- batch execution scripts
- per-experiment result filtering
- aggregated analysis scripts
- single-seed replay and DAG export utilities

## Before Running

The commands below assume that the current working directory is the repository
root.

### 1. Build the Java simulator

```bash
ant build
```

The Python scripts call the compiled Java main class
`net.gripps.cloud.nfv.main.NFVSchedulingTest`, so `classes/` must exist before
running the experiments.

### 2. Install Python dependencies

```bash
python3 -m venv experiments/.venv
source experiments/.venv/bin/activate
pip install -r experiments/requirements.txt
```

### 3. Configure the Java runtime path

Copy the template:

```bash
cp experiments/java_runtime.properties.example experiments/java_runtime.properties
```

Then edit `experiments/java_runtime.properties` if needed.

If `experiments/` is located directly under the simulator repository root, the
default template value `project_root=..` is already correct.

## Recommended Starting Point

For new users, start with:

- [`three/`](/Users/tengfeisun/Developer/2026/with-downloadscheduling2022-t/experiments/three)

This directory contains the most structured condition-based experiments
(`e31-e58`) and is the best entry point for reproducing the current
communication-condition comparisons.

## Quick Reproduction Example

The following example runs a small `e31` batch and analyzes the result.

### Run a small batch

```bash
E31_NUM_SEEDS=5 python3 experiments/three/e31/run_experiment.py
```

At the end of the run, the script prints a line like:

```text
RESULT_DIR=/.../experiments/three/e31/run_YYYYMMDD_HHMMSS_151_500
```

Use the printed path directly. Do not infer the directory name from
`E31_NUM_SEEDS`, because the current run-directory suffix follows the script
template and may still contain the default seed-count marker.

### Analyze that batch

Use the printed `RESULT_DIR`, or pass only its basename:

```bash
python3 experiments/three/e31/analyze_results.py run_YYYYMMDD_HHMMSS_151_500
```

The analysis script reads the per-seed logs, filters valid samples, and writes
summary CSV/PNG files into the same `run_*` directory.

## Directory Layout

The experiment sets are organized into three groups:

1. [`three/`](/Users/tengfeisun/Developer/2026/with-downloadscheduling2022-t/experiments/three)
2. [`two/`](/Users/tengfeisun/Developer/2026/with-downloadscheduling2022-t/experiments/two)
3. [`one/`](/Users/tengfeisun/Developer/2026/with-downloadscheduling2022-t/experiments/one)

### `three/`

`three/` contains the `e31-e58` family.

These experiments are defined by:

- `NCCR_total` bucket
- relation between `CCR_data` and `IDR_image`

The families are:

- `e31-e38`: `CCR_data ~= IDR_image`
- `e41-e48`: `CCR_data < IDR_image`
- `e51-e58`: `CCR_data > IDR_image`

Main aggregation scripts:

- [`three/analyze_e3x.py`](/Users/tengfeisun/Developer/2026/with-downloadscheduling2022-t/experiments/three/analyze_e3x.py)
- [`three/analyze_e4x.py`](/Users/tengfeisun/Developer/2026/with-downloadscheduling2022-t/experiments/three/analyze_e4x.py)
- [`three/analyze_e5x.py`](/Users/tengfeisun/Developer/2026/with-downloadscheduling2022-t/experiments/three/analyze_e5x.py)
- [`three/analyze_e345x.py`](/Users/tengfeisun/Developer/2026/with-downloadscheduling2022-t/experiments/three/analyze_e345x.py)

See also:

- [`three/README.md`](/Users/tengfeisun/Developer/2026/with-downloadscheduling2022-t/experiments/three/README.md)

### `two/`

`two/` contains the earlier `e21-e29` condition-based experiments.

These experiments use three coarse `NCCR_total` regions:

- `0 < NCCR_total < 1`
- `1 < NCCR_total < 2`
- `NCCR_total > 2`

For each region, three `CCR_data / IDR_image` relations are tested:

- `CCR_data > IDR_image`
- `CCR_data ~= IDR_image`
- `CCR_data < IDR_image`

Main aggregation scripts:

- [`two/analyze_e21_e22_e23_latest.py`](/Users/tengfeisun/Developer/2026/with-downloadscheduling2022-t/experiments/two/analyze_e21_e22_e23_latest.py)
- [`two/analyze_e24_e25_e26_latest.py`](/Users/tengfeisun/Developer/2026/with-downloadscheduling2022-t/experiments/two/analyze_e24_e25_e26_latest.py)
- [`two/analyze_e27_e28_e29_latest.py`](/Users/tengfeisun/Developer/2026/with-downloadscheduling2022-t/experiments/two/analyze_e27_e28_e29_latest.py)

### `one/`

`one/` contains earlier parameter-sweep experiments.

Representative topics include:

- repository bandwidth
- VNF type diversity
- VNF image size
- number of SFCs
- total VNF count
- combined bandwidth and concurrency settings

## Shared Configuration

Java runtime settings for Python-driven experiments are stored in:

- [`java_runtime.properties`](/Users/tengfeisun/Developer/2026/with-downloadscheduling2022-t/experiments/java_runtime.properties)

An example template is available at:

- [`java_runtime.properties.example`](/Users/tengfeisun/Developer/2026/with-downloadscheduling2022-t/experiments/java_runtime.properties.example)

The `three/` run scripts read this shared file instead of embedding Java
runtime paths in each experiment script.

## Result Filtering

For condition-based experiments, the number of executed seeds and the number of
qualified samples are not always the same.

The typical flow is:

1. `run_experiment.py` executes all sampled seeds
2. `analyze_results.py` parses per-seed logs
3. only seeds satisfying the target condition are included in final statistics

This is expected behavior for `two/` and `three/`.

## Single-Seed Replay

To replay and inspect a specific seed with a selected property file, use:

- [`analyze_single_seed_with_dag.py`](/Users/tengfeisun/Developer/2026/with-downloadscheduling2022-t/experiments/analyze_single_seed_with_dag.py)

Example:

```bash
python3 experiments/analyze_single_seed_with_dag.py 1769 experiments/three/e48/b48.properties
```

This utility is used to:

- replay a specific seed
- regenerate scheduler outputs under the selected properties
- export DAG metadata
- inspect cases where `NHEFT` wins or loses against `DHEFT`

## Useful Entry Points

- [`three/README.md`](/Users/tengfeisun/Developer/2026/with-downloadscheduling2022-t/experiments/three/README.md)
- [`three/e31/`](/Users/tengfeisun/Developer/2026/with-downloadscheduling2022-t/experiments/three/e31)
- [`three/analyze_e345x.py`](/Users/tengfeisun/Developer/2026/with-downloadscheduling2022-t/experiments/three/analyze_e345x.py)
- [`analyze_single_seed_with_dag.py`](/Users/tengfeisun/Developer/2026/with-downloadscheduling2022-t/experiments/analyze_single_seed_with_dag.py)
