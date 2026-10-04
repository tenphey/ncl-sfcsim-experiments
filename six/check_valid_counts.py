#!/usr/bin/env python3
"""Count currently valid seeds in the newest five-series run directory.

This checker is intentionally read-only.  It can inspect a completed run or
an active run; an incomplete final CSV row is simply not counted.
"""

import argparse
import csv
import math
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
TARGET_SEED_COUNT = 500
PRIMARY_SCENARIOS = [
    f"e{bucket:02d}{composition}"
    for bucket in range(1, 9)
    for composition in "xyz"
]
# Calibration fallbacks are checked by default together with the 24 primary scenarios.
SCENARIOS = PRIMARY_SCENARIOS + ["e03yp1", "e03yp2", "e04yp1", "e04yp2", "e06yp1", "e06yp2"]

BUCKETS = (
    (0.10, 0.18),
    (0.18, 0.32),
    (0.32, 0.56),
    (0.56, 1.00),
    (1.00, 1.78),
    (1.78, 3.16),
    (3.16, 5.62),
    (5.62, 10.00),
)

REQUIRED_FIELDS = (
    "seed",
    "ccr_data",
    "idr_image",
    "nccr_total",
    "dheft_makespan",
    "nheft_makespan",
    "gheft_makespan",
    "dheft_vcpus",
    "nheft_vcpus",
    "gheft_vcpus",
)

INVALID_REASON_LABELS = (
    "not_ok",
    "incomplete_or_non_numeric",
    "nccr_out_of_bucket",
    "composition_mismatch",
)

COMPOSITION_LABELS = {
    "x": "balanced",
    "y": "image_dominant",
    "z": "data_dominant",
}


def parse_number(value):
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) else None


def relative_gap_percent(ccr, idr):
    denominator = (ccr + idr) / 2.0
    if denominator <= 0:
        return None
    return abs(ccr - idr) / denominator * 100.0


def parse_required_values(row):
    """Return the communication values when the row is complete and numeric."""
    if any(not (row.get(field) or "").strip() for field in REQUIRED_FIELDS):
        return None
    if any(parse_number(row.get(field)) is None for field in REQUIRED_FIELDS[1:]):
        return None

    ccr = parse_number(row.get("ccr_data"))
    idr = parse_number(row.get("idr_image"))
    nccr = parse_number(row.get("nccr_total"))
    if ccr is None or idr is None or nccr is None:
        return None
    return ccr, idr, nccr


def composition_class(ccr, idr):
    """Classify a row using the same x/y/z rules as the five-series analysis."""
    gap = relative_gap_percent(ccr, idr)
    if gap is None:
        return None
    if gap <= 10.0:
        return "x"
    if ccr < idr and gap >= 20.0:
        return "y"
    if ccr > idr and gap >= 20.0:
        return "z"
    return None


def in_scenario_bucket(nccr, scenario):
    bucket_index = int(scenario[1:3]) - 1
    lower, upper = BUCKETS[bucket_index]
    return lower < nccr <= upper


def classify_row(row, scenario):
    """Return the first reason why a row is not included in valid seeds."""
    if (row.get("status") or "").strip().lower() != "ok":
        return "not_ok"

    values = parse_required_values(row)
    if values is None:
        return "incomplete_or_non_numeric"

    ccr, idr, nccr = values
    if not in_scenario_bucket(nccr, scenario):
        return "nccr_out_of_bucket"

    return "valid" if composition_class(ccr, idr) == scenario[3] else "composition_mismatch"


def is_valid_row(row, scenario):
    return classify_row(row, scenario) == "valid"


def latest_run_dir(scenario, target_seed_count):
    scenario_dir = SCRIPT_DIR / scenario
    candidates = []
    suffix = f"_{target_seed_count}"
    for path in scenario_dir.glob("run_*"):
        if path.is_dir() and path.name.endswith(suffix):
            csv_path = path / f"{scenario}_results.csv"
            if csv_path.is_file():
                # The timestamp in the standard run directory name is sortable.
                candidates.append((path.name, path, csv_path))
    return max(candidates, key=lambda item: item[0]) if candidates else None


def count_valid_rows(csv_path, scenario):
    raw_rows = ok_rows = 0
    reason_counts = {"valid": 0, **{reason: 0 for reason in INVALID_REASON_LABELS}}
    invalid_seeds = {reason: [] for reason in INVALID_REASON_LABELS}
    valid_seeds = set()
    same_bucket_compositions = {composition: 0 for composition in "xyz"}
    same_bucket_compositions["unclassified"] = 0
    try:
        with csv_path.open("r", encoding="utf-8", newline="") as handle:
            reader = csv.DictReader(handle)
            for row in reader:
                raw_rows += 1
                if (row.get("status") or "").strip().lower() == "ok":
                    ok_rows += 1
                reason = classify_row(row, scenario)
                reason_counts[reason] += 1
                if reason == "valid":
                    valid_seeds.add(row.get("seed", "").strip())
                if reason not in {"not_ok", "incomplete_or_non_numeric", "nccr_out_of_bucket"}:
                    values = parse_required_values(row)
                    composition = composition_class(values[0], values[1])
                    same_bucket_compositions[composition or "unclassified"] += 1
                if reason != "valid":
                    invalid_seeds[reason].append(row.get("seed", "").strip() or "<missing>")
    except (OSError, csv.Error) as exc:
        return None, str(exc)

    valid_rows = reason_counts["valid"]
    duplicate_count = valid_rows - len(valid_seeds)
    return {
        "raw_rows": raw_rows,
        "ok_rows": ok_rows,
        "valid_rows": valid_rows,
        "valid_unique_seeds": len(valid_seeds),
        "duplicate_count": duplicate_count,
        "reason_counts": reason_counts,
        "same_bucket_compositions": same_bucket_compositions,
        "invalid_seeds": invalid_seeds,
    }, None


def main():
    parser = argparse.ArgumentParser(description="Count valid seeds in the latest five-series runs.")
    parser.add_argument(
        "--seed-count",
        type=int,
        default=TARGET_SEED_COUNT,
        help=f"Only inspect run directories ending in _N (default: {TARGET_SEED_COUNT}).",
    )
    parser.add_argument(
        "--show-invalid-seeds",
        action="store_true",
        help="Also print the seed IDs grouped by invalid reason.",
    )
    parser.add_argument(
        "--scenario",
        action="append",
        dest="scenarios",
        help=(
            "Inspect a specific scenario directory instead of the default scenario set; "
            "may be repeated, for example --scenario e04yp1."
        ),
    )
    args = parser.parse_args()

    scenarios = args.scenarios or SCENARIOS
    print(f"Latest run per scenario (target seeds: {args.seed_count}; read-only):")
    for scenario in scenarios:
        if len(scenario) < 4 or scenario[3] not in COMPOSITION_LABELS:
            print(f"{scenario}: invalid scenario name; expected eNNx/eNNy/eNNz or eNNypN")
            continue
        selected = latest_run_dir(scenario, args.seed_count)
        if selected is None:
            print(f"{scenario}: no matching run")
            continue

        run_name, _, csv_path = selected
        counts, error = count_valid_rows(csv_path, scenario)
        if error:
            print(f"{scenario}: read error: {error} / {run_name}")
            continue

        raw_rows = counts["raw_rows"]
        ok_rows = counts["ok_rows"]
        valid_rows = counts["valid_rows"]
        duplicate_count = counts["duplicate_count"]
        reasons = counts["reason_counts"]
        compositions = counts["same_bucket_compositions"]
        target = scenario[3]
        other_compositions = [composition for composition in "xyz" if composition != target]
        invalid_total = raw_rows - valid_rows
        print(
            f"{scenario}: valid={valid_rows} / ok={ok_rows} / raw={raw_rows}"
            f" / other_{COMPOSITION_LABELS[other_compositions[0]]}={compositions[other_compositions[0]]}"
            f" / other_{COMPOSITION_LABELS[other_compositions[1]]}={compositions[other_compositions[1]]}"
            f" / same_bucket_unclassified={compositions['unclassified']}"
            f" / invalid={invalid_total}"
            f" / not_ok={reasons['not_ok']}"
            f" / incomplete={reasons['incomplete_or_non_numeric']}"
            f" / nccr_out={reasons['nccr_out_of_bucket']}"
            f" / composition_mismatch={reasons['composition_mismatch']}"
            f" / {run_name}"
        )
        if args.show_invalid_seeds:
            for reason in INVALID_REASON_LABELS:
                seeds = counts["invalid_seeds"][reason]
                if seeds:
                    print(f"  {reason}: {', '.join(seeds)}")


if __name__ == "__main__":
    main()
