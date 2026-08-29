#!/usr/bin/env python3
"""Run all 24 experiments/five scenarios sequentially."""

import argparse
import os
import subprocess
import sys
from pathlib import Path


FIVE_DIR = Path(__file__).resolve().parent
SCENARIOS = [f"e{bucket:02d}{composition}" for bucket in range(1, 9) for composition in "xyz"]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--limit-runs", type=int, default=0, help="Limit each scenario to this many seeds")
    parser.add_argument("--dry-run", action="store_true", help="Print commands without running Java")
    args = parser.parse_args()

    env = os.environ.copy()
    if args.limit_runs:
        env["FIVE_LIMIT_RUNS"] = str(args.limit_runs)
    if args.dry_run:
        env["FIVE_DRY_RUN"] = "1"

    for index, scenario in enumerate(SCENARIOS, start=1):
        script = FIVE_DIR / scenario / "run_experiment.py"
        print(f"\n=== [{index}/{len(SCENARIOS)}] {scenario} ===", flush=True)
        completed = subprocess.run([sys.executable, str(script)], env=env, check=False)
        if completed.returncode != 0:
            raise SystemExit(f"{scenario} failed with exit code {completed.returncode}")


if __name__ == "__main__":
    main()

