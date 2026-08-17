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
| (0.10, 0.18] | 2000 | 1842 | 2000 | 1842 | 1842 | 100.0% | 100.0% |
| (0.18, 0.32] | 2000 | 1585 | 2000 | 1585 | 1585 | 100.0% | 100.0% |
| (0.32, 0.56] | 2000 | 1858 | 2000 | 1858 | 1858 | 100.0% | 100.0% |
| (0.56, 1.00] | 2000 | 1973 | 2000 | 1973 | 1973 | 100.0% | 100.0% |
| (1.00, 1.78] | 2000 | 1912 | 2000 | 1912 | 1912 | 100.0% | 100.0% |
| (1.78, 3.16] | 2000 | 1950 | 2000 | 1950 | 1950 | 100.0% | 100.0% |
| (3.16, 5.62] | 2000 | 1949 | 2000 | 1949 | 1949 | 100.0% | 100.0% |
| (5.62, 10.00] | 2000 | 1903 | 2000 | 1903 | 1903 | 100.0% | 100.0% |
