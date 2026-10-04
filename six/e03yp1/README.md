# e03yp1

Calibration follow-up for `e03y`.

- Target bucket: `0.32 < NCCR_total <= 0.56`
- Target composition: image-dominant, `CCR_data < IDR_image`
- Analysis composition rule: relative gap at least `20%`
- Purpose: increase valid samples without locking any random range

Compared with `e03y`, this first fallback uses:

- `vnf_datasize_min=320`
- `vnf_datasize_max=645`
- `vnf_image_size_min=255`
- `vnf_image_size_max=505`

The data range is reduced and the image range is increased. This moves the
composition toward image-dominant while keeping both ranges non-zero. The
parameter choice is a calibration attempt; valid counts must be checked after
the run.

Run from the repository root:

```bash
experiments/.venv/bin/python experiments/five/e03yp1/run_experiment.py
```

If the valid count is still insufficient, use `e03yp2` as the stronger fallback.
