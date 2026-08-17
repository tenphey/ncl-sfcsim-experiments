#!/usr/bin/env python3
"""Standalone GHEFT runner for E22Z."""

import os
import sys

THIS_DIR = os.path.dirname(os.path.abspath(__file__))
FOUR_DIR = os.path.dirname(THIS_DIR)
SHARED_DIR = os.path.join(FOUR_DIR, "_shared")
if SHARED_DIR not in sys.path:
    sys.path.insert(0, SHARED_DIR)

from single_gheft_mode_runner import run_single_gheft_experiment


GATE_VARIANT = {
    "label": "drt_only",
    "display_label": "GHEFT",
    "tolerance": "0.0",
    "comp_advantage": "0",
    "drt_advantage": "1",
    "irt_advantage": "0",
    "gate_logic": "all",
    "description": "Run only GHEFT with the DRT-only opening gate under the shared E02Z scenario.",
}


if __name__ == "__main__":
    run_single_gheft_experiment(
        experiment_dir=THIS_DIR,
        experiment_code="e22z",
        raw_csv_name="e22z_results.csv",
        base_properties_path=os.path.join(FOUR_DIR, "e02z", "b02z.properties"),
        gate_variant=GATE_VARIANT,
        purpose=(
            "Standalone GHEFT run for E22Z using the shared "
            "E02Z communication scenario. Shared HEFT/DHEFT/NHEFT baselines should be "
            "taken from the corresponding common scenario run."
        ),
    )
