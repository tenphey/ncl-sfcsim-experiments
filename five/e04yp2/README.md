# e04yp2

Fallback calibration follow-up for `e04y`, to use if `e04yp1` still produces
too few valid image-dominant samples.

- Target bucket: `0.56 < NCCR_total <= 1.00`
- Target composition: image-dominant, `CCR_data < IDR_image`
- Analysis composition rule: relative gap at least `20%`
- Purpose: further increase the number of valid image-dominant samples without locking any random range

Compared with `e04y`, this stronger fallback uses:

- `vnf_datasize_min=660`
- `vnf_datasize_max=1005`
- `vnf_image_size_min=590`
- `vnf_image_size_max=925`

These values move the communication-composition center further toward
image-dominant while keeping non-zero ranges for random generation. The expected
valid-count increase is only an estimate based on a read-only reclassification of
the previous `e04y` samples; the final count must be checked after the run.

Run from the repository root:

```bash
experiments/.venv/bin/python experiments/five/e04yp2/run_experiment.py
```

The run uses the shared seed manifest and the same DHEFT/NHEFT/GHEFT runner as the
other `experiments/five` scenarios. Raw rows are retained and filtered during later
analysis.
