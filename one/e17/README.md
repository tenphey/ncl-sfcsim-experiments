# E17: Repository BW x Concurrent Download Opportunity

## Purpose

This experiment is designed from the latest E11-E16 findings.

The goal is to make `NHEFT`'s advantage over `DHEFT` easier to observe by
combining the two strongest drivers:

1. high enough `repository_bw`, and
2. more concurrent download opportunity via `multiple_sfc_num`.

In other words, E17 asks:

> When repository bandwidth is sufficient, does increasing the number of
> concurrent SFCs make NHEFT's slot-based download scheduling more effective
> than DHEFT's queue-style download model?

## Design

### Sweep variables

- `repository_bw ∈ {300, 600, 900}`
- `multiple_sfc_num ∈ {1, 2, 4, 8}`

### Fixed parameters

- `effective_total_vnf_num = 320`
- `vnf_type_min = 1`
- `vnf_type_max = 20`
- `vnf_image_size_min = 5000`
- `vnf_image_size_max = 7000`
- `datacenter_externalbw_min = 500`
- `datacenter_externalbw_max = 1000`
- `host_bw_min = 1000`
- `host_bw_max = 2000`

### Derived rule

For each `multiple_sfc_num`, the script computes:

- `per_sfc_vnf_num = effective_total_vnf_num / multiple_sfc_num`

So the total workload size stays fixed, while only the concurrent structure
changes.

## Why this experiment

Recent experiments suggested:

- E11: `repository_bw` is the strongest direct lever.
- E12: reduced reuse / more cold-start pressure helps NHEFT.
- E13: image size helps only up to a moderate-heavy range.
- E16: simply increasing total VNF count is not enough.

Therefore, E17 focuses on:

- enough bandwidth to make slot parallelism usable,
- enough concurrent SFC structure to create overlapping downloads,
- enough image/type pressure to avoid a reuse-dominated trivial case.

## Usage

### Normal run

```bash
python3 experiments/e17/run_experiment.py
```

### Dry run

```bash
E17_DRY_RUN=1 python3 experiments/e17/run_experiment.py
```

### Fewer seeds

```bash
E17_NUM_SEEDS=10 python3 experiments/e17/run_experiment.py
```

### Analyze one run

```bash
python3 experiments/e17/analyze_results.py run_YYYYMMDD_HHMMSS_150_100
```

## Outputs

Each run folder contains:

- `grid_e17_results.csv`
- `run_manifest.json`
- `base_properties_snapshot.properties`
- per-seed raw logs

The analysis script produces:

- `grid_e17_summary.csv`
- `e17_gain_heatmap.png`
- `e17_winrate_heatmap.png`
- `e17_repo_bw_trend.png`

## Expected pattern

If the hypothesis is correct:

- gain should improve as `repository_bw` increases,
- gain should improve as `multiple_sfc_num` increases,
- the strongest region should appear in the high-`repository_bw`,
  high-`multiple_sfc_num` corner.
