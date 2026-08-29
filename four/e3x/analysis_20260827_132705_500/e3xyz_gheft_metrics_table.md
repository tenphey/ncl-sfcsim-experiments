# GHEFT Metrics by Scenario

- `Gain_G/D`: GHEFT makespan gain over DHEFT. Positive values mean that GHEFT is faster than DHEFT.
- `DeltaM_G/N`: GHEFT makespan change from NHEFT. Positive values mean that GHEFT is slower than NHEFT.
- `DeltaU_G/N`: GHEFT used-vCPU reduction from NHEFT. Positive values mean that GHEFT uses fewer vCPUs than NHEFT.
- Every percentage is calculated for each paired seed first and then averaged within the scenario.

## Balanced (CCR ~= IDR)

| NCCR bucket | Paired n | Gain_G/D (%) | DeltaM_G/N (%) | DeltaU_G/N (%) |
| --- | ---: | ---: | ---: | ---: |
| (0.10, 0.18] | 488 | -4.15 | 4.71 | 17.20 |
| (0.18, 0.32] | 394 | -3.49 | 4.11 | 15.30 |
| (0.32, 0.56] | 285 | -0.90 | 3.87 | 13.78 |
| (0.56, 1.00] | 173 | 4.97 | 5.37 | 14.26 |
| (1.00, 1.78] | 108 | 16.19 | 7.53 | 15.61 |
| (1.78, 3.16] | 59 | 23.43 | 10.67 | 21.86 |
| (3.16, 5.62] | 31 | 25.27 | 14.61 | 32.72 |
| (5.62, 10.00] | 12 | 32.16 | 11.13 | 35.46 |

## Image-dominant (CCR < IDR)

| NCCR bucket | Paired n | Gain_G/D (%) | DeltaM_G/N (%) | DeltaU_G/N (%) |
| --- | ---: | ---: | ---: | ---: |
| (0.10, 0.18] | 274 | -3.06 | 4.21 | 15.61 |
| (0.18, 0.32] | 238 | -2.08 | 3.77 | 14.07 |
| (0.32, 0.56] | 184 | 2.08 | 4.14 | 12.61 |
| (0.56, 1.00] | 154 | 7.25 | 4.43 | 12.60 |
| (1.00, 1.78] | 397 | 21.14 | 4.96 | 14.71 |
| (1.78, 3.16] | 186 | 25.11 | 10.38 | 21.50 |
| (3.16, 5.62] | 199 | 29.60 | 12.82 | 28.92 |
| (5.62, 10.00] | 254 | 32.23 | 8.91 | 36.20 |

## Data-dominant (CCR > IDR)

| NCCR bucket | Paired n | Gain_G/D (%) | DeltaM_G/N (%) | DeltaU_G/N (%) |
| --- | ---: | ---: | ---: | ---: |
| (0.10, 0.18] | 475 | -5.43 | 5.73 | 19.23 |
| (0.18, 0.32] | 417 | -5.54 | 5.31 | 17.47 |
| (0.32, 0.56] | 469 | -4.60 | 5.20 | 16.46 |
| (0.56, 1.00] | 495 | 0.70 | 7.57 | 14.94 |
| (1.00, 1.78] | 490 | 12.64 | 7.15 | 16.87 |
| (1.78, 3.16] | 493 | 16.86 | 11.73 | 21.32 |
| (3.16, 5.62] | 493 | 17.52 | 16.17 | 28.82 |
| (5.62, 10.00] | 488 | 16.75 | 17.11 | 38.41 |
