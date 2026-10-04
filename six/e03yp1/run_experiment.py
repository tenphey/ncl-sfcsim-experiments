#!/usr/bin/env python3
"""Run e03yp1, a calibrated e03y image-dominant fallback variant."""

import sys
from pathlib import Path

FIVE_DIR = Path(__file__).resolve().parents[1]
if str(FIVE_DIR) not in sys.path:
    sys.path.insert(0, str(FIVE_DIR))

from common_runner import run_scenario


if __name__ == "__main__":
    run_scenario(
        "e03yp1",
        Path(__file__).resolve().parent,
        Path(__file__).resolve().parent / "b03yp1.properties",
    )
