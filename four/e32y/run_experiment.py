#!/usr/bin/env python3
"""Standalone GHEFT runner for E32Y."""

import os
import sys

THIS_DIR = os.path.dirname(os.path.abspath(__file__))
FOUR_DIR = os.path.dirname(THIS_DIR)
SHARED_DIR = os.path.join(FOUR_DIR, "_shared")
if SHARED_DIR not in sys.path:
    sys.path.insert(0, SHARED_DIR)

from single_gheft_mode_runner import run_single_gheft_experiment


GATE_VARIANT = {
    "label": "irt_only",
    "display_label": "GHEFT",
    "tolerance": "0.0",
    "comp_advantage": "0",
    "drt_advantage": "0",
    "irt_advantage": "1",
    "gate_logic": "all",
    "description": "Run only GHEFT with the IRT-only opening gate under the shared E02Y scenario.",
}


if __name__ == "__main__":
    run_single_gheft_experiment(
        experiment_dir=THIS_DIR,
        experiment_code="e32y",
        raw_csv_name="e32y_results.csv",
        base_properties_path=os.path.join(FOUR_DIR, "e02y", "b02y.properties"),
        gate_variant=GATE_VARIANT,
        purpose=(
            "Standalone GHEFT run for E32Y using the shared "
            "E02Y communication scenario. Shared HEFT/DHEFT/NHEFT baselines should be "
            "taken from the corresponding common scenario run."
        ),
    )
