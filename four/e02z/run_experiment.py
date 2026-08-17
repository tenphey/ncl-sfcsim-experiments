#!/usr/bin/env python3
"""Shared baseline runner for E02Z."""

import os
import sys

THIS_DIR = os.path.dirname(os.path.abspath(__file__))
FOUR_DIR = os.path.dirname(THIS_DIR)
SHARED_DIR = os.path.join(FOUR_DIR, "_shared")
if SHARED_DIR not in sys.path:
    sys.path.insert(0, SHARED_DIR)

from single_baseline_mode_runner import run_single_baseline_experiment


if __name__ == "__main__":
    run_single_baseline_experiment(
        experiment_dir=THIS_DIR,
        experiment_code="e02z",
        raw_csv_name="e02z_results.csv",
        base_properties_path=os.path.join(THIS_DIR, "b02z.properties"),
        purpose=(
            "Shared baseline run for E02Z. "
            "This scenario provides the common HEFT/DHEFT/NHEFT reference side "
            "for the corresponding gated experiments in experiments/four."
        ),
    )
