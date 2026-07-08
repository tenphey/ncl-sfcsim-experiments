# E13: VNF Image Size Impact — H2 Verification

This experiment varies only `vnf_image_size_min` and `vnf_image_size_max` while keeping all other parameters inherited from `base.properties` unchanged.

## Design

### Variables
- `vnf_image_size_min` / `vnf_image_size_max`
- Image-size ranges used in E13:
  - `500–2000` MB
  - `2000–4000` MB
  - `4000–8000` MB
  - `8000–10000` MB

These ranges are chosen as a monotonic progression from low to high image-size pressure and are intended to increase download pressure gradually.

### Fixed
- All other settings are inherited directly from `base.properties`
- `random_seed` changes per run only for replication

### Seeds
- 100 per image-size level by default
- Total: 4 levels × 100 = 400 runs

## Expected

As image size increases:
1. download time becomes longer,
2. image-download / execution overlap becomes more likely,
3. NHEFT's dynamic scheduling advantage should become more visible.

So the expected pattern is:
- `makespan` increases for both algorithms,
- `NHEFT` keeps a better makespan than `DHEFT`,
- the relative gain of `NHEFT` over `DHEFT` should show an upward trend.

## Outputs
- `grid_e13_results.csv` (raw data)
- `grid_e13_summary.csv` (aggregated statistics)
- `run_manifest.json` (experiment metadata)
- `base_properties_snapshot.properties` (baseline snapshot)
- `e13_image_size_trend.png` (trend plot)
- `e13_makespan_comparison.png` (grouped bar chart)

## Run

```bash
cd /Users/tengfeisun/Developer/2026/with-downloadscheduling2022-t/experiments/e13
python3 run_experiment.py
```

Dry run:

```bash
E13_DRY_RUN=1 python3 run_experiment.py
```

## Analysis

After the experiment finishes:

```bash
python3 analyze_results.py run_YYYYMMDD_HHMMSS
```

Example:

```bash
python3 analyze_results.py run_20260527_123000
```

