#!/usr/bin/env python3
"""Generate paired data for the NHEFT vCPU EFT-tolerance sweep.

For every random seed, this runner executes the same simulator input with
``nheft_vcpu_eft_tolerance`` set to 0.0, 0.1, ..., 1.0.  The 0.0 run is the
original NHEFT baseline; positive values enable the already-used-vCPU
preference.  HEFT and DHEFT are also recorded from every invocation.

The script only generates raw logs and a long-format CSV.  Analysis and plots
belong in a separate script so that raw experiment data are never modified.

Run from the simulator repository root, for example:

  experiments/.venv/bin/python \
      experiments/four/e0_nheft_vcpu_tolerance/run_experiment.py

Useful environment variables:

  E0_NUM_SEEDS=5       Run five paired seeds instead of the default 500.
  E0_MASTER_SEED=151   Change the deterministic seed list.
  E0_LIMIT_RUNS=2      Stop after two Java invocations (smoke testing).
  E0_DRY_RUN=1         Print commands without launching Java.
  E0_TIMEOUT=180       Timeout in seconds for each Java invocation.
  E0_TOLERANCES=0,0.1  Override the tolerance grid when debugging.
  E0_BASE_PROPERTIES=/absolute/path/to/file.properties
                       Override the default <project_root>/nheft.properties.
"""

import csv
import json
import os
import random
import re
import shlex
import shutil
import subprocess
import tempfile
import time
from collections import Counter
from datetime import datetime
from decimal import Decimal, InvalidOperation


THIS_DIR = os.path.dirname(os.path.abspath(__file__))
FOUR_DIR = os.path.dirname(THIS_DIR)
EXPERIMENTS_DIR = os.path.dirname(FOUR_DIR)
JAVA_RUNTIME_PROPS = os.path.join(EXPERIMENTS_DIR, "java_runtime.properties")

DEFAULT_TOLERANCES = [f"{i / 10:.1f}" for i in range(11)]
NUM_SEEDS_DEFAULT = 50
MASTER_SEED = int(os.getenv("E0_MASTER_SEED", "151"))
NUM_SEEDS = int(os.getenv("E0_NUM_SEEDS", str(NUM_SEEDS_DEFAULT)))
LIMIT_RUNS = int(os.getenv("E0_LIMIT_RUNS", "0"))
DRY_RUN = os.getenv("E0_DRY_RUN", "0") == "1"
TIMEOUT = int(os.getenv("E0_TIMEOUT", "180"))


CSV_FIELDS = [
    "seed",
    "tolerance",
    "is_original_nheft",
    "configured_tolerance",
    "ccr_data",
    "idr_image",
    "nccr_total",
    "heft_makespan",
    "heft_slr",
    "heft_vcpus",
    "heft_hosts",
    "heft_instances",
    "heft_image_dl_total",
    "heft_image_from_repo",
    "heft_image_from_host",
    "dheft_makespan",
    "dheft_slr",
    "dheft_vcpus",
    "dheft_hosts",
    "dheft_instances",
    "dheft_image_dl_total",
    "dheft_image_from_repo",
    "dheft_image_from_host",
    "nheft_makespan",
    "nheft_slr",
    "nheft_vcpus",
    "nheft_hosts",
    "nheft_instances",
    "nheft_image_dl_total",
    "nheft_image_from_repo",
    "nheft_image_from_host",
    "time_sec",
    "return_code",
    "status",
    "log_file",
]


MAKESPAN_RE = re.compile(
    r"^\[(HEFT|DHEFT|NHEFT)\]makespan:\s*([-+0-9.eE]+)\s*$"
)
RESOURCE_RE = re.compile(
    r"^\[(HEFT|DHEFT|NHEFT)\]SLR:\s*([-+0-9.eE]+)\s*"
    r"/\s*# of vCPUs:\s*(\d+)\s*"
    r"/\s*# of Hosts:\s*(\d+)\s*"
    r"/\s*# of Ins:\s*(\d+)\s*$"
)
IMAGE_RE = re.compile(
    r"^\[(HEFT|DHEFT|NHEFT)\]imageDL_total=(\d+)\s*"
    r"/\s*fromRepo=(\d+)\s*"
    r"/\s*fromHost=(\d+)\s*$"
)
COMMUNICATION_RE = re.compile(
    r"^CCR_data:\s*([-+0-9.eE]+)\s*"
    r"/\s*IDR_image:\s*([-+0-9.eE]+)\s*"
    r"/\s*NCCR_total:\s*([-+0-9.eE]+)\s*$"
)
CONFIG_TOLERANCE_RE = re.compile(
    r"(?:^|\s/\s)nheft_vcpu_eft_tolerance=([-+0-9.eE]+)(?:\s/\s|$)"
)


def read_props(path):
    """Read a Java properties file into an insertion-ordered dict."""
    props = {}
    with open(path, encoding="utf-8") as source:
        for raw_line in source:
            line = raw_line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            props[key.strip()] = value.strip()
    return props


def require_prop(props, key, source_path):
    value = props.get(key, "").strip()
    if not value:
        raise RuntimeError(f"Missing required property '{key}' in {source_path}")
    return value


def write_props(props, path):
    """Write effective simulator properties used by one Java invocation."""
    with open(path, "w", encoding="utf-8") as target:
        for key, value in props.items():
            target.write(f"{key}={value}\n")


def parse_tolerances():
    raw_value = os.getenv("E0_TOLERANCES")
    values = DEFAULT_TOLERANCES if raw_value is None else raw_value.split(",")
    normalized = []
    seen = set()
    for raw in values:
        value = raw.strip()
        if not value:
            continue
        try:
            decimal_value = Decimal(value)
        except InvalidOperation as exc:
            raise ValueError(f"Invalid tolerance '{value}'") from exc
        if not decimal_value.is_finite() or decimal_value < 0:
            raise ValueError(f"Tolerance must be finite and non-negative: {value}")
        canonical = format(decimal_value, "f")
        if "." not in canonical:
            canonical += ".0"
        if canonical not in seen:
            normalized.append(canonical)
            seen.add(canonical)
    if not normalized:
        raise ValueError("The tolerance grid is empty")
    return normalized


def resolve_runtime():
    runtime = read_props(JAVA_RUNTIME_PROPS)
    project_root_raw = require_prop(runtime, "project_root", JAVA_RUNTIME_PROPS)
    if os.path.isabs(project_root_raw):
        project_root = os.path.normpath(project_root_raw)
    else:
        project_root = os.path.normpath(
            os.path.join(EXPERIMENTS_DIR, project_root_raw)
        )

    java_bin = require_prop(runtime, "java_bin", JAVA_RUNTIME_PROPS)
    java_heap = require_prop(runtime, "java_heap", JAVA_RUNTIME_PROPS)
    classes_dir_rel = require_prop(runtime, "classes_dir_rel", JAVA_RUNTIME_PROPS)
    lib_glob_rel = require_prop(runtime, "lib_glob_rel", JAVA_RUNTIME_PROPS)
    main_class = require_prop(runtime, "main_class", JAVA_RUNTIME_PROPS)

    classes_dir = os.path.normpath(os.path.join(project_root, classes_dir_rel))
    lib_glob = os.path.normpath(os.path.join(project_root, lib_glob_rel))
    java_command = [java_bin] + shlex.split(java_heap) + [
        "-cp",
        f"{classes_dir}:{lib_glob}",
        main_class,
    ]
    return project_root, java_command


def resolve_base_properties(project_root):
    override = os.getenv("E0_BASE_PROPERTIES")
    if override:
        path = override if os.path.isabs(override) else os.path.abspath(override)
    else:
        path = os.path.join(project_root, "nheft.properties")
    path = os.path.normpath(path)
    if not os.path.isfile(path):
        raise FileNotFoundError(f"Base properties file not found: {path}")
    return path


def make_seed_list():
    if NUM_SEEDS <= 0:
        raise ValueError("E0_NUM_SEEDS must be positive")
    population = range(1000, 1000000)
    if NUM_SEEDS > len(population):
        raise ValueError("E0_NUM_SEEDS is larger than the available seed range")
    return random.Random(MASTER_SEED).sample(population, NUM_SEEDS)


def empty_algorithm_metrics():
    metrics = {}
    for algorithm in ("heft", "dheft", "nheft"):
        metrics.update(
            {
                f"{algorithm}_makespan": None,
                f"{algorithm}_slr": None,
                f"{algorithm}_vcpus": None,
                f"{algorithm}_hosts": None,
                f"{algorithm}_instances": None,
                f"{algorithm}_image_dl_total": None,
                f"{algorithm}_image_from_repo": None,
                f"{algorithm}_image_from_host": None,
            }
        )
    return metrics


def parse_output(output):
    parsed = {
        "configured_tolerance": None,
        "ccr_data": None,
        "idr_image": None,
        "nccr_total": None,
    }
    parsed.update(empty_algorithm_metrics())

    for raw_line in output.splitlines():
        line = raw_line.strip()

        config_match = CONFIG_TOLERANCE_RE.search(line)
        if config_match:
            parsed["configured_tolerance"] = float(config_match.group(1))
            continue

        communication_match = COMMUNICATION_RE.match(line)
        if communication_match:
            parsed["ccr_data"] = float(communication_match.group(1))
            parsed["idr_image"] = float(communication_match.group(2))
            parsed["nccr_total"] = float(communication_match.group(3))
            continue

        makespan_match = MAKESPAN_RE.match(line)
        if makespan_match:
            algorithm = makespan_match.group(1).lower()
            parsed[f"{algorithm}_makespan"] = float(makespan_match.group(2))
            continue

        resource_match = RESOURCE_RE.match(line)
        if resource_match:
            algorithm = resource_match.group(1).lower()
            parsed[f"{algorithm}_slr"] = float(resource_match.group(2))
            parsed[f"{algorithm}_vcpus"] = int(resource_match.group(3))
            parsed[f"{algorithm}_hosts"] = int(resource_match.group(4))
            parsed[f"{algorithm}_instances"] = int(resource_match.group(5))
            continue

        image_match = IMAGE_RE.match(line)
        if image_match:
            algorithm = image_match.group(1).lower()
            parsed[f"{algorithm}_image_dl_total"] = int(image_match.group(2))
            parsed[f"{algorithm}_image_from_repo"] = int(image_match.group(3))
            parsed[f"{algorithm}_image_from_host"] = int(image_match.group(4))

    return parsed


def has_required_metrics(parsed):
    required = [
        "configured_tolerance",
        "ccr_data",
        "idr_image",
        "nccr_total",
        "heft_makespan",
        "heft_vcpus",
        "dheft_makespan",
        "dheft_vcpus",
        "nheft_makespan",
        "nheft_vcpus",
    ]
    return all(parsed.get(key) is not None for key in required)


def tolerance_slug(tolerance):
    return tolerance.replace("-", "minus_").replace(".", "_")


def write_manifest(path, manifest):
    temporary_path = path + ".tmp"
    with open(temporary_path, "w", encoding="utf-8") as target:
        json.dump(manifest, target, indent=2)
        target.write("\n")
    os.replace(temporary_path, path)


def main():
    project_root, java_command = resolve_runtime()
    base_properties_path = resolve_base_properties(project_root)
    base_properties = read_props(base_properties_path)
    tolerances = parse_tolerances()
    seeds = make_seed_list()

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_dir = os.path.join(
        THIS_DIR, f"run_{timestamp}_{MASTER_SEED}_{NUM_SEEDS}"
    )
    logs_dir = os.path.join(output_dir, "logs")
    os.makedirs(logs_dir, exist_ok=True)

    csv_path = os.path.join(output_dir, "e0_tolerance_results.csv")
    manifest_path = os.path.join(output_dir, "run_manifest.json")
    total_planned_runs = len(seeds) * len(tolerances)
    statuses = Counter()
    completed_runs = 0
    interrupted = False

    manifest = {
        "experiment": "E0 - NHEFT vCPU EFT-tolerance sweep",
        "purpose": (
            "Compare HEFT, DHEFT, original NHEFT (tolerance=0.0), and "
            "resource-consolidating NHEFT tolerance variants"
        ),
        "timestamp": timestamp,
        "project_root": project_root,
        "base_properties": base_properties_path,
        "java_runtime_properties": JAVA_RUNTIME_PROPS,
        "master_seed": MASTER_SEED,
        "num_seeds": NUM_SEEDS,
        "seeds_used": seeds,
        "tolerances": tolerances,
        "loop_order": "seed_then_tolerance",
        "total_planned_runs": total_planned_runs,
        "completed_runs": 0,
        "status_counts": {},
        "dry_run": DRY_RUN,
        "timeout_seconds": TIMEOUT,
        "interrupted": False,
    }
    write_manifest(manifest_path, manifest)

    shutil.copy2(
        base_properties_path,
        os.path.join(output_dir, "nheft_base_snapshot.properties"),
    )
    shutil.copy2(
        JAVA_RUNTIME_PROPS,
        os.path.join(output_dir, "java_runtime_snapshot.properties"),
    )

    print("=== E0: NHEFT vCPU EFT-Tolerance Sweep ===")
    print(f"Base properties: {base_properties_path}")
    print(f"Master seed: {MASTER_SEED}")
    print(f"Number of paired seeds: {NUM_SEEDS}")
    print(f"Tolerances: {', '.join(tolerances)}")
    print(f"Total Java runs: {total_planned_runs}")
    print("Baseline: tolerance=0.0 (original NHEFT)")
    if DRY_RUN:
        print("[DRY RUN MODE - Java will not be executed]")
    print()

    with open(csv_path, "w", newline="", encoding="utf-8") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=CSV_FIELDS)
        writer.writeheader()
        csv_file.flush()

        try:
            stop_requested = False
            for seed in seeds:
                for tolerance in tolerances:
                    if LIMIT_RUNS > 0 and completed_runs >= LIMIT_RUNS:
                        stop_requested = True
                        break

                    run_number = completed_runs + 1
                    tolerance_dir = os.path.join(
                        logs_dir, f"tolerance_{tolerance_slug(tolerance)}"
                    )
                    os.makedirs(tolerance_dir, exist_ok=True)
                    log_path = os.path.join(tolerance_dir, f"seed_{seed}.log")

                    properties = base_properties.copy()
                    properties["random_seed"] = str(seed)
                    properties["nheft_vcpu_eft_tolerance"] = tolerance

                    temp_file = tempfile.NamedTemporaryFile(
                        delete=False,
                        suffix=".properties",
                        mode="w",
                        encoding="utf-8",
                    )
                    temp_path = temp_file.name
                    temp_file.close()
                    write_props(properties, temp_path)
                    command = java_command + [temp_path]

                    print(
                        f"[{run_number}/{total_planned_runs}] "
                        f"seed={seed} tolerance={tolerance}",
                        end="",
                        flush=True,
                    )

                    row = {field: None for field in CSV_FIELDS}
                    row.update(
                        {
                            "seed": seed,
                            "tolerance": tolerance,
                            "is_original_nheft": 1 if Decimal(tolerance) == 0 else 0,
                            "log_file": os.path.relpath(log_path, output_dir),
                        }
                    )

                    try:
                        if DRY_RUN:
                            print(" [DRY RUN]")
                            print(f"  {shlex.join(command)}")
                            row["status"] = "dry_run"
                            row["time_sec"] = 0.0
                            row["return_code"] = None
                        else:
                            start_time = time.time()
                            try:
                                process = subprocess.run(
                                    command,
                                    stdout=subprocess.PIPE,
                                    stderr=subprocess.STDOUT,
                                    text=True,
                                    timeout=TIMEOUT,
                                    check=False,
                                )
                                elapsed = time.time() - start_time
                                output = process.stdout
                                with open(log_path, "w", encoding="utf-8") as log_file:
                                    log_file.write(output)

                                parsed = parse_output(output)
                                row.update(parsed)
                                row["time_sec"] = round(elapsed, 6)
                                row["return_code"] = process.returncode

                                tolerance_matches = (
                                    parsed["configured_tolerance"] is not None
                                    and abs(
                                        parsed["configured_tolerance"] - float(tolerance)
                                    )
                                    <= 1.0e-12
                                )
                                if process.returncode != 0:
                                    row["status"] = "process_error"
                                elif not has_required_metrics(parsed):
                                    row["status"] = "parse_error"
                                elif not tolerance_matches:
                                    row["status"] = "tolerance_mismatch"
                                else:
                                    row["status"] = "ok"

                                print(
                                    f" {row['status'].upper()} ({elapsed:.1f}s)"
                                    f" NHEFT={row['nheft_makespan']}"
                                    f" vCPUs={row['nheft_vcpus']}"
                                )
                            except subprocess.TimeoutExpired as exc:
                                elapsed = time.time() - start_time
                                timeout_output = exc.stdout or ""
                                if isinstance(timeout_output, bytes):
                                    timeout_output = timeout_output.decode(
                                        "utf-8", errors="replace"
                                    )
                                with open(log_path, "w", encoding="utf-8") as log_file:
                                    log_file.write(timeout_output)
                                    log_file.write(
                                        f"\n[E0-RUNNER] TIMEOUT after {TIMEOUT} seconds\n"
                                    )
                                row["status"] = "timeout"
                                row["time_sec"] = round(elapsed, 6)
                                row["return_code"] = None
                                print(f" TIMEOUT ({elapsed:.1f}s)")
                    finally:
                        try:
                            os.remove(temp_path)
                        except OSError:
                            pass

                    writer.writerow(row)
                    csv_file.flush()
                    completed_runs += 1
                    statuses[row["status"]] += 1

                    manifest["completed_runs"] = completed_runs
                    manifest["status_counts"] = dict(statuses)
                    write_manifest(manifest_path, manifest)

                if stop_requested:
                    break
        except KeyboardInterrupt:
            interrupted = True
            print("\nInterrupted by user. Completed CSV rows have been preserved.")
        finally:
            manifest["completed_runs"] = completed_runs
            manifest["status_counts"] = dict(statuses)
            manifest["interrupted"] = interrupted
            manifest["stopped_by_limit"] = (
                LIMIT_RUNS > 0 and completed_runs >= LIMIT_RUNS
            )
            write_manifest(manifest_path, manifest)

    print()
    print(f"Results written to: {csv_path}")
    print(f"Raw logs written under: {logs_dir}")
    print(f"RESULT_DIR={output_dir}")


if __name__ == "__main__":
    main()
