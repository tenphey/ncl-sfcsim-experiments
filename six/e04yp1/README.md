# e04yp1

Calibration follow-up for `e04y`.

- Target bucket: `0.56 < NCCR_total <= 1.00`
- Target composition: image-dominant, `CCR_data < IDR_image`
- Analysis composition rule: relative gap at least `20%`
- Purpose: increase the number of valid image-dominant samples without locking any random range

Compared with `e04y`, this variant uses:

- `vnf_datasize_min=750`
- `vnf_datasize_max=1140`
- `vnf_image_size_min=560`
- `vnf_image_size_max=890`

These values move the communication-composition center toward image-dominant while
keeping non-zero ranges for random generation. The expected valid-count increase is
an estimate based on a read-only reclassification of the previous `e04y` samples;
the final count must be checked after the run.

Run from the repository root:

```bash
experiments/.venv/bin/python experiments/five/e04yp1/run_experiment.py
```

The run uses the shared seed manifest and the same DHEFT/NHEFT/GHEFT runner as the
other `experiments/five` scenarios. Raw rows are retained and filtered during later
analysis.
