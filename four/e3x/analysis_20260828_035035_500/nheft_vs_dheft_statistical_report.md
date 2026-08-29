# NHEFT vs DHEFT Paired Statistical Analysis

## Method

- Source: the exact original 500-seed per-scenario files used to produce the paper's NHEFT gain-rate and win-rate table.
- Unit of analysis: a DHEFT/NHEFT pair generated from the same seed.
- Variation: sample standard deviation of the per-seed NHEFT gain over DHEFT.
- Confidence interval: 95% percentile bootstrap interval for the mean gain (10,000 resamples, fixed random seed).
- Significance test: two-sided paired Wilcoxon signed-rank test for DHEFT and NHEFT makespan.
- Multiple comparisons: Holm correction across all 24 scenarios; significant means adjusted p < 0.05.

Holm-significant scenarios: 22 / 24.

| NCCR bucket | Composition | Paired n | Gain mean | Gain SD | 95% CI | Win rate | Raw p | Holm p | Significant |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | :---: |
| (0.10, 0.18] | Balanced (CCR ~= IDR) | 480 | 0.45% | 2.78 | [0.20, 0.69] | 56.7% | 4.45e-05 | 0.0003 | Yes |
| (0.10, 0.18] | Image-dominant (CCR < IDR) | 273 | 0.52% | 3.34 | [0.13, 0.92] | 58.2% | 0.0007 | 0.0021 | Yes |
| (0.10, 0.18] | Data-dominant (CCR > IDR) | 458 | 0.05% | 2.90 | [-0.21, 0.31] | 48.9% | 0.5009 | 0.9410 | No |
| (0.18, 0.32] | Balanced (CCR ~= IDR) | 360 | 0.84% | 3.85 | [0.45, 1.23] | 56.4% | 5.72e-05 | 0.0003 | Yes |
| (0.18, 0.32] | Image-dominant (CCR < IDR) | 244 | 1.59% | 3.89 | [1.12, 2.09] | 65.2% | 1.58e-09 | 1.10e-08 | Yes |
| (0.18, 0.32] | Data-dominant (CCR > IDR) | 389 | -0.18% | 4.32 | [-0.62, 0.25] | 47.3% | 0.4705 | 0.9410 | No |
| (0.32, 0.56] | Balanced (CCR ~= IDR) | 293 | 3.10% | 5.75 | [2.43, 3.76] | 72.7% | 8.64e-18 | 7.78e-17 | Yes |
| (0.32, 0.56] | Image-dominant (CCR < IDR) | 207 | 4.64% | 7.63 | [3.58, 5.67] | 77.8% | 1.32e-17 | 1.05e-16 | Yes |
| (0.32, 0.56] | Data-dominant (CCR > IDR) | 460 | 0.83% | 6.09 | [0.27, 1.38] | 58.5% | 6.02e-05 | 0.0003 | Yes |
| (0.56, 1.00] | Balanced (CCR ~= IDR) | 273 | 10.28% | 8.01 | [9.31, 11.21] | 91.2% | 2.33e-41 | 3.03e-40 | Yes |
| (0.56, 1.00] | Image-dominant (CCR < IDR) | 171 | 10.41% | 8.07 | [9.21, 11.63] | 88.9% | 1.77e-26 | 1.77e-25 | Yes |
| (0.56, 1.00] | Data-dominant (CCR > IDR) | 492 | 7.00% | 9.10 | [6.21, 7.80] | 78.5% | 1.99e-45 | 2.99e-44 | Yes |
| (1.00, 1.78] | Balanced (CCR ~= IDR) | 292 | 22.27% | 8.38 | [21.31, 23.21] | 97.9% | 3.22e-49 | 5.80e-48 | Yes |
| (1.00, 1.78] | Image-dominant (CCR < IDR) | 412 | 23.40% | 7.80 | [22.63, 24.15] | 99.0% | 3.67e-69 | 7.33e-68 | Yes |
| (1.00, 1.78] | Data-dominant (CCR > IDR) | 474 | 17.55% | 9.25 | [16.72, 18.37] | 96.0% | 5.76e-77 | 1.21e-75 | Yes |
| (1.78, 3.16] | Balanced (CCR ~= IDR) | 289 | 30.62% | 7.44 | [29.74, 31.44] | 99.7% | 4.30e-49 | 6.88e-48 | Yes |
| (1.78, 3.16] | Image-dominant (CCR < IDR) | 203 | 31.77% | 6.88 | [30.82, 32.70] | 100.0% | 4.63e-35 | 5.09e-34 | Yes |
| (1.78, 3.16] | Data-dominant (CCR > IDR) | 488 | 24.54% | 9.03 | [23.73, 25.35] | 99.2% | 2.19e-81 | 5.24e-80 | Yes |
| (3.16, 5.62] | Balanced (CCR ~= IDR) | 289 | 35.46% | 6.75 | [34.69, 36.23] | 100.0% | 3.83e-49 | 6.52e-48 | Yes |
| (3.16, 5.62] | Image-dominant (CCR < IDR) | 217 | 35.75% | 7.51 | [34.75, 36.74] | 100.0% | 2.35e-37 | 2.82e-36 | Yes |
| (3.16, 5.62] | Data-dominant (CCR > IDR) | 487 | 27.90% | 9.40 | [27.04, 28.72] | 99.4% | 2.22e-81 | 5.24e-80 | Yes |
| (5.62, 10.00] | Balanced (CCR ~= IDR) | 298 | 36.57% | 8.62 | [35.56, 37.53] | 100.0% | 1.29e-50 | 2.46e-49 | Yes |
| (5.62, 10.00] | Image-dominant (CCR < IDR) | 264 | 36.27% | 8.77 | [35.22, 37.30] | 99.6% | 4.84e-45 | 6.77e-44 | Yes |
| (5.62, 10.00] | Data-dominant (CCR > IDR) | 471 | 26.35% | 11.19 | [25.34, 27.34] | 98.3% | 3.40e-78 | 7.49e-77 | Yes |
