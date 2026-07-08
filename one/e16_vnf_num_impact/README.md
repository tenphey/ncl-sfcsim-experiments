# E16: VNF Quantity / Scale Impact

E16 tests whether increasing the total number of VNFs makes NHEFT's slot-based
bandwidth scheduling more visible.

## Design Goal

Keep the SFC count fixed and scale the per-SFC VNF count so that the total VNF
count grows in a controlled way.

This isolates the effect of workload scale from the effects of image size,
type diversity, or multiple-SFC concurrency.

## Variables

- `effective_total_vnf_num ∈ {80, 160, 240, 320}`

## Fixed Settings

- `multiple_sfc_num = 4`
- `vnf_type_min = 1`
- `vnf_type_max = 12`
- `vnf_image_size_min = 6000`
- `vnf_image_size_max = 12000`
- `repository_bw = 200`
- `datacenter_externalbw_min = 500`
- `datacenter_externalbw_max = 1000`
- `host_bw_min = 1000`
- `host_bw_max = 2000`

For each level:

- `per_sfc_vnf_num = effective_total_vnf_num / multiple_sfc_num`
- `multiple_sfc_vnf_num_min = multiple_sfc_vnf_num_max = per_sfc_vnf_num`

## Why This Is Useful

- If VNF count is too small, NHEFT's bandwidth-slot advantage may be hard to see.
- As scale increases, more downloads overlap and critical-path effects can grow.
- This lets you test whether NHEFT becomes more visible at larger problem sizes.

## Run

```bash
python3 experiments/e16_vnf_num_impact/run_experiment.py
```

Dry run:

```bash
E16_DRY_RUN=1 python3 experiments/e16_vnf_num_impact/run_experiment.py
```

## Analyze

```bash
python3 experiments/e16_vnf_num_impact/analyze_results.py run_<master_seed>_<timestamp>
```

Outputs:

- `grid_e16_results.csv`
- `grid_e16_summary.csv`
- `e16_gain_trend.png`
- `e16_makespan_comparison.png`
