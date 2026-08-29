# E3XYZ Paired Statistical Analysis

## Method

- All statistics use paired per-seed observations after the same NCCR and CCR/IDR scenario filters used by the figures.
- Variation is reported as the sample standard deviation of the per-seed percentage effect.
- The 95% confidence interval is a percentile bootstrap interval for the mean (10,000 resamples, fixed seed).
- Significance is tested with a two-sided paired Wilcoxon signed-rank test. Zero paired differences are excluded from the signed-rank sum.
- Holm correction is applied across the 24 scenarios separately within each comparison family.
- `Significant` means Holm-adjusted p < 0.05. A win rate is descriptive evidence and is not used as a replacement for this test.

## NHEFT vs DHEFT makespan

Effect: NHEFT gain over DHEFT (%). Positive values mean that NHEFT is faster.

Holm-significant scenarios: 21 / 24.

| NCCR bucket | Composition | Paired n | Mean effect | SD | 95% CI for mean | Nonzero n | W | Raw p | Holm p | Significant |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | :---: |
| (0.10, 0.18] | Balanced (CCR ~= IDR) | 488 | 0.48 | 2.96 | [0.21, 0.74] | 485 | 46444.00 | 5.29e-05 | 0.0003 | Yes |
| (0.10, 0.18] | Image-dominant (CCR < IDR) | 274 | 1.06 | 2.84 | [0.72, 1.39] | 272 | 10906.00 | 3.69e-09 | 2.96e-08 | Yes |
| (0.10, 0.18] | Data-dominant (CCR > IDR) | 475 | 0.24 | 2.99 | [-0.03, 0.51] | 473 | 49489.00 | 0.0274 | 0.0821 | No |
| (0.18, 0.32] | Balanced (CCR ~= IDR) | 394 | 0.49 | 4.27 | [0.06, 0.90] | 392 | 32064.00 | 0.0041 | 0.0162 | Yes |
| (0.18, 0.32] | Image-dominant (CCR < IDR) | 238 | 1.57 | 4.46 | [0.99, 2.11] | 236 | 7984.00 | 1.10e-08 | 7.73e-08 | Yes |
| (0.18, 0.32] | Data-dominant (CCR > IDR) | 417 | -0.29 | 3.93 | [-0.68, 0.08] | 413 | 41513.00 | 0.6116 | 0.6116 | No |
| (0.32, 0.56] | Balanced (CCR ~= IDR) | 285 | 2.67 | 6.35 | [1.93, 3.40] | 284 | 10456.00 | 1.67e-12 | 1.84e-11 | Yes |
| (0.32, 0.56] | Image-dominant (CCR < IDR) | 184 | 5.80 | 6.37 | [4.90, 6.72] | 183 | 1514.00 | 6.49e-22 | 8.44e-21 | Yes |
| (0.32, 0.56] | Data-dominant (CCR > IDR) | 469 | 0.40 | 6.24 | [-0.17, 0.96] | 468 | 48863.00 | 0.0401 | 0.0821 | No |
| (0.56, 1.00] | Balanced (CCR ~= IDR) | 173 | 9.58 | 8.48 | [8.32, 10.85] | 173 | 1006.00 | 4.97e-23 | 7.45e-22 | Yes |
| (0.56, 1.00] | Image-dominant (CCR < IDR) | 154 | 10.83 | 8.38 | [9.51, 12.17] | 154 | 492.00 | 5.24e-23 | 7.45e-22 | Yes |
| (0.56, 1.00] | Data-dominant (CCR > IDR) | 495 | 7.42 | 8.49 | [6.67, 8.16] | 495 | 13231.00 | 1.16e-51 | 2.20e-50 | Yes |
| (1.00, 1.78] | Balanced (CCR ~= IDR) | 108 | 21.77 | 8.25 | [20.23, 23.31] | 108 | 0.00 | 1.87e-19 | 2.24e-18 | Yes |
| (1.00, 1.78] | Image-dominant (CCR < IDR) | 397 | 24.58 | 8.19 | [23.79, 25.38] | 397 | 27.00 | 1.04e-66 | 2.07e-65 | Yes |
| (1.00, 1.78] | Data-dominant (CCR > IDR) | 490 | 18.09 | 9.20 | [17.26, 18.90] | 490 | 727.00 | 4.57e-80 | 9.59e-79 | Yes |
| (1.78, 3.16] | Balanced (CCR ~= IDR) | 59 | 30.56 | 8.20 | [28.44, 32.55] | 59 | 0.00 | 2.39e-11 | 2.39e-10 | Yes |
| (1.78, 3.16] | Image-dominant (CCR < IDR) | 186 | 31.81 | 7.56 | [30.70, 32.87] | 186 | 0.00 | 2.84e-32 | 4.54e-31 | Yes |
| (1.78, 3.16] | Data-dominant (CCR > IDR) | 493 | 25.30 | 8.90 | [24.51, 26.08] | 493 | 20.00 | 1.99e-82 | 4.77e-81 | Yes |
| (3.16, 5.62] | Balanced (CCR ~= IDR) | 31 | 34.85 | 7.46 | [32.23, 37.37] | 31 | 0.00 | 9.31e-10 | 8.38e-09 | Yes |
| (3.16, 5.62] | Image-dominant (CCR < IDR) | 199 | 37.36 | 6.98 | [36.39, 38.31] | 199 | 0.00 | 2.09e-34 | 3.56e-33 | Yes |
| (3.16, 5.62] | Data-dominant (CCR > IDR) | 493 | 28.89 | 9.25 | [28.07, 29.71] | 493 | 26.00 | 2.06e-82 | 4.77e-81 | Yes |
| (5.62, 10.00] | Balanced (CCR ~= IDR) | 12 | 38.62 | 8.04 | [34.37, 43.09] | 12 | 0.00 | 0.0005 | 0.0024 | Yes |
| (5.62, 10.00] | Image-dominant (CCR < IDR) | 254 | 37.57 | 7.89 | [36.58, 38.51] | 254 | 0.00 | 2.05e-43 | 3.69e-42 | Yes |
| (5.62, 10.00] | Data-dominant (CCR > IDR) | 488 | 28.50 | 11.40 | [27.50, 29.50] | 488 | 138.00 | 2.69e-81 | 5.92e-80 | Yes |

## GHEFT vs DHEFT makespan

Effect: GHEFT gain over DHEFT (%). Positive values mean that GHEFT is faster.

Holm-significant scenarios: 23 / 24.

| NCCR bucket | Composition | Paired n | Mean effect | SD | 95% CI for mean | Nonzero n | W | Raw p | Holm p | Significant |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | :---: |
| (0.10, 0.18] | Balanced (CCR ~= IDR) | 488 | -4.15 | 5.83 | [-4.68, -3.66] | 486 | 11858.00 | 1.15e-52 | 2.06e-51 | Yes |
| (0.10, 0.18] | Image-dominant (CCR < IDR) | 274 | -3.06 | 5.99 | [-3.82, -2.38] | 272 | 6518.00 | 1.75e-20 | 1.93e-19 | Yes |
| (0.10, 0.18] | Data-dominant (CCR > IDR) | 475 | -5.43 | 6.72 | [-6.07, -4.86] | 473 | 8785.00 | 7.30e-57 | 1.39e-55 | Yes |
| (0.18, 0.32] | Balanced (CCR ~= IDR) | 394 | -3.49 | 6.29 | [-4.12, -2.88] | 393 | 13783.00 | 1.91e-28 | 2.48e-27 | Yes |
| (0.18, 0.32] | Image-dominant (CCR < IDR) | 238 | -2.08 | 7.05 | [-3.01, -1.22] | 236 | 9587.00 | 2.83e-05 | 0.0001 | Yes |
| (0.18, 0.32] | Data-dominant (CCR > IDR) | 417 | -5.54 | 7.16 | [-6.24, -4.87] | 415 | 7038.00 | 2.15e-49 | 3.65e-48 | Yes |
| (0.32, 0.56] | Balanced (CCR ~= IDR) | 285 | -0.90 | 8.69 | [-1.90, 0.09] | 284 | 19256.00 | 0.4797 | 0.4797 | No |
| (0.32, 0.56] | Image-dominant (CCR < IDR) | 184 | 2.08 | 8.19 | [0.87, 3.20] | 183 | 5202.00 | 7.40e-06 | 3.70e-05 | Yes |
| (0.32, 0.56] | Data-dominant (CCR > IDR) | 469 | -4.60 | 9.61 | [-5.48, -3.74] | 468 | 27600.00 | 1.20e-20 | 1.44e-19 | Yes |
| (0.56, 1.00] | Balanced (CCR ~= IDR) | 173 | 4.97 | 11.67 | [3.22, 6.66] | 173 | 3720.00 | 8.00e-09 | 5.60e-08 | Yes |
| (0.56, 1.00] | Image-dominant (CCR < IDR) | 154 | 7.25 | 9.59 | [5.72, 8.74] | 154 | 1604.00 | 3.52e-15 | 3.16e-14 | Yes |
| (0.56, 1.00] | Data-dominant (CCR > IDR) | 495 | 0.70 | 14.25 | [-0.58, 1.94] | 495 | 48625.00 | 6.18e-05 | 0.0002 | Yes |
| (1.00, 1.78] | Balanced (CCR ~= IDR) | 108 | 16.19 | 11.69 | [13.96, 18.38] | 108 | 254.00 | 1.69e-16 | 1.69e-15 | Yes |
| (1.00, 1.78] | Image-dominant (CCR < IDR) | 397 | 21.14 | 8.62 | [20.29, 21.98] | 397 | 104.00 | 1.85e-66 | 4.08e-65 | Yes |
| (1.00, 1.78] | Data-dominant (CCR > IDR) | 490 | 12.64 | 11.73 | [11.59, 13.66] | 490 | 8863.00 | 4.09e-60 | 8.17e-59 | Yes |
| (1.78, 3.16] | Balanced (CCR ~= IDR) | 59 | 23.43 | 10.93 | [20.61, 26.09] | 59 | 9.00 | 3.79e-11 | 3.03e-10 | Yes |
| (1.78, 3.16] | Image-dominant (CCR < IDR) | 186 | 25.11 | 8.68 | [23.84, 26.35] | 186 | 11.00 | 3.39e-32 | 4.74e-31 | Yes |
| (1.78, 3.16] | Data-dominant (CCR > IDR) | 493 | 16.86 | 12.57 | [15.73, 17.98] | 493 | 5040.00 | 1.09e-69 | 2.62e-68 | Yes |
| (3.16, 5.62] | Balanced (CCR ~= IDR) | 31 | 25.27 | 13.34 | [20.36, 29.71] | 31 | 6.00 | 1.30e-08 | 7.82e-08 | Yes |
| (3.16, 5.62] | Image-dominant (CCR < IDR) | 199 | 29.60 | 9.00 | [28.36, 30.82] | 199 | 0.00 | 2.09e-34 | 3.14e-33 | Yes |
| (3.16, 5.62] | Data-dominant (CCR > IDR) | 493 | 17.52 | 14.61 | [16.22, 18.79] | 493 | 6284.00 | 1.06e-66 | 2.44e-65 | Yes |
| (5.62, 10.00] | Balanced (CCR ~= IDR) | 12 | 32.16 | 9.06 | [27.08, 36.77] | 12 | 0.00 | 0.0005 | 0.0010 | Yes |
| (5.62, 10.00] | Image-dominant (CCR < IDR) | 254 | 32.23 | 9.00 | [31.11, 33.32] | 254 | 6.00 | 2.20e-43 | 3.52e-42 | Yes |
| (5.62, 10.00] | Data-dominant (CCR > IDR) | 488 | 16.75 | 14.30 | [15.50, 18.03] | 488 | 6186.00 | 5.65e-66 | 1.19e-64 | Yes |

## GHEFT vs NHEFT makespan

Effect: GHEFT makespan change from NHEFT (%). Positive values mean that GHEFT is slower.

Holm-significant scenarios: 24 / 24.

| NCCR bucket | Composition | Paired n | Mean effect | SD | 95% CI for mean | Nonzero n | W | Raw p | Holm p | Significant |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | :---: |
| (0.10, 0.18] | Balanced (CCR ~= IDR) | 488 | 4.71 | 6.03 | [4.19, 5.25] | 461 | 7236.00 | 3.75e-58 | 7.88e-57 | Yes |
| (0.10, 0.18] | Image-dominant (CCR < IDR) | 274 | 4.21 | 6.12 | [3.53, 4.95] | 255 | 2716.00 | 8.38e-31 | 1.34e-29 | Yes |
| (0.10, 0.18] | Data-dominant (CCR > IDR) | 475 | 5.73 | 6.64 | [5.13, 6.34] | 453 | 5218.00 | 1.13e-61 | 2.49e-60 | Yes |
| (0.18, 0.32] | Balanced (CCR ~= IDR) | 394 | 4.11 | 6.67 | [3.47, 4.78] | 365 | 9276.00 | 5.89e-33 | 1.06e-31 | Yes |
| (0.18, 0.32] | Image-dominant (CCR < IDR) | 238 | 3.77 | 6.56 | [2.98, 4.65] | 218 | 3621.00 | 4.76e-19 | 4.29e-18 | Yes |
| (0.18, 0.32] | Data-dominant (CCR > IDR) | 417 | 5.31 | 7.19 | [4.64, 6.03] | 397 | 7466.00 | 1.50e-44 | 2.84e-43 | Yes |
| (0.32, 0.56] | Balanced (CCR ~= IDR) | 285 | 3.87 | 8.74 | [2.86, 4.89] | 251 | 7333.00 | 1.77e-13 | 1.42e-12 | Yes |
| (0.32, 0.56] | Image-dominant (CCR < IDR) | 184 | 4.14 | 8.07 | [3.02, 5.33] | 158 | 2106.00 | 4.26e-13 | 2.98e-12 | Yes |
| (0.32, 0.56] | Data-dominant (CCR > IDR) | 469 | 5.20 | 9.42 | [4.36, 6.06] | 445 | 19692.00 | 2.91e-28 | 4.07e-27 | Yes |
| (0.56, 1.00] | Balanced (CCR ~= IDR) | 173 | 5.37 | 11.31 | [3.73, 7.11] | 153 | 2715.00 | 7.29e-09 | 4.37e-08 | Yes |
| (0.56, 1.00] | Image-dominant (CCR < IDR) | 154 | 4.43 | 10.64 | [2.83, 6.14] | 134 | 2180.00 | 1.97e-07 | 5.91e-07 | Yes |
| (0.56, 1.00] | Data-dominant (CCR > IDR) | 495 | 7.57 | 14.48 | [6.32, 8.88] | 469 | 23540.00 | 5.98e-27 | 7.17e-26 | Yes |
| (1.00, 1.78] | Balanced (CCR ~= IDR) | 108 | 7.53 | 13.76 | [5.14, 10.26] | 107 | 1139.00 | 5.36e-08 | 2.68e-07 | Yes |
| (1.00, 1.78] | Image-dominant (CCR < IDR) | 397 | 4.96 | 9.49 | [4.03, 5.90] | 368 | 14944.00 | 1.32e-20 | 1.32e-19 | Yes |
| (1.00, 1.78] | Data-dominant (CCR > IDR) | 490 | 7.15 | 12.86 | [6.06, 8.30] | 477 | 22791.00 | 6.79e-30 | 1.02e-28 | Yes |
| (1.78, 3.16] | Balanced (CCR ~= IDR) | 59 | 10.67 | 13.08 | [7.45, 14.00] | 57 | 163.00 | 1.35e-07 | 5.41e-07 | Yes |
| (1.78, 3.16] | Image-dominant (CCR < IDR) | 186 | 10.38 | 11.86 | [8.68, 12.09] | 180 | 1492.00 | 2.03e-21 | 2.23e-20 | Yes |
| (1.78, 3.16] | Data-dominant (CCR > IDR) | 493 | 11.73 | 14.50 | [10.47, 13.02] | 484 | 10325.00 | 1.32e-55 | 2.64e-54 | Yes |
| (3.16, 5.62] | Balanced (CCR ~= IDR) | 31 | 14.61 | 14.79 | [9.69, 20.01] | 31 | 26.00 | 9.96e-07 | 1.99e-06 | Yes |
| (3.16, 5.62] | Image-dominant (CCR < IDR) | 199 | 12.82 | 12.51 | [11.12, 14.59] | 198 | 1078.00 | 1.67e-27 | 2.17e-26 | Yes |
| (3.16, 5.62] | Data-dominant (CCR > IDR) | 493 | 16.17 | 15.21 | [14.88, 17.54] | 492 | 5008.00 | 1.40e-69 | 3.23e-68 | Yes |
| (5.62, 10.00] | Balanced (CCR ~= IDR) | 12 | 11.13 | 11.55 | [4.80, 17.22] | 12 | 9.00 | 0.0161 | 0.0161 | Yes |
| (5.62, 10.00] | Image-dominant (CCR < IDR) | 254 | 8.91 | 9.80 | [7.73, 10.14] | 254 | 2592.00 | 3.92e-31 | 6.67e-30 | Yes |
| (5.62, 10.00] | Data-dominant (CCR > IDR) | 488 | 17.11 | 15.09 | [15.83, 18.46] | 488 | 4459.00 | 3.49e-70 | 8.39e-69 | Yes |

## GHEFT vs NHEFT used vCPUs

Effect: GHEFT vCPU reduction from NHEFT (%). Positive values mean that GHEFT uses fewer vCPUs.

Holm-significant scenarios: 24 / 24.

| NCCR bucket | Composition | Paired n | Mean effect | SD | 95% CI for mean | Nonzero n | W | Raw p | Holm p | Significant |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | :---: |
| (0.10, 0.18] | Balanced (CCR ~= IDR) | 488 | 17.20 | 7.61 | [16.51, 17.86] | 485 | 45.50 | 3.77e-81 | 7.92e-80 | Yes |
| (0.10, 0.18] | Image-dominant (CCR < IDR) | 274 | 15.61 | 7.32 | [14.76, 16.48] | 271 | 15.00 | 3.49e-46 | 4.19e-45 | Yes |
| (0.10, 0.18] | Data-dominant (CCR > IDR) | 475 | 19.23 | 7.94 | [18.52, 19.95] | 472 | 2.00 | 3.94e-79 | 7.89e-78 | Yes |
| (0.18, 0.32] | Balanced (CCR ~= IDR) | 394 | 15.30 | 7.45 | [14.58, 16.02] | 391 | 106.50 | 1.51e-65 | 2.27e-64 | Yes |
| (0.18, 0.32] | Image-dominant (CCR < IDR) | 238 | 14.07 | 7.72 | [13.07, 15.05] | 231 | 116.50 | 4.83e-39 | 4.83e-38 | Yes |
| (0.18, 0.32] | Data-dominant (CCR > IDR) | 417 | 17.47 | 7.80 | [16.71, 18.20] | 415 | 95.50 | 1.63e-69 | 2.61e-68 | Yes |
| (0.32, 0.56] | Balanced (CCR ~= IDR) | 285 | 13.78 | 8.00 | [12.84, 14.72] | 281 | 303.00 | 1.76e-46 | 2.28e-45 | Yes |
| (0.32, 0.56] | Image-dominant (CCR < IDR) | 184 | 12.61 | 6.96 | [11.61, 13.64] | 181 | 29.50 | 2.75e-31 | 1.92e-30 | Yes |
| (0.32, 0.56] | Data-dominant (CCR > IDR) | 469 | 16.46 | 7.95 | [15.74, 17.19] | 465 | 88.50 | 9.85e-78 | 1.68e-76 | Yes |
| (0.56, 1.00] | Balanced (CCR ~= IDR) | 173 | 14.26 | 9.29 | [12.87, 15.61] | 169 | 242.00 | 1.13e-27 | 6.79e-27 | Yes |
| (0.56, 1.00] | Image-dominant (CCR < IDR) | 154 | 12.60 | 8.68 | [11.21, 13.95] | 150 | 249.50 | 2.90e-24 | 1.45e-23 | Yes |
| (0.56, 1.00] | Data-dominant (CCR > IDR) | 495 | 14.94 | 8.33 | [14.19, 15.67] | 484 | 831.00 | 7.14e-79 | 1.36e-77 | Yes |
| (1.00, 1.78] | Balanced (CCR ~= IDR) | 108 | 15.61 | 9.41 | [13.77, 17.34] | 106 | 78.50 | 3.42e-18 | 1.37e-17 | Yes |
| (1.00, 1.78] | Image-dominant (CCR < IDR) | 397 | 14.71 | 9.45 | [13.75, 15.60] | 389 | 1143.50 | 8.73e-62 | 1.22e-60 | Yes |
| (1.00, 1.78] | Data-dominant (CCR > IDR) | 490 | 16.87 | 9.32 | [16.05, 17.69] | 479 | 845.00 | 5.37e-78 | 9.67e-77 | Yes |
| (1.78, 3.16] | Balanced (CCR ~= IDR) | 59 | 21.86 | 8.19 | [19.80, 23.90] | 59 | 1.50 | 2.45e-11 | 7.36e-11 | Yes |
| (1.78, 3.16] | Image-dominant (CCR < IDR) | 186 | 21.50 | 9.48 | [20.13, 22.84] | 184 | 8.50 | 6.39e-32 | 5.11e-31 | Yes |
| (1.78, 3.16] | Data-dominant (CCR > IDR) | 493 | 21.32 | 9.31 | [20.51, 22.16] | 491 | 61.50 | 4.47e-82 | 1.03e-80 | Yes |
| (3.16, 5.62] | Balanced (CCR ~= IDR) | 31 | 32.72 | 9.00 | [29.53, 35.70] | 31 | 0.00 | 1.16e-06 | 2.31e-06 | Yes |
| (3.16, 5.62] | Image-dominant (CCR < IDR) | 199 | 28.92 | 9.14 | [27.65, 30.22] | 199 | 1.00 | 1.96e-34 | 1.76e-33 | Yes |
| (3.16, 5.62] | Data-dominant (CCR > IDR) | 493 | 28.82 | 8.92 | [28.01, 29.61] | 493 | 0.00 | 1.41e-82 | 3.38e-81 | Yes |
| (5.62, 10.00] | Balanced (CCR ~= IDR) | 12 | 35.46 | 7.27 | [31.55, 39.42] | 12 | 0.00 | 0.0005 | 0.0005 | Yes |
| (5.62, 10.00] | Image-dominant (CCR < IDR) | 254 | 36.20 | 8.99 | [35.08, 37.29] | 254 | 0.00 | 1.77e-43 | 1.95e-42 | Yes |
| (5.62, 10.00] | Data-dominant (CCR > IDR) | 488 | 38.41 | 8.78 | [37.64, 39.18] | 488 | 0.00 | 8.97e-82 | 1.97e-80 | Yes |
