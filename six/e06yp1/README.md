# e06yp1

Calibration fallback for `e06y`.

- Target bucket: `1.78 < NCCR_total <= 3.16`
- Target composition: image-dominant, `CCR_data < IDR_image`
- Analysis composition rule: directional relative gap at least `20%`
- Purpose: increase valid samples without locking any random range

Compared with `e06y`, this first fallback moderately reduces the data-size range
and increases the image-size range. The target NCCR bucket and composition rule
are unchanged. Both `min` and `max` values remain different, so random parameter
generation is preserved.

This is a calibration candidate, not an automatically selected replacement.
Check the valid count after a complete run before using it as the formal `e06y`
source.

Run from the repository root:

```bash
experiments/.venv/bin/python experiments/five/e06yp1/run_experiment.py
```

If the valid count is still insufficient, use `e06yp2` as the stronger fallback.
