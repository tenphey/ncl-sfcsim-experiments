# E1Y Seed Coverage Report

## Definitions
- Planned seeds: target seed count written in `run_manifest.json` (if available).
- Recorded seeds: unique seeds that appear in the raw CSV for that bucket.
- OK seeds: recorded seeds that contain at least one `status = ok` row.
- Scenario-valid seeds: OK seeds that satisfy the current bucket rule and the y-condition (`CCR_data < IDR_image` and relative CCR/IDR gap >= 20.0%).
- Complete valid seeds: scenario-valid seeds that contain both expected variants (`baseline` and `comp_advantage`) and are actually used in the final aggregation.

## Coverage Table

| Bucket | Planned seeds | Recorded seeds | OK seeds | Scenario-valid seeds | Complete valid seeds | Valid / Recorded | Used / Valid |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| (0.10, 0.18] | - | 500 | 500 | 274 | 274 | 54.8% | 100.0% |
| (0.18, 0.32] | - | 500 | 500 | 238 | 238 | 47.6% | 100.0% |
| (0.32, 0.56] | - | 500 | 500 | 184 | 184 | 36.8% | 100.0% |
| (0.56, 1.00] | - | 500 | 500 | 154 | 154 | 30.8% | 100.0% |
| (1.00, 1.78] | - | 500 | 500 | 397 | 397 | 79.4% | 100.0% |
| (1.78, 3.16] | - | 500 | 500 | 186 | 186 | 37.2% | 100.0% |
| (3.16, 5.62] | - | 500 | 500 | 199 | 199 | 39.8% | 100.0% |
| (5.62, 10.00] | - | 500 | 500 | 254 | 254 | 50.8% | 100.0% |
