# E12: VNF Type Diversity Impact

This experiment varies `vnf_type_max` while keeping all other parameters the same as `base.properties`.

## Design

### Variables
- `vnf_type_max ∈ {4, 8, 12, 20}`

### Fixed
- All other parameters inherit directly from `base.properties`

### Seeds
- 100 per type level by default
- Total: 4 levels × 100 = 400 runs

## Expected Pattern

This run is designed to isolate how the number of VNF types affects scheduling behavior and image reuse opportunities.

## Outputs
- `grid_e12_results.csv` (raw data)
- `grid_e12_summary.csv` (aggregated statistics)
- `run_manifest.json` (experiment metadata)
- `base_properties_snapshot.properties` (configuration snapshot)
- `e12_makespan_comparison.png` (grouped bar chart)

## Analysis

After running the experiment, generate the chart with:

```bash
python3 analyze_results.py <run_folder>
```

Example:

```bash
python3 analyze_results.py run_20260527_123000
```

## Rationale

Changing `vnf_type_max` alters the diversity of task types in the generated SFCs, which can change image reuse density and therefore influence scheduling outcomes.

## Key Insight

E12 now isolates **task-type diversity** while leaving all other settings to `base.properties`, so the resulting comparison focuses on the effect of `vnf_type_max` alone.

