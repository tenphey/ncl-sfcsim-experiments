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
| (0.10, 0.18] | 2000 | 1031 | 2000 | 1031 | 1031 | 100.0% | 100.0% |
| (0.18, 0.32] | 2000 | 932 | 2000 | 932 | 932 | 100.0% | 100.0% |
| (0.32, 0.56] | 2000 | 756 | 2000 | 756 | 756 | 100.0% | 100.0% |
| (0.56, 1.00] | 2000 | 642 | 2000 | 642 | 642 | 100.0% | 100.0% |
| (1.00, 1.78] | 2000 | 1564 | 2000 | 1564 | 1564 | 100.0% | 100.0% |
| (1.78, 3.16] | 2000 | 769 | 2000 | 769 | 769 | 100.0% | 100.0% |
| (3.16, 5.62] | 2000 | 825 | 356 | 139 | 139 | 16.8% | 100.0% |
| (5.62, 10.00] | 2000 | 980 | 368 | 185 | 185 | 18.9% | 100.0% |
