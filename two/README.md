# Two: Coarse Condition-Based Experiments

This directory contains the earlier condition-based experiments in the
`with-downloadscheduling` branch.

The `two/` group is the stage between simple parameter sweeps and the more
structured `three/` experiment family.

## Scope

The experiments in this directory are based on:

- coarse `NCCR_total` regions
- the relation between `CCR_data` and `IDR_image`

The three `NCCR_total` regions are:

- `0 < NCCR_total < 1`
- `1 < NCCR_total < 2`
- `NCCR_total > 2`

For each region, three `CCR_data / IDR_image` relations are tested:

- `CCR_data > IDR_image`
- `CCR_data ~= IDR_image`
- `CCR_data < IDR_image`

This produces the following experiment matrix:

- `e21-e23` for `0 < NCCR_total < 1`
- `e24-e26` for `1 < NCCR_total < 2`
- `e27-e29` for `NCCR_total > 2`

## Directory Mapping

- [`e21`](/Users/tengfeisun/Developer/2026/with-downloadscheduling2022-t/experiments/two/e21): `0 < NCCR_total < 1` and `CCR_data > IDR_image`
- [`e22`](/Users/tengfeisun/Developer/2026/with-downloadscheduling2022-t/experiments/two/e22): `0 < NCCR_total < 1` and `CCR_data ~= IDR_image`
- [`e23`](/Users/tengfeisun/Developer/2026/with-downloadscheduling2022-t/experiments/two/e23): `0 < NCCR_total < 1` and `CCR_data < IDR_image`
- [`e24`](/Users/tengfeisun/Developer/2026/with-downloadscheduling2022-t/experiments/two/e24): `1 < NCCR_total < 2` and `CCR_data > IDR_image`
- [`e25`](/Users/tengfeisun/Developer/2026/with-downloadscheduling2022-t/experiments/two/e25): `1 < NCCR_total < 2` and `CCR_data ~= IDR_image`
- [`e26`](/Users/tengfeisun/Developer/2026/with-downloadscheduling2022-t/experiments/two/e26): `1 < NCCR_total < 2` and `CCR_data < IDR_image`
- [`e27`](/Users/tengfeisun/Developer/2026/with-downloadscheduling2022-t/experiments/two/e27): `NCCR_total > 2` and `CCR_data > IDR_image`
- [`e28`](/Users/tengfeisun/Developer/2026/with-downloadscheduling2022-t/experiments/two/e28): `NCCR_total > 2` and `CCR_data ~= IDR_image`
- [`e29`](/Users/tengfeisun/Developer/2026/with-downloadscheduling2022-t/experiments/two/e29): `NCCR_total > 2` and `CCR_data < IDR_image`

## Common Structure

Each experiment directory typically contains:

- `run_experiment.py`
- `analyze_results.py`
- `bX.properties`
- timestamped `run_*` result directories after execution

Family-level aggregation scripts are located in this directory:

- [`analyze_e21_e22_e23_latest.py`](/Users/tengfeisun/Developer/2026/with-downloadscheduling2022-t/experiments/two/analyze_e21_e22_e23_latest.py)
- [`analyze_e24_e25_e26_latest.py`](/Users/tengfeisun/Developer/2026/with-downloadscheduling2022-t/experiments/two/analyze_e24_e25_e26_latest.py)
- [`analyze_e27_e28_e29_latest.py`](/Users/tengfeisun/Developer/2026/with-downloadscheduling2022-t/experiments/two/analyze_e27_e28_e29_latest.py)

These aggregation scripts read existing experiment outputs and summarize the
latest `run_*` directory of each experiment in the corresponding family.

## Current Runtime Configuration Note

At the moment, the `two/` run scripts do **not** read the shared
[`experiments/java_runtime.properties`](/Users/tengfeisun/Developer/2026/with-downloadscheduling2022-t/experiments/java_runtime.properties)
file.

Instead, they assume the standard repository layout:

- compiled classes under `classes/`
- library jars under `lib/`
- the repository root as the base for the Java classpath

For this reason, build the Java simulator first from the repository root:

```bash
ant build
```

## Quick Example

The commands below assume that the current working directory is the repository
root.

### Run a small `e21` batch

```bash
E21_NUM_SEEDS=5 python3 experiments/two/e21/run_experiment.py
```

### Analyze that batch

```bash
python3 experiments/two/e21/analyze_results.py run_YYYYMMDD_HHMMSS_150_100
```

### Aggregate the latest `e21-e23` results

```bash
python3 experiments/two/analyze_e21_e22_e23_latest.py
```

## Filtering Rule

These are target-condition experiments.

This means that:

1. `run_experiment.py` executes sampled seeds
2. `analyze_results.py` checks whether each seed actually satisfies the target condition
3. only qualified seeds are included in final summary statistics

Therefore, the number of executed seeds and the number of qualified samples may
be different.
