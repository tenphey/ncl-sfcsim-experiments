# Four: Resource-Aware NHEFT Gate Experiments

This directory contains the fourth experiment line for the
`with-downloadscheduling` simulator study.

The purpose of `four/` is different from the earlier
[`three/`](/Users/tengfeisun/Developer/2026/with-downloadscheduling2022-t/experiments/three/README.md)
condition-based comparison.

In `three/`, the main question is:

- under which communication conditions does `NHEFT` outperform `DHEFT`?

In `four/`, the main question is:

- can `NHEFT` reduce its vCPU usage without losing too much of its makespan
  advantage?

More specifically, this directory studies **resource-aware opening rules** for
new vCPUs in `NHEFT`.

For paper-facing readers, `four/` should be understood as a **follow-up line**
to `three/`:

- `three/` asks when bandwidth-aware image-transfer modeling improves makespan
- `four/` asks how much of that makespan benefit can be retained while
  suppressing unnecessary vCPU opening

## Core Idea

The original `NHEFT` always selects the candidate vCPU with the minimum EFT
(`Earliest Finish Time`) for the current task.

The experiments in `four/` keep that baseline as the reference, and then add
extra opening gates for unused vCPUs.

The intuition is:

- a new vCPU should not be opened only because it is temporarily free
- it should be opened only when it provides a meaningful scheduling advantage

The candidate opening gates currently studied are:

- `CompT` gate:
  the new vCPU must also have a shorter computation time than the best
  already-used vCPU
- `DRT` gate:
  the new vCPU must also have an earlier `DRT` (`Data Ready Time`)
- `IRT` gate:
  the new vCPU must also have an earlier `IRT` (`Image Ready Time`)

In all gated variants, the new vCPU must still satisfy:

- `EFT_new < EFT_used`

The optional gates above are then added on top of that basic EFT condition.

From the viewpoint of gate logic, the current study should be divided into two
families:

- **strict gate family**:
  `EFT_new < EFT_used` is mandatory, and every enabled extra gate must also be
  satisfied
- **relaxed gate family**:
  `EFT_new < EFT_used` is still mandatory, but among the enabled extra gates,
  satisfying at least one of them is enough to open a new vCPU

At the moment, the repository contains two different layers of work:

- the **historical gate-screening layer** in `e0-e4`
- the **current scenario-matrix plan** defined by `QUICK_LOOKUP.md`

These two layers should not be mixed.
The old `e0-e4` directories are still useful as screening evidence, but the
current experiment arrangement is the one listed in `QUICK_LOOKUP.md`.

## Current Status

The current **planned scenario matrix** is defined by
[`QUICK_LOOKUP.md`](/Users/tengfeisun/Developer/2026/with-downloadscheduling2022-t/experiments/four/QUICK_LOOKUP.md).

That file should be treated as the authoritative experiment map for:

- series meaning
- `x / y / z` family meaning
- bucket-to-directory mapping

At the time of writing, the planned series are:

- `e1`: `CompT` only
- `e2`: `DRT` only
- `e3`: `IRT` only
- `e4`: `DRT OR IRT`
- `e5`: `CompT OR DRT`
- `e6`: `CompT OR IRT`
- `e7`: `CompT OR DRT OR IRT`

The gate strictness order is:

- `e4 > e2/e3 > e1 > e5/e6 > e7`

This ordering describes only the **opening-rule strictness**.
It does **not** imply that makespan or vCPU usage will change monotonically in
exactly that order for every dataset.

### Historical Exploratory Sweeps

The directories below are **earlier screening runs** that were created before
the current `e1-e7` scenario plan was finalized:

- [`e0_nheft_vcpu_tolerance/`](/Users/tengfeisun/Developer/2026/with-downloadscheduling2022-t/experiments/four/e0_nheft_vcpu_tolerance)
  - sweeps `nheft_vcpu_eft_tolerance` from `0.0` to `1.0`
  - used to study the direct makespan-vs-vCPU trade-off of the tolerance idea
- [`e1_nheft_comp_advantage/`](/Users/tengfeisun/Developer/2026/with-downloadscheduling2022-t/experiments/four/e1_nheft_comp_advantage)
  - baseline `NHEFT` vs `CompT` gate only
- [`e2_nheft_comp_drt_gates/`](/Users/tengfeisun/Developer/2026/with-downloadscheduling2022-t/experiments/four/e2_nheft_comp_drt_gates)
  - baseline `NHEFT` vs strict `CompT + DRT`
- [`e3_nheft_comp_irt_gates/`](/Users/tengfeisun/Developer/2026/with-downloadscheduling2022-t/experiments/four/e3_nheft_comp_irt_gates)
  - baseline `NHEFT` vs strict `CompT + IRT`
- [`e4_nheft_all_gates/`](/Users/tengfeisun/Developer/2026/with-downloadscheduling2022-t/experiments/four/e4_nheft_all_gates)
  - baseline `NHEFT` vs exploratory all-gates `CompT + DRT + IRT`

These directories remain useful as **historical screening evidence**, but they
should not be confused with the current `e1-e7` series plan used by the
scenario-conditioned expansion.

The `e0` group is an **orthogonal tolerance sweep**.
It is useful for the early makespan-vs-vCPU trade-off discussion, but it is
not part of the later gate-family matrix.

Each implemented group compares:

- `HEFT`
- `DHEFT`
- baseline `NHEFT`
- one gated `NHEFT` variant

using the same seed and the same generated input for paired comparison.

Detailed run instructions and analysis outputs are documented in each
subdirectory README.

## Interpreting the Current Exploratory Sweeps

The current historical `e0-e4` groups should be read as **screening
experiments**.

Their role is to answer questions such as:

- which gate combination is too strict?
- which gate combination still preserves a meaningful makespan advantage?
- which gate combination is worth expanding into a full communication-condition
  matrix?

So, if this repository is cited in a paper, it is important to distinguish:

- **historical exploratory gate sweeps** in `e0-e4`
- **current structured condition matrix** described below

These are related, but they are not the same phase of the study.

## Gate Family Interpretation

All `four/` gate families share the same hard baseline rule:

- `EFT_new < EFT_used`

The difference between the series is only **which extra advantage conditions**
are required on top of that EFT improvement.

Under the current plan:

- `e1`: require `CompT`
- `e2`: require `DRT`
- `e3`: require `IRT`
- `e4`: require `DRT OR IRT`
- `e5`: require `CompT OR DRT`
- `e6`: require `CompT OR IRT`
- `e7`: require `CompT OR DRT OR IRT`

## What Is Compared in One Seed?

For one random seed, the experiment framework keeps the generated workflow and
platform input fixed and then compares multiple schedulers or scheduler
variants under that same input.

Depending on the experiment group, the compared outputs include:

- `HEFT`: reference scheduler without image-aware modeling
- `DHEFT`: image-aware scheduler with reuse and coarse transfer estimation
- baseline `NHEFT`: bandwidth-aware scheduler without extra vCPU-opening gate
- one modified `NHEFT` gate variant

This paired-seed design is important because the raw workflow instance is not
regenerated between variants of the same seed.

Therefore, observed differences are intended to reflect the scheduler decision
logic itself, not a changed workload.

## Minimal Reproduction Workflow

If a reader wants to reproduce the current `four/` experiments, the simplest
path is:

1. build the Java simulator from the repository root
2. prepare the Python virtual environment under `experiments/.venv`
3. configure `experiments/java_runtime.properties`
4. run one historical sweep in `e0-e4`, or one scenario directory such as
   `e21x`
5. analyze the produced `run_*` directory

The shared setup steps are documented in:

- [`../README.md`](/Users/tengfeisun/Developer/2026/with-downloadscheduling2022-t/experiments/README.md)

For example, a typical exploratory comparison starts from:

- [`e1_nheft_comp_advantage/README.md`](/Users/tengfeisun/Developer/2026/with-downloadscheduling2022-t/experiments/four/e1_nheft_comp_advantage/README.md)

That README shows both:

- how to execute the paired runs
- how to summarize makespan and vCPU behavior from the saved CSV data

## Planned 24-Scenario Matrix

The current plan for `four/` is to expand the resource-aware gate experiments
into the same communication-condition structure used in
[`three/`](/Users/tengfeisun/Developer/2026/with-downloadscheduling2022-t/experiments/three/README.md).

That planned matrix is:

- `8` `NCCR_total` buckets
- `3` communication families
- `8 x 3 = 24` scenarios per gate design

The reserved naming plan below follows the current `QUICK_LOOKUP` convention.
If this README and `QUICK_LOOKUP.md` ever disagree, `QUICK_LOOKUP.md` wins.

### `NCCR_total` Buckets

1. `(0.10, 0.18]`
2. `(0.18, 0.32]`
3. `(0.32, 0.56]`
4. `(0.56, 1.00]`
5. `(1.00, 1.78]`
6. `(1.78, 3.16]`
7. `(3.16, 5.62]`
8. `(5.62, 10.00]`

### Families

- `x`: `CCR_data ~= IDR_image`
- `y`: `CCR_data < IDR_image`
- `z`: `CCR_data > IDR_image`

## Reserved Naming Plan for the Scenario Matrix

The following names are **reserved directory mappings** for the
condition-based expansion of `four/`.

They describe the intended naming scheme.
For the current implementation status, `QUICK_LOOKUP.md` remains the source of
truth.

### `e11-e18`: `CompT` Only

- `e11x`, `e11y`, `e11z` -> `(0.10, 0.18]`
- `e12x`, `e12y`, `e12z` -> `(0.18, 0.32]`
- `e13x`, `e13y`, `e13z` -> `(0.32, 0.56]`
- `e14x`, `e14y`, `e14z` -> `(0.56, 1.00]`
- `e15x`, `e15y`, `e15z` -> `(1.00, 1.78]`
- `e16x`, `e16y`, `e16z` -> `(1.78, 3.16]`
- `e17x`, `e17y`, `e17z` -> `(3.16, 5.62]`
- `e18x`, `e18y`, `e18z` -> `(5.62, 10.00]`

### `e21-e28`: `DRT` Only

- `e21x`, `e21y`, `e21z` -> `(0.10, 0.18]`
- `e22x`, `e22y`, `e22z` -> `(0.18, 0.32]`
- `e23x`, `e23y`, `e23z` -> `(0.32, 0.56]`
- `e24x`, `e24y`, `e24z` -> `(0.56, 1.00]`
- `e25x`, `e25y`, `e25z` -> `(1.00, 1.78]`
- `e26x`, `e26y`, `e26z` -> `(1.78, 3.16]`
- `e27x`, `e27y`, `e27z` -> `(3.16, 5.62]`
- `e28x`, `e28y`, `e28z` -> `(5.62, 10.00]`

### `e31-e38`: `IRT` Only

- `e31x`, `e31y`, `e31z` -> `(0.10, 0.18]`
- `e32x`, `e32y`, `e32z` -> `(0.18, 0.32]`
- `e33x`, `e33y`, `e33z` -> `(0.32, 0.56]`
- `e34x`, `e34y`, `e34z` -> `(0.56, 1.00]`
- `e35x`, `e35y`, `e35z` -> `(1.00, 1.78]`
- `e36x`, `e36y`, `e36z` -> `(1.78, 3.16]`
- `e37x`, `e37y`, `e37z` -> `(3.16, 5.62]`
- `e38x`, `e38y`, `e38z` -> `(5.62, 10.00]`

### `e41-e48`: `DRT OR IRT`

- `e41x`, `e41y`, `e41z` -> `(0.10, 0.18]`
- `e42x`, `e42y`, `e42z` -> `(0.18, 0.32]`
- `e43x`, `e43y`, `e43z` -> `(0.32, 0.56]`
- `e44x`, `e44y`, `e44z` -> `(0.56, 1.00]`
- `e45x`, `e45y`, `e45z` -> `(1.00, 1.78]`
- `e46x`, `e46y`, `e46z` -> `(1.78, 3.16]`
- `e47x`, `e47y`, `e47z` -> `(3.16, 5.62]`
- `e48x`, `e48y`, `e48z` -> `(5.62, 10.00]`

### `e51-e58`: `CompT OR DRT`

- `e51x`, `e51y`, `e51z` -> `(0.10, 0.18]`
- `e52x`, `e52y`, `e52z` -> `(0.18, 0.32]`
- `e53x`, `e53y`, `e53z` -> `(0.32, 0.56]`
- `e54x`, `e54y`, `e54z` -> `(0.56, 1.00]`
- `e55x`, `e55y`, `e55z` -> `(1.00, 1.78]`
- `e56x`, `e56y`, `e56z` -> `(1.78, 3.16]`
- `e57x`, `e57y`, `e57z` -> `(3.16, 5.62]`
- `e58x`, `e58y`, `e58z` -> `(5.62, 10.00]`

### `e61-e68`: `CompT OR IRT`

- `e61x`, `e61y`, `e61z` -> `(0.10, 0.18]`
- `e62x`, `e62y`, `e62z` -> `(0.18, 0.32]`
- `e63x`, `e63y`, `e63z` -> `(0.32, 0.56]`
- `e64x`, `e64y`, `e64z` -> `(0.56, 1.00]`
- `e65x`, `e65y`, `e65z` -> `(1.00, 1.78]`
- `e66x`, `e66y`, `e66z` -> `(1.78, 3.16]`
- `e67x`, `e67y`, `e67z` -> `(3.16, 5.62]`
- `e68x`, `e68y`, `e68z` -> `(5.62, 10.00]`

### `e71-e78`: `CompT OR DRT OR IRT`

- `e71x`, `e71y`, `e71z` -> `(0.10, 0.18]`
- `e72x`, `e72y`, `e72z` -> `(0.18, 0.32]`
- `e73x`, `e73y`, `e73z` -> `(0.32, 0.56]`
- `e74x`, `e74y`, `e74z` -> `(0.56, 1.00]`
- `e75x`, `e75y`, `e75z` -> `(1.00, 1.78]`
- `e76x`, `e76y`, `e76z` -> `(1.78, 3.16]`
- `e77x`, `e77y`, `e77z` -> `(3.16, 5.62]`
- `e78x`, `e78y`, `e78z` -> `(5.62, 10.00]`

## Recommended Reading Order

For new readers, the easiest order is:

1. [`../README.md`](/Users/tengfeisun/Developer/2026/with-downloadscheduling2022-t/experiments/README.md)
2. [`e0_nheft_vcpu_tolerance/README.md`](/Users/tengfeisun/Developer/2026/with-downloadscheduling2022-t/experiments/four/e0_nheft_vcpu_tolerance/README.md)
3. [`e1_nheft_comp_advantage/README.md`](/Users/tengfeisun/Developer/2026/with-downloadscheduling2022-t/experiments/four/e1_nheft_comp_advantage/README.md)
4. [`e2_nheft_comp_drt_gates/README.md`](/Users/tengfeisun/Developer/2026/with-downloadscheduling2022-t/experiments/four/e2_nheft_comp_drt_gates/README.md)
5. [`e3_nheft_comp_irt_gates/README.md`](/Users/tengfeisun/Developer/2026/with-downloadscheduling2022-t/experiments/four/e3_nheft_comp_irt_gates/README.md)
6. [`e4_nheft_all_gates/README.md`](/Users/tengfeisun/Developer/2026/with-downloadscheduling2022-t/experiments/four/e4_nheft_all_gates/README.md)

That order follows the historical research progression:

- tolerance idea
- computation-only gate
- communication-aware gates
- strict all-gate setting
- future relaxed-gate extensions

It should not be interpreted as the current `e1-e7` naming plan.

## Result Artifacts

Each implemented experiment group creates a timestamped `run_*` directory.

Although file names differ slightly by group, the saved artifacts follow the
same general pattern:

- raw CSV rows for every `seed x variant`
- per-run Java logs
- a manifest file recording execution progress and settings
- snapshots of the base properties and Java runtime configuration
- one or more `analysis_*` directories containing summary CSV files and figures

This means the experiment pipeline is intentionally split into two stages:

1. `run_experiment.py` generates raw paired data
2. `analyze_results.py` reads only the saved data and produces summaries

That separation is useful for long experiments, because:

- interrupted runs still leave reusable partial raw data
- analysis can be rerun without rerunning the Java simulator
- figure generation stays reproducible from the saved CSV outputs

## Notes for Citation and Reproducibility

If this repository is referenced in a paper, the following distinction should
be made explicit:

- `e0-e4` are implemented gate-comparison sweeps using a common base property
  profile
- `e11+` naming describes the planned communication-condition matrix for future
  expansion

In other words:

- the current exploratory results already exist in this repository
- the larger matrix naming scheme is documented here so that later experiment
  groups remain systematic and reproducible

When citing this directory in a paper, it is usually best to state explicitly
whether the cited evidence comes from:

- the currently implemented exploratory groups `e0-e4`, or
- the future reserved naming plan `e11+`

That distinction helps readers avoid assuming that every reserved name already
has a completed dataset behind it.
