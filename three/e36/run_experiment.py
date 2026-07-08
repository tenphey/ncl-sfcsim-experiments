#!/usr/bin/env python3
"""
E36 Experiment: Fixed B36 Scenario (No Variable Sweep)

Runs repeated random-seed trials on experiments/e36/b36.properties,
which targets: 1.78 < NCCR_total <= 3.16 AND CCR_data ~= IDR_image.

Usage:
  python3 run_experiment.py                     # Normal run
  E36_DRY_RUN=1 python3 run_experiment.py       # Dry run (print commands only)
  E36_NUM_SEEDS=10 python3 run_experiment.py    # Use 10 seeds instead of default
"""

import csv
import json
import os
import random
import subprocess
import tempfile
import time
from datetime import datetime

# Configuration
THIS_DIR = os.path.dirname(os.path.abspath(__file__))
THREE_DIR = os.path.dirname(THIS_DIR)
EXPERIMENTS_DIR = os.path.dirname(THREE_DIR)
JAVA_RUNTIME_PROPS = os.path.join(EXPERIMENTS_DIR, "java_runtime.properties")
BASE_PROPS = os.path.join(THIS_DIR, "b36.properties")

DRY_RUN = int(os.getenv("E36_DRY_RUN", "0")) == 1
LIMIT_RUNS = int(os.getenv("E36_LIMIT_RUNS", "0"))

# Seeding
MASTER_SEED = int(os.getenv("E36_MASTER_SEED", "151"))
NUM_SEEDS_DEFAULT = 500
NUM_SEEDS = int(os.getenv("E36_NUM_SEEDS", str(NUM_SEEDS_DEFAULT)))

random.seed(MASTER_SEED)
SEEDS = random.sample(range(1000, 9999), NUM_SEEDS)

TIMEOUT = 120  # seconds per run


def read_props(path):
    """Read properties file into dict."""
    props = {}
    if os.path.exists(path):
        with open(path) as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                if "=" in line:
                    k, v = line.split("=", 1)
                    props[k.strip()] = v.strip()
    return props


def require_prop(props, key):
    value = props.get(key, "").strip()
    if not value:
        raise RuntimeError(f"Missing required property '{key}' in {JAVA_RUNTIME_PROPS}")
    return value


def build_java_cmd_base():
    java_runtime = read_props(JAVA_RUNTIME_PROPS)

    project_root_raw = require_prop(java_runtime, "project_root")
    if os.path.isabs(project_root_raw):
        project_root = os.path.normpath(project_root_raw)
    else:
        project_root = os.path.normpath(os.path.join(EXPERIMENTS_DIR, project_root_raw))

    java_bin = require_prop(java_runtime, "java_bin")
    java_heap = require_prop(java_runtime, "java_heap")
    classes_dir_rel = require_prop(java_runtime, "classes_dir_rel")
    lib_glob_rel = require_prop(java_runtime, "lib_glob_rel")
    main_class = require_prop(java_runtime, "main_class")

    classes_dir = os.path.normpath(os.path.join(project_root, classes_dir_rel))
    lib_glob = os.path.normpath(os.path.join(project_root, lib_glob_rel))

    return [
        java_bin,
        java_heap,
        "-cp",
        f"{classes_dir}:{lib_glob}",
        main_class,
    ]


def write_props(props, path):
    """Write properties dict to file."""
    with open(path, "w") as f:
        for k, v in props.items():
            f.write(f"{k}={v}\n")


def extract_makespans(output):
    """Extract HEFT, DHEFT, NHEFT makespans from Java output."""
    heft = dheft = nheft = None
    for line in output.split("\n"):
        if "[HEFT]makespan" in line and ":" in line:
            try:
                heft = float(line.split(":")[-1].strip())
            except Exception:
                pass
        elif "[DHEFT]makespan" in line and ":" in line:
            try:
                dheft = float(line.split(":")[-1].strip())
            except Exception:
                pass
        elif "[NHEFT]makespan" in line and ":" in line:
            try:
                nheft = float(line.split(":")[-1].strip())
            except Exception:
                pass
    return heft, dheft, nheft


def main():
    java_cmd_base = build_java_cmd_base()
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_dir = os.path.join(THIS_DIR, f"run_{timestamp}_{MASTER_SEED}_{NUM_SEEDS_DEFAULT}")
    os.makedirs(out_dir, exist_ok=True)
    logs_dir = os.path.join(out_dir, "logs")
    os.makedirs(logs_dir, exist_ok=True)

    csv_path = os.path.join(out_dir, "grid_e36_results.csv")
    results = []

    base = read_props(BASE_PROPS)

    total_runs = len(SEEDS)
    run_count = 0

    print("=== E36 Experiment: Fixed B36 Scenario (No Variable Sweep) ===")
    print("Target scenario: 1.78 < NCCR_total <= 3.16 AND CCR_data ~= IDR_image")
    print(f"Master seed: {MASTER_SEED}")
    print(f"Number of seeds: {NUM_SEEDS}")
    print(f"Total runs: {total_runs}")
    if DRY_RUN:
        print("[DRY RUN MODE - will not execute Java]")
    print()

    for s in SEEDS:
        run_count += 1
        if LIMIT_RUNS > 0 and run_count > LIMIT_RUNS:
            print(f"[{run_count}/{total_runs}] Limit reached, stopping.")
            break

        props = base.copy()
        props["random_seed"] = str(s)

        # Write temp properties
        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".properties", mode="w")
        write_props(props, tmp.name)
        tmp.close()

        cmd = java_cmd_base + [tmp.name]

        print(f"[{run_count}/{total_runs}] seed={s}", end="")

        if DRY_RUN:
            print(" [DRY RUN CMD]")
            print(f"  {' '.join(cmd)}")
            heft = dheft = nheft = time_sec = 0
        else:
            try:
                start = time.time()
                result = subprocess.run(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    universal_newlines=True,
                    timeout=TIMEOUT,
                )
                elapsed = time.time() - start
                output = result.stdout

                # Save raw stdout for debugging (one file per run)
                log_name = os.path.join(logs_dir, f"run_seed_{s}.log")
                try:
                    with open(log_name, "w") as lf:
                        lf.write(output)
                except Exception:
                    pass

                heft, dheft, nheft = extract_makespans(output)
                if heft is not None and dheft is not None and nheft is not None:
                    print(f" OK ({elapsed:.1f}s)")
                    time_sec = elapsed
                else:
                    print(f" PARSE ERROR (see {log_name})")
                    heft = dheft = nheft = time_sec = 0
            except subprocess.TimeoutExpired:
                print(" TIMEOUT")
                heft = dheft = nheft = time_sec = 0
            except Exception as e:
                print(f" ERROR: {e}")
                heft = dheft = nheft = time_sec = 0

        results.append(
            {
                "seed": s,
                "HEFT": heft if heft else 0,
                "DHEFT": dheft if dheft else 0,
                "NHEFT": nheft if nheft else 0,
                "time_sec": time_sec,
            }
        )

        # Cleanup temp file
        try:
            os.remove(tmp.name)
        except Exception:
            pass

    # Write results CSV
    with open(csv_path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["seed", "HEFT", "DHEFT", "NHEFT", "time_sec"])
        writer.writeheader()
        writer.writerows(results)

    print(f"\nResults written to: {csv_path}")
    print(f"RESULT_DIR={out_dir}")

    # Write manifest
    manifest = {
        "experiment": "E36 - Fixed B36 Scenario (No Variable Sweep)",
        "scenario": "1.78 < NCCR_total <= 3.16 AND CCR_data ~= IDR_image",
        "timestamp": timestamp,
        "master_seed": MASTER_SEED,
        "num_seeds": NUM_SEEDS,
        "seeds_used": SEEDS,
        "total_runs": len(results),
        "dry_run": DRY_RUN,
    }
    with open(os.path.join(out_dir, "run_manifest.json"), "w") as f:
        json.dump(manifest, f, indent=2)

    # Copy b36 properties snapshot
    if os.path.exists(BASE_PROPS):
        with open(BASE_PROPS) as src:
            content = src.read()
        with open(os.path.join(out_dir, "b36_properties_snapshot.properties"), "w") as dst:
            dst.write(content)

    if os.path.exists(JAVA_RUNTIME_PROPS):
        with open(JAVA_RUNTIME_PROPS) as src:
            content = src.read()
        with open(os.path.join(out_dir, "java_runtime_snapshot.properties"), "w") as dst:
            dst.write(content)


if __name__ == "__main__":
    main()
