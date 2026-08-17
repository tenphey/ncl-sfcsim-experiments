# E3Y Seed Coverage Report

## Definitions
- Baseline side: shared baseline results from `e01y` to `e08y`.
- GHEFT side: IRT-only gate results from `e31y` to `e38y`.
- Recorded seeds: unique seeds that appear in the raw CSV.
- OK seeds: recorded seeds that contain at least one `status = ok` row.
- Valid seeds: OK seeds that satisfy the current bucket rule and the y-condition (`CCR_data < IDR_image` and relative gap >= 20.00%).
- Paired seeds: seeds that are valid on both sides and therefore actually used in the final aggregation.

## Coverage Table

| Bucket | Baseline recorded | Baseline valid | GHEFT recorded | GHEFT valid | Paired seeds | Paired / Baseline valid | Paired / GHEFT valid |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| (0.10, 0.18] | 500 | 274 | 500 | 274 | 274 | 100.0% | 100.0% |
| (0.18, 0.32] | 500 | 238 | 500 | 238 | 238 | 100.0% | 100.0% |
| (0.32, 0.56] | 500 | 184 | 500 | 184 | 184 | 100.0% | 100.0% |
| (0.56, 1.00] | 500 | 154 | 500 | 154 | 154 | 100.0% | 100.0% |
| (1.00, 1.78] | 500 | 397 | 500 | 397 | 397 | 100.0% | 100.0% |
| (1.78, 3.16] | 500 | 186 | 500 | 186 | 186 | 100.0% | 100.0% |
| (3.16, 5.62] | 500 | 199 | 500 | 199 | 199 | 100.0% | 100.0% |
| (5.62, 10.00] | 500 | 254 | 500 | 254 | 254 | 100.0% | 100.0% |
