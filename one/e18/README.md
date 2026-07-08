# E18: High Repository BW x SFC Fragmentation Trade-off

## Purpose

This experiment is a refined follow-up to E17.

E15 showed that `multiple_sfc_num` is useful, but not simply monotonic:

- larger `multiple_sfc_num` can create more overlapping downloads,
- but it also shortens each child SFC (`per_sfc_vnf_num` becomes smaller).

Therefore E18 does two things:

1. remove the lower-`repository_bw` weak-signal region,
2. reinterpret the second axis as a fragmentation trade-off, not a pure
   "more is always better" concurrency axis.

## Design

### Sweep variables

- `repository_bw ∈ {600, 900}`
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

So total workload stays fixed, while fragmentation level changes.

## Why E18 exists

The recent experiments suggested:

- E11: `repository_bw` is the strongest direct lever.
- E15: `multiple_sfc_num` matters, but not monotonically.
- E16: total VNF count alone is not the right way to amplify NHEFT.

So E18 narrows the search to the region most likely to make NHEFT's advantage
look clear while keeping the interpretation honest.

## Usage

### Normal run

```bash
python3 experiments/e18/run_experiment.py
```

### Dry run

```bash
E18_DRY_RUN=1 python3 experiments/e18/run_experiment.py
```

### Fewer seeds

```bash
E18_NUM_SEEDS=10 python3 experiments/e18/run_experiment.py
```

### Analyze one run

```bash
python3 experiments/e18/analyze_results.py run_YYYYMMDD_HHMMSS_150_100
```

## Outputs

Each run folder contains:

- `grid_e18_results.csv`
- `run_manifest.json`
- `base_properties_snapshot.properties`
- per-seed raw logs

The analysis script produces:

- `grid_e18_summary.csv`
- `e18_summary_table.png`
- `e18_gain_heatmap.png`
- `e18_winrate_heatmap.png`
- `e18_fragmentation_trend.png`
- `e18_repo_bw_trend.png`

## Expected pattern

Compared with E17, E18 should:

- suppress the weak low-bandwidth cases,
- make the repository-bandwidth effect cleaner,
- reveal whether the best region is at low, medium, or high fragmentation,
  instead of assuming monotonic growth with `multiple_sfc_num`.
