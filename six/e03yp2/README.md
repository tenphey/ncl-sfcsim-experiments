# e03yp2

Stronger calibration follow-up for `e03y`, to use if `e03yp1` still produces
too few valid image-dominant samples.

- Target bucket: `0.32 < NCCR_total <= 0.56`
- Target composition: image-dominant, `CCR_data < IDR_image`
- Analysis composition rule: relative gap at least `20%`
- Purpose: further increase valid samples without locking any random range

Compared with `e03y`, this stronger fallback uses:

- `vnf_datasize_min=285`
- `vnf_datasize_max=570`
- `vnf_image_size_min=265`
- `vnf_image_size_max=530`

The data range is reduced further and the image range is increased further.
This moves the composition more clearly toward image-dominant while keeping
both ranges non-zero. The parameter choice is a calibration attempt; valid
counts must be checked after the run.

Run from the repository root:

```bash
experiments/.venv/bin/python experiments/five/e03yp2/run_experiment.py
```
