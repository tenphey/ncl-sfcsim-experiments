# One: Parameter-Sweep Experiments

This directory contains the earlier parameter-sweep experiments in the
`with-downloadscheduling` branch.

The purpose of this group is to vary low-level simulator parameters and observe
how they affect the relative behavior of `HEFT`, `DHEFT`, and `NHEFT`.

## Scope

The experiments in `one/` are organized as independent subdirectories.

Representative topics include:

- repository bandwidth
- VNF type diversity
- VNF image size
- number of SFCs
- total VNF count
- combined bandwidth and concurrency settings

Main subdirectories:

- [`e11_repository_bw`](/Users/tengfeisun/Developer/2026/with-downloadscheduling2022-t/experiments/one/e11_repository_bw)
- [`e12_vnf_type_max`](/Users/tengfeisun/Developer/2026/with-downloadscheduling2022-t/experiments/one/e12_vnf_type_max)
- [`e13_vnf_image_size`](/Users/tengfeisun/Developer/2026/with-downloadscheduling2022-t/experiments/one/e13_vnf_image_size)
- [`e14_vnf_type_max_times`](/Users/tengfeisun/Developer/2026/with-downloadscheduling2022-t/experiments/one/e14_vnf_type_max_times)
- [`e15_multiple_sfc_num`](/Users/tengfeisun/Developer/2026/with-downloadscheduling2022-t/experiments/one/e15_multiple_sfc_num)
- [`e16_vnf_num_impact`](/Users/tengfeisun/Developer/2026/with-downloadscheduling2022-t/experiments/one/e16_vnf_num_impact)
- [`e17`](/Users/tengfeisun/Developer/2026/with-downloadscheduling2022-t/experiments/one/e17)
- [`e18`](/Users/tengfeisun/Developer/2026/with-downloadscheduling2022-t/experiments/one/e18)

## Common Structure

Each experiment directory typically contains:

- `run_experiment.py`
- `analyze_results.py`
- a local `README.md`
- timestamped `run_*` output directories after execution

Most experiments in this group use:

- [`experiments/base.properties`](/Users/tengfeisun/Developer/2026/with-downloadscheduling2022-t/experiments/base.properties)

and then override selected parameters inside the Python run script.

## Current Runtime Configuration Note

At the moment, the `one/` run scripts do **not** read the shared
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

### Run a small `e11` batch

```bash
E11_NUM_SEEDS=5 python3 experiments/one/e11_repository_bw/run_experiment.py
```

### Analyze that batch

```bash
python3 experiments/one/e11_repository_bw/analyze_results.py run_YYYYMMDD_HHMMSS
```

Use the actual `run_*` directory printed or created by the script.

## Notes

- Each subdirectory has its own local README with experiment-specific details.
- Some experiments in this group sweep multiple grid points in a single run.
- Output files usually include raw CSV, summary CSV, and one or more plots.
- This group is best read together with the directory-level READMEs of the
  individual experiments.
