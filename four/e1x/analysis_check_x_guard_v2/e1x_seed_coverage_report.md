# E1X Seed Coverage Report

## Definitions
- Planned seeds: target seed count written in `run_manifest.json` (if available).
- Recorded seeds: unique seeds that appear in the raw CSV for that bucket.
- OK seeds: recorded seeds that contain at least one `status = ok` row.
- Scenario-valid seeds: OK seeds that satisfy the current bucket rule and the x-condition (`|CCR_data - IDR_image| <= 0.0200`).
- Complete valid seeds: scenario-valid seeds that contain both expected variants (`baseline` and `comp_advantage`) and are actually used in the final aggregation.

## Coverage Table

| Bucket | Planned seeds | Recorded seeds | OK seeds | Scenario-valid seeds | Complete valid seeds | Valid / Recorded | Used / Valid |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| (0.10, 0.18] | 500 | 500 | 500 | 488 | 488 | 97.6% | 100.0% |
| (0.18, 0.32] | 500 | 500 | 500 | 394 | 394 | 78.8% | 100.0% |
| (0.32, 0.56] | 500 | 500 | 500 | 285 | 285 | 57.0% | 100.0% |
| (0.56, 1.00] | 500 | 500 | 500 | 173 | 173 | 34.6% | 100.0% |
| (1.00, 1.78] | 500 | 500 | 500 | 108 | 108 | 21.6% | 100.0% |
| (1.78, 3.16] | 500 | 500 | 500 | 59 | 59 | 11.8% | 100.0% |
| (3.16, 5.62] | 500 | 500 | 500 | 31 | 31 | 6.2% | 100.0% |
| (5.62, 10.00] | 500 | 500 | 500 | 12 | 12 | 2.4% | 100.0% |

## Low-Coverage Buckets

The following buckets have fewer than 100 complete valid seeds:

- (1.78, 3.16]: complete valid seeds = 59
- (3.16, 5.62]: complete valid seeds = 31
- (5.62, 10.00]: complete valid seeds = 12
