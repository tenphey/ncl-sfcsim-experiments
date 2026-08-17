#!/usr/bin/env python3
"""Count latest raw-result rows for the full e3-series experiments.

This script scans experiments/four/e31x ... e38z, picks the latest `run_*`
directory in each experiment folder, counts the number of data rows in the
corresponding `*_results.csv`, and prints a compact command-line report such as:

e31x: 2000
e31y: 2000
...
TOTAL: 48000
"""

from __future__ import annotations

import csv
from pathlib import Path


THIS_DIR = Path(__file__).resolve().parent
FOUR_DIR = THIS_DIR.parent


def iter_experiment_codes():
    for bucket in range(1, 9):
        for suffix in ("x", "y", "z"):
            yield f"e3{bucket}{suffix}"


def latest_run_dir(experiment_dir: Path) -> Path | None:
    run_dirs = sorted(
        path for path in experiment_dir.iterdir() if path.is_dir() and path.name.startswith("run_")
    )
    return run_dirs[-1] if run_dirs else None


def count_csv_rows(csv_path: Path) -> int:
    with csv_path.open(newline="", encoding="utf-8") as source:
        reader = csv.DictReader(source)
        return sum(1 for _ in reader)


def main():
    total = 0

    for experiment_code in iter_experiment_codes():
        experiment_dir = FOUR_DIR / experiment_code
        run_dir = latest_run_dir(experiment_dir)

        if run_dir is None:
            print(f"{experiment_code}: 0 [no run]")
            continue

        csv_path = run_dir / f"{experiment_code}_results.csv"
        if not csv_path.is_file():
            print(f"{experiment_code}: 0 [missing csv]")
            continue

        row_count = count_csv_rows(csv_path)
        total += row_count
        print(f"{experiment_code}: {row_count}")

    print(f"TOTAL: {total}")


if __name__ == "__main__":
    main()
