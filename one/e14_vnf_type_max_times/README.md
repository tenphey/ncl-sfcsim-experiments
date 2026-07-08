# E14: Task-Type Diversity with Controlled Repetition Density — H3a Verification

**Advisor's requirement**: when the number of task types increases, the total number of tasks should also increase accordingly.

So E14 should **not** keep total task count fixed. Instead, it should increase `vnf_type_max` and `sfc_vnf_num` together so that the expected number of tasks per type stays constant.

## Design

### Variables
- `vnf_type_max ∈ {4, 8, 12, 20}`
- `sfc_vnf_num = 10 × vnf_type_max`
- `expected_tasks_per_type = sfc_vnf_num / vnf_type_max = 10` (constant)

### Fixed
- `repository_bw = 120` MBps
- `vnf_image_size_min = 2400`, `vnf_image_size_max = 6200`
- `multiple_sfc_num = 1`

### Seeds
- 50 per type level
- Total: 4 levels × 50 = 200 runs

## Expected Pattern

Because `expected_tasks_per_type` is kept constant, the experiment isolates the effect of **type diversity itself** rather than the confounder of reduced repetition density.

Expected behavior:

1. `vnf_type_max` increases
2. `sfc_vnf_num` increases proportionally
3. the repetition density per type remains roughly unchanged
4. NHEFT's gain should therefore remain **stable** or change only mildly

This is the “fair” version of the task-type experiment.

**Predicted visualization**: line plot or grouped bar chart showing a **stable or mildly changing trend** in gain %.

## Outputs
- `grid_e14_results.csv` (raw data)
- `grid_e14_summary.csv` (aggregated)
- `e14_type_diversity_fixed_tasks.png` (line plot)

## Key Insight
E14 follows the advisor's comment directly: higher task-type counts must be accompanied by more total tasks. That way, we do **not** unintentionally reduce the number of repeated tasks per type while studying type diversity.

In short:

- **Independent variable**: `vnf_type_max`
- **Controlled scaling**: `sfc_vnf_num = 10 × vnf_type_max`
- **What it tests**: whether type diversity alone changes NHEFT's advantage when repetition density is held constant

