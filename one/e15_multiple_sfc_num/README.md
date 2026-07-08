# E15: Download Concurrency Opportunity Impact

E15 is designed to show NHEFT's core strength with minimal complexity.

## Design Goal

Keep task scale controlled, and change only the chance of concurrent downloads.

NHEFT's slot-based model should benefit when concurrent image downloads become more frequent.

## Variables

- `multiple_sfc_num ∈ {1, 2, 4, 8}`

## Fixed Settings

- `effective_total_vnf_num = 320` (constant)
- `vnf_type_min = 1`, `vnf_type_max = 12`
- `per_sfc_vnf_num = effective_total_vnf_num / multiple_sfc_num`
- `vnf_image_size_min = 6000`, `vnf_image_size_max = 12000`
- `repository_bw = 200`

This keeps overall scale stable while increasing multi-source/multi-branch download opportunity.

## Why This Should Highlight NHEFT

- DHEFT uses queue-like download modeling.
- NHEFT uses slot-based dynamic bandwidth occupancy.
- As `multiple_sfc_num` increases, more tasks are ready in overlapping windows.
- Under heavy image download pressure, slot-based scheduling should have clearer advantage.

## Run

```bash
python3 experiments/e15/run_experiment.py
```

Dry run:

```bash
E15_DRY_RUN=1 python3 experiments/e15/run_experiment.py
```

## Analyze

```bash
python3 experiments/e15/analyze_results.py run_<master_seed>_<timestamp>
```

Outputs:

- `grid_e15_results.csv`
- `grid_e15_summary.csv`
- `e15_gain_trend.png`
- `e15_makespan_comparison.png`
