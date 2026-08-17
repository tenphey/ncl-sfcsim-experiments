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
| (0.10, 0.18] | 2000 | 1926 | 2000 | 1926 | 1926 | 100.0% | 100.0% |
| (0.18, 0.32] | 2000 | 1477 | 2000 | 1477 | 1477 | 100.0% | 100.0% |
| (0.32, 0.56] | 2000 | 1064 | 2000 | 1064 | 1064 | 100.0% | 100.0% |
| (0.56, 1.00] | 2000 | 589 | 2000 | 589 | 589 | 100.0% | 100.0% |
| (1.00, 1.78] | 2000 | 359 | 2000 | 359 | 359 | 100.0% | 100.0% |
| (1.78, 3.16] | 2000 | 187 | 2000 | 187 | 187 | 100.0% | 100.0% |
| (3.16, 5.62] | 2000 | 111 | 2000 | 111 | 111 | 100.0% | 100.0% |
| (5.62, 10.00] | 2000 | 62 | 2000 | 62 | 62 | 100.0% | 100.0% |

## Low-Coverage Buckets

The following buckets have fewer than 100 paired seeds:

- (5.62, 10.00]: paired seeds = 62
