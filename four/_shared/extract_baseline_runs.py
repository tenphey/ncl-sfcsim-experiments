#!/usr/bin/env python3
"""Extract baseline rows from combined e1-series results into shared e0 runs.

This utility is intended for the experiments/four workflow after the baseline
side was split out conceptually, but the older e1-series runs still contain:

- baseline NHEFT
- gated GHEFT (comp-only for e1)

Instead of rerunning the shared baseline scenarios, we can reuse the baseline
rows that already exist inside the combined CSVs.
"""

from __future__ import annotations

import csv
import json
import os
from collections import Counter
from datetime import datetime
from typing import Iterable


SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
FOUR_DIR = os.path.dirname(SCRIPT_DIR)


MAPPINGS = [
    ("e11x", "e01x"),
    ("e12x", "e02x"),
    ("e13x", "e03x"),
    ("e14x", "e04x"),
    ("e15x", "e05x"),
    ("e16x", "e06x"),
    ("e17x", "e07x"),
    ("e18x", "e08x"),
    ("e11y", "e01y"),
    ("e12y", "e02y"),
    ("e13y", "e03y"),
    ("e14y", "e04y"),
    ("e15y", "e05y"),
    ("e16y", "e06y"),
    ("e17y", "e07y"),
    ("e18y", "e08y"),
    ("e11z", "e01z"),
    ("e12z", "e02z"),
    ("e13z", "e03z"),
    ("e14z", "e04z"),
    ("e15z", "e05z"),
    ("e16z", "e06z"),
    ("e17z", "e07z"),
    ("e18z", "e08z"),
]


def read_json(path: str) -> dict:
    with open(path, encoding="utf-8") as source:
        return json.load(source)


def write_json(path: str, payload: dict) -> None:
    with open(path, "w", encoding="utf-8") as target:
        json.dump(payload, target, indent=2)
        target.write("\n")


def find_latest_source_run(experiment_code: str) -> str:
    experiment_dir = os.path.join(FOUR_DIR, experiment_code)
    candidates = []
    for name in os.listdir(experiment_dir):
        path = os.path.join(experiment_dir, name)
        if not name.startswith("run_") or not os.path.isdir(path):
            continue
        csv_path = os.path.join(path, f"{experiment_code}_results.csv")
        manifest_path = os.path.join(path, "run_manifest.json")
        if not os.path.isfile(csv_path) or not os.path.isfile(manifest_path):
            continue
        manifest = read_json(manifest_path)
        if int(manifest.get("completed_runs", 0)) <= 0:
            continue
        candidates.append(path)

    if not candidates:
        raise FileNotFoundError(f"No reusable run directory found for {experiment_code}")
    return sorted(candidates)[-1]


def load_baseline_rows(csv_path: str) -> tuple[list[dict], list[str]]:
    with open(csv_path, newline="", encoding="utf-8") as source:
        reader = csv.DictReader(source)
        fieldnames = reader.fieldnames or []
        rows = [row for row in reader if str(row.get("variant", "")).strip() == "baseline"]

    if not rows:
        raise RuntimeError(f"No baseline rows found in {csv_path}")
    return rows, fieldnames


def build_target_manifest(
    target_code: str,
    source_code: str,
    source_run_dir: str,
    source_manifest: dict,
    rows: Iterable[dict],
) -> dict:
    rows = list(rows)
    status_counts = Counter(str(row.get("status", "")).strip() or "unknown" for row in rows)
    seeds = [int(row["seed"]) for row in rows if str(row.get("seed", "")).strip()]
    source_base = os.path.relpath(source_run_dir, FOUR_DIR)
    baseline_variant = {
        "label": "baseline",
        "display_label": "NHEFT",
        "tolerance": "0.0",
        "comp_advantage": "0",
        "drt_advantage": "0",
        "irt_advantage": "0",
        "description": "Extracted shared baseline rows from the older combined e1-series run.",
    }
    return {
        "experiment": target_code.upper(),
        "purpose": (
            f"Shared baseline extracted from {source_code.upper()} to avoid rerunning "
            "HEFT/DHEFT/NHEFT for the same communication scenario."
        ),
        "timestamp": datetime.now().strftime("%Y%m%d_%H%M%S"),
        "project_root": source_manifest.get("project_root"),
        "base_properties": source_manifest.get("base_properties"),
        "java_runtime_properties": source_manifest.get("java_runtime_properties"),
        "master_seed": source_manifest.get("master_seed"),
        "num_seeds": len(rows),
        "seeds_used": seeds,
        "variants": [baseline_variant],
        "loop_order": "extracted_from_combined_e1_run",
        "total_planned_runs": len(rows),
        "completed_runs": len(rows),
        "status_counts": dict(status_counts),
        "dry_run": False,
        "timeout_seconds": source_manifest.get("timeout_seconds"),
        "interrupted": False,
        "source_experiment": source_code.upper(),
        "source_run_dir": source_base,
        "source_variants": [
            item.get("label")
            for item in (source_manifest.get("variants") or [])
            if isinstance(item, dict)
        ],
    }


def ensure_parent(path: str) -> None:
    os.makedirs(path, exist_ok=True)


def copy_if_exists(src: str, dst: str) -> None:
    if os.path.isfile(src):
        with open(src, "rb") as source, open(dst, "wb") as target:
            target.write(source.read())


def copy_logs_dir(source_run_dir: str, target_run_dir: str) -> None:
    source_logs = os.path.join(source_run_dir, "logs")
    target_logs = os.path.join(target_run_dir, "logs")
    if not os.path.isdir(source_logs):
        return
    if os.path.isdir(target_logs):
        return
    os.makedirs(target_logs, exist_ok=True)
    for name in os.listdir(source_logs):
        src = os.path.join(source_logs, name)
        dst = os.path.join(target_logs, name)
        if os.path.isfile(src):
            with open(src, "rb") as source, open(dst, "wb") as target:
                target.write(source.read())


def main() -> None:
    extraction_timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    for source_code, target_code in MAPPINGS:
        source_run_dir = find_latest_source_run(source_code)
        source_csv = os.path.join(source_run_dir, f"{source_code}_results.csv")
        source_manifest = read_json(os.path.join(source_run_dir, "run_manifest.json"))
        rows, fieldnames = load_baseline_rows(source_csv)

        target_experiment_dir = os.path.join(FOUR_DIR, target_code)
        ensure_parent(target_experiment_dir)

        master_seed = source_manifest.get("master_seed", "151")
        target_run_dir = os.path.join(
            target_experiment_dir,
            f"run_{extraction_timestamp}_{master_seed}_{len(rows)}",
        )
        ensure_parent(target_run_dir)
        copy_logs_dir(source_run_dir, target_run_dir)

        target_csv = os.path.join(target_run_dir, f"{target_code}_results.csv")
        for row in rows:
            source_log_rel = str(row.get("log_file", "")).strip()
            if source_log_rel and source_log_rel.startswith("logs/"):
                row["log_file"] = source_log_rel

        with open(target_csv, "w", newline="", encoding="utf-8") as target:
            writer = csv.DictWriter(target, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)

        manifest = build_target_manifest(
            target_code=target_code,
            source_code=source_code,
            source_run_dir=source_run_dir,
            source_manifest=source_manifest,
            rows=rows,
        )
        write_json(os.path.join(target_run_dir, "run_manifest.json"), manifest)

        copy_if_exists(
            os.path.join(source_run_dir, "base_properties_snapshot.properties"),
            os.path.join(target_run_dir, "base_properties_snapshot.properties"),
        )
        copy_if_exists(
            os.path.join(source_run_dir, "java_runtime_snapshot.properties"),
            os.path.join(target_run_dir, "java_runtime_snapshot.properties"),
        )

        note_path = os.path.join(target_run_dir, "EXTRACTION_NOTE.md")
        with open(note_path, "w", encoding="utf-8") as note:
            note.write(f"# Extracted Baseline Run for {target_code.upper()}\n\n")
            note.write(
                f"- Source experiment: `{source_code}`\n"
                f"- Source run: `{os.path.relpath(source_run_dir, FOUR_DIR)}`\n"
                f"- Extracted rows: `{len(rows)}` baseline rows only\n"
                "- Reason: reuse existing HEFT/DHEFT/NHEFT results without rerunning the shared baseline side\n"
            )

        print(
            f"{source_code} -> {target_code}: extracted {len(rows)} baseline rows "
            f"into {os.path.relpath(target_run_dir, FOUR_DIR)}"
        )


if __name__ == "__main__":
    main()
