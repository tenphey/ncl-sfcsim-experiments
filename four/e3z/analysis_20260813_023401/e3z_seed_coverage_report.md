# E3Z Seed Coverage Report

## Definitions
- Baseline side: shared baseline results from `e01z` to `e08z`.
- GHEFT side: IRT-only gate results from `e31z` to `e38z`.
- Recorded seeds: unique seeds that appear in the raw CSV.
- OK seeds: recorded seeds that contain at least one `status = ok` row.
- Valid seeds: OK seeds that satisfy the current bucket rule and the z-condition (`CCR_data > IDR_image` and relative gap >= 20.00%).
- Paired seeds: seeds that are valid on both sides and therefore actually used in the final aggregation.

## Coverage Table

| Bucket | Baseline recorded | Baseline valid | GHEFT recorded | GHEFT valid | Paired seeds | Paired / Baseline valid | Paired / GHEFT valid |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| (0.10, 0.18] | 500 | 475 | 500 | 475 | 475 | 100.0% | 100.0% |
| (0.18, 0.32] | 500 | 417 | 500 | 417 | 417 | 100.0% | 100.0% |
| (0.32, 0.56] | 500 | 469 | 500 | 469 | 469 | 100.0% | 100.0% |
| (0.56, 1.00] | 500 | 495 | 500 | 495 | 495 | 100.0% | 100.0% |
| (1.00, 1.78] | 500 | 490 | 500 | 490 | 490 | 100.0% | 100.0% |
| (1.78, 3.16] | 500 | 493 | 500 | 493 | 493 | 100.0% | 100.0% |
| (3.16, 5.62] | 500 | 493 | 500 | 493 | 493 | 100.0% | 100.0% |
| (5.62, 10.00] | 500 | 488 | 500 | 488 | 488 | 100.0% | 100.0% |
