# E1Z Seed Coverage Report

## Definitions
- Planned seeds: target seed count written in `run_manifest.json` (if available).
- Recorded seeds: unique seeds that appear in the raw CSV for that bucket.
- OK seeds: recorded seeds that contain at least one `status = ok` row.
- Scenario-valid seeds: OK seeds that satisfy the current bucket rule and the z-condition (`CCR_data > IDR_image` and relative CCR/IDR gap >= 20.0%).
- Complete valid seeds: scenario-valid seeds that contain both expected variants (`baseline` and `comp_advantage`) and are actually used in the final aggregation.

## Coverage Table

| Bucket | Planned seeds | Recorded seeds | OK seeds | Scenario-valid seeds | Complete valid seeds | Valid / Recorded | Used / Valid |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| (0.10, 0.18] | 500 | 500 | 500 | 475 | 475 | 95.0% | 100.0% |
| (0.18, 0.32] | 500 | 500 | 500 | 417 | 417 | 83.4% | 100.0% |
| (0.32, 0.56] | 500 | 500 | 500 | 469 | 469 | 93.8% | 100.0% |
| (0.56, 1.00] | 500 | 500 | 500 | 495 | 495 | 99.0% | 100.0% |
| (1.00, 1.78] | 500 | 500 | 500 | 490 | 490 | 98.0% | 100.0% |
| (1.78, 3.16] | 500 | 500 | 500 | 493 | 493 | 98.6% | 100.0% |
| (3.16, 5.62] | 500 | 500 | 500 | 493 | 493 | 98.6% | 100.0% |
| (5.62, 10.00] | 500 | 500 | 500 | 488 | 488 | 97.6% | 100.0% |
