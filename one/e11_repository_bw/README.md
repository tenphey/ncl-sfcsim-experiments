# E11: Repository Bandwidth Impact on NHEFT Advantage

**Hypothesis H1**: When repository bandwidth decreases, mirror download becomes a tighter bottleneck, and NHEFT's dynamic bandwidth simulation provides more significant advantages over DHEFT's static pre-download model.

## Experiment Design

### Variables
- `repository_bw ∈ {60, 120, 240, 480}` MBps

### Fixed Parameters
- `vnf_type_max = 20` (high diversity, low repetition per type)
- `sfc_vnf_num = 200` (fixed total task count)
- `vnf_image_size_min = 2400`, `vnf_image_size_max = 6200` (large images)
- `multiple_sfc_num = 1` (single SFC)

### Repetition
- 50 random seeds per grid point (adjust via `E11_NUM_SEEDS`)
- Total: 4 repo_bw levels × 50 seeds = 200 runs

## Output

Each run creates a timestamped directory `experiments/e11/run_YYYYMMDD_HHMMSS/` containing:

- `grid_e11_results.csv` — Raw results (200 rows):
  ```
  repo_bw, seed, HEFT, DHEFT, NHEFT, time_sec
  60, 1001, ..., ..., ..., ...
  ```

- `grid_e11_summary.csv` — Aggregated statistics by repo_bw:
  ```
  repo_bw, HEFT_mean, HEFT_std, DHEFT_mean, DHEFT_std, NHEFT_mean, NHEFT_std,
  gain_N_over_D_mean, gain_N_over_D_std, wins_count, p_value
  ```

- `e11_repo_bw_trend.png` — **Line plot** (primary visualization):
  - x-axis: repository_bw (60, 120, 240, 480)
  - y-axis: NHEFT gain % over DHEFT (mean ± std)
  - Shows clear downward trend as repo_bw increases

- `run_manifest.json` — Provenance (timestamp, SEEDS, config snapshot)
- `base_properties_snapshot.properties` — Baseline config used

## Quick Start

### Dry Run (no Java execution)
```bash
cd experiments/e11
E11_DRY_RUN=1 python3 run_experiment.py
```

### Full Execution
```bash
# Run with default 50 seeds per grid point
cd experiments/e11
python3 run_experiment.py

# Or limit runs for testing
E11_LIMIT_RUNS=1 python3 run_experiment.py

# Analyze and generate chart
python3 analyze_results.py run_YYYYMMDD_HHMMSS
```

### Or use the convenience wrapper
```bash
bash run_all.sh
```

## Expected Results

### H1 Prediction
NHEFT gain % **decreases as repo_bw increases**:

| repo_bw | Expected gain % | Interpretation |
|---------|-----------------|-----------------|
| 60 | ~45% | Very tight bottleneck; dynamic scheduling highly valuable |
| 120 | ~30% | Moderate bottleneck; some improvement |
| 240 | ~15% | Loose bottleneck; limited opportunity |
| 480 | ~5% | No bottleneck; algorithms similar |

### Visual Pattern
The line plot should show a clear **downward slope** (monotonic or near-monotonic), validating H1.

## Configuration

To customize grid scope:

```bash
# Edit run_experiment.py, find these lines:
REPO_BWS = [60, 120, 240, 480]           # Bandwidth levels
SEEDS = random.sample(range(1000, 9999), 50)  # 50 random seeds
NUM_SEEDS = int(os.getenv('E11_NUM_SEEDS', str(len(SEEDS))))
```

## Notes

- Scripts assume Java classes & lib jars in `./classes/` and `./lib/`
- Base config from `../base.properties`
- Analysis requires: `pandas`, `matplotlib`, `scipy`
- Runtime: ~1-2 hours for 200 total runs (depends on machine)

## Troubleshooting

**Java OutOfMemory**: Increase `-Xmx` in `run_experiment.py`

**Slow runs**: Check if Java processes are blocking; run smaller subset first via `E11_LIMIT_RUNS`

**Missing CSV**: Check `run_YYYYMMDD_HHMMSS/used_properties.properties` for config snapshot

