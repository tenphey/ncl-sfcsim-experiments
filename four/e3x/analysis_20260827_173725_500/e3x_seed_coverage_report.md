# E3X Seed Coverage Report

## Definitions
- Baseline side: shared baseline results from `e01x` to `e08x`.
- GHEFT side: IRT-only gate results from `e31x` to `e38x`.
- Recorded seeds: unique seeds that appear in the raw CSV.
- OK seeds: recorded seeds that contain at least one `status = ok` row.
- Valid seeds: OK seeds that satisfy the current bucket rule and the x-condition (`|CCR_data - IDR_image| <= 0.0200`).
- Paired seeds: seeds that are valid on both sides and therefore actually used in the final aggregation.

## Coverage Table

| Bucket | Baseline recorded | Baseline valid | GHEFT recorded | GHEFT valid | Paired seeds | Paired / Baseline valid | Paired / GHEFT valid |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| (0.10, 0.18] | 500 | 488 | 500 | 488 | 488 | 100.0% | 100.0% |
| (0.18, 0.32] | 500 | 394 | 500 | 394 | 394 | 100.0% | 100.0% |
| (0.32, 0.56] | 500 | 285 | 500 | 285 | 285 | 100.0% | 100.0% |
| (0.56, 1.00] | 500 | 173 | 500 | 173 | 173 | 100.0% | 100.0% |
| (1.00, 1.78] | 500 | 108 | 500 | 108 | 108 | 100.0% | 100.0% |
| (1.78, 3.16] | 500 | 59 | 500 | 59 | 59 | 100.0% | 100.0% |
| (3.16, 5.62] | 500 | 31 | 500 | 31 | 31 | 100.0% | 100.0% |
| (5.62, 10.00] | 500 | 12 | 500 | 12 | 12 | 100.0% | 100.0% |

## Low-Coverage Buckets

The following buckets have fewer than 100 paired seeds:

- (1.78, 3.16]: paired seeds = 59
- (3.16, 5.62]: paired seeds = 31
- (5.62, 10.00]: paired seeds = 12
