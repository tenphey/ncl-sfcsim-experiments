#!/usr/bin/env python3
"""Shared runner for standalone baseline experiments in experiments/four."""

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


EXPERIMENTS_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
JAVA_RUNTIME_PROPS = os.path.join(EXPERIMENTS_DIR, "java_runtime.properties")
NUM_SEEDS_DEFAULT = 2000

ALGORITHM_LABELS = {
    "HEFT": "heft",
    "DHEFT": "dheft",
    "NHEFT": "nheft",
    "GHEFT": "gheft",
}
CSV_FIELDS = [
    "seed",
    "variant",
    "variant_display_label",
    "is_baseline_nheft",
    "configured_tolerance",
    "configured_comp_advantage",
    "configured_drt_advantage",
    "configured_irt_advantage",
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

MAKESPAN_RE = re.compile(r"^\[(HEFT|DHEFT|NHEFT|GHEFT)\]makespan:\s*([-+0-9.eE]+)\s*$")
RESOURCE_RE = re.compile(
    r"^\[(HEFT|DHEFT|NHEFT|GHEFT)\]SLR:\s*([-+0-9.eE]+)\s*"
    r"/\s*# of vCPUs:\s*(\d+)\s*"
    r"/\s*# of Hosts:\s*(\d+)\s*"
    r"/# of Ins:\s*(\d+)\s*$"
)
IMAGE_RE = re.compile(
    r"^\[(HEFT|DHEFT|NHEFT|GHEFT)\]imageDL_total=(\d+)\s*"
    r"/\s*fromRepo=(\d+)\s*"
    r"/\s*fromHost=(\d+)\s*$"
)
COMMUNICATION_RE = re.compile(
    r"^CCR_data:\s*([-+0-9.eE]+)\s*"
    r"/\s*IDR_image:\s*([-+0-9.eE]+)\s*"
    r"/\s*NCCR_total:\s*([-+0-9.eE]+)\s*$"
)


def read_props(path):
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
    with open(path, "w", encoding="utf-8") as target:
        for key, value in props.items():
            target.write(f"{key}={value}\n")


def resolve_runtime():
    runtime = read_props(JAVA_RUNTIME_PROPS)
    project_root_raw = require_prop(runtime, "project_root", JAVA_RUNTIME_PROPS)
    if os.path.isabs(project_root_raw):
        project_root = os.path.normpath(project_root_raw)
    else:
        project_root = os.path.normpath(os.path.join(EXPERIMENTS_DIR, project_root_raw))

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


def make_seed_list(master_seed, num_seeds):
    if num_seeds <= 0:
        raise ValueError("NUM_SEEDS must be positive")
    population = range(1000, 1000000)
    if num_seeds > len(population):
        raise ValueError("NUM_SEEDS is larger than the available seed range")
    return random.Random(master_seed).sample(population, num_seeds)


def empty_algorithm_metrics(prefixes=None):
    prefixes = prefixes or ("heft", "dheft", "nheft", "gheft")
    metrics = {}
    for algorithm in prefixes:
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
        "ccr_data": None,
        "idr_image": None,
        "nccr_total": None,
    }
    parsed.update(empty_algorithm_metrics())

    for raw_line in output.splitlines():
        line = raw_line.strip()

        communication_match = COMMUNICATION_RE.match(line)
        if communication_match:
            parsed["ccr_data"] = float(communication_match.group(1))
            parsed["idr_image"] = float(communication_match.group(2))
            parsed["nccr_total"] = float(communication_match.group(3))
            continue

        makespan_match = MAKESPAN_RE.match(line)
        if makespan_match:
            algorithm = ALGORITHM_LABELS[makespan_match.group(1)]
            parsed[f"{algorithm}_makespan"] = float(makespan_match.group(2))
            continue

        resource_match = RESOURCE_RE.match(line)
        if resource_match:
            algorithm = ALGORITHM_LABELS[resource_match.group(1)]
            parsed[f"{algorithm}_slr"] = float(resource_match.group(2))
            parsed[f"{algorithm}_vcpus"] = int(resource_match.group(3))
            parsed[f"{algorithm}_hosts"] = int(resource_match.group(4))
            parsed[f"{algorithm}_instances"] = int(resource_match.group(5))
            continue

        image_match = IMAGE_RE.match(line)
        if image_match:
            algorithm = ALGORITHM_LABELS[image_match.group(1)]
            parsed[f"{algorithm}_image_dl_total"] = int(image_match.group(2))
            parsed[f"{algorithm}_image_from_repo"] = int(image_match.group(3))
            parsed[f"{algorithm}_image_from_host"] = int(image_match.group(4))

    return parsed


def has_required_metrics(parsed):
    required = [
        "ccr_data",
        "idr_image",
        "nccr_total",
        "heft_makespan",
        "dheft_makespan",
        "nheft_makespan",
        "nheft_vcpus",
    ]
    return all(parsed.get(key) is not None for key in required)


def write_manifest(path, manifest):
    temporary_path = path + ".tmp"
    with open(temporary_path, "w", encoding="utf-8") as target:
        json.dump(manifest, target, indent=2)
        target.write("\n")
    os.replace(temporary_path, path)


def build_baseline_row(seed, parsed, elapsed, return_code, status, log_path, output_dir):
    row = {field: None for field in CSV_FIELDS}
    row.update(
        {
            "seed": seed,
            "variant": "baseline",
            "variant_display_label": "NHEFT",
            "is_baseline_nheft": 1,
            "configured_tolerance": 0.0,
            "configured_comp_advantage": 0,
            "configured_drt_advantage": 0,
            "configured_irt_advantage": 0,
            "ccr_data": parsed.get("ccr_data"),
            "idr_image": parsed.get("idr_image"),
            "nccr_total": parsed.get("nccr_total"),
            "time_sec": round(elapsed, 6) if elapsed is not None else None,
            "return_code": return_code,
            "status": status,
            "log_file": os.path.relpath(log_path, output_dir),
        }
    )

    for prefix in ("heft", "dheft", "nheft"):
        for suffix in (
            "makespan",
            "slr",
            "vcpus",
            "hosts",
            "instances",
            "image_dl_total",
            "image_from_repo",
            "image_from_host",
        ):
            row[f"{prefix}_{suffix}"] = parsed.get(f"{prefix}_{suffix}")

    return row


def run_single_baseline_experiment(experiment_dir, experiment_code, raw_csv_name, base_properties_path, purpose):
    env_prefix = experiment_code.upper()
    master_seed = int(os.getenv(f"{env_prefix}_MASTER_SEED", "151"))
    num_seeds = int(os.getenv(f"{env_prefix}_NUM_SEEDS", str(NUM_SEEDS_DEFAULT)))
    limit_runs = int(os.getenv(f"{env_prefix}_LIMIT_RUNS", "0"))
    dry_run = os.getenv(f"{env_prefix}_DRY_RUN", "0") == "1"
    timeout = int(os.getenv(f"{env_prefix}_TIMEOUT", "180"))
    base_override = os.getenv(f"{env_prefix}_BASE_PROPERTIES")

    if base_override:
        if os.path.isabs(base_override):
            resolved_base_properties = os.path.normpath(base_override)
        else:
            resolved_base_properties = os.path.abspath(base_override)
    else:
        resolved_base_properties = os.path.normpath(base_properties_path)

    if not os.path.isfile(resolved_base_properties):
        raise FileNotFoundError(f"Base properties file not found: {resolved_base_properties}")

    project_root, java_command = resolve_runtime()
    base_properties = read_props(resolved_base_properties)
    seeds = make_seed_list(master_seed, num_seeds)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_dir = os.path.join(experiment_dir, f"run_{timestamp}_{master_seed}_{num_seeds}")
    logs_dir = os.path.join(output_dir, "logs")
    os.makedirs(logs_dir, exist_ok=True)

    csv_path = os.path.join(output_dir, raw_csv_name)
    manifest_path = os.path.join(output_dir, "run_manifest.json")
    total_planned_runs = len(seeds)
    statuses = Counter()
    completed_runs = 0
    interrupted = False

    manifest = {
        "experiment": experiment_code.upper(),
        "purpose": purpose,
        "timestamp": timestamp,
        "project_root": project_root,
        "base_properties": resolved_base_properties,
        "java_runtime_properties": JAVA_RUNTIME_PROPS,
        "master_seed": master_seed,
        "num_seeds": num_seeds,
        "seeds_used": seeds,
        "variants": [
            {
                "label": "baseline",
                "display_label": "NHEFT",
                "tolerance": "0.0",
                "comp_advantage": "0",
                "drt_advantage": "0",
                "irt_advantage": "0",
            }
        ],
        "loop_order": "seed_only_single_java_invocation_baseline_only",
        "total_planned_runs": total_planned_runs,
        "completed_runs": 0,
        "status_counts": {},
        "dry_run": dry_run,
        "timeout_seconds": timeout,
        "interrupted": False,
    }
    write_manifest(manifest_path, manifest)

    shutil.copy2(
        resolved_base_properties,
        os.path.join(output_dir, "base_properties_snapshot.properties"),
    )
    shutil.copy2(
        JAVA_RUNTIME_PROPS,
        os.path.join(output_dir, "java_runtime_snapshot.properties"),
    )

    print(f"=== {experiment_code.upper()}: shared baseline ===")
    print(f"Base properties: {resolved_base_properties}")
    print(f"Master seed: {master_seed}")
    print(f"Number of seeds: {num_seeds}")
    print("This runner executes only the shared baseline algorithms: HEFT, DHEFT, and NHEFT.")
    print("GHEFT should be obtained from the corresponding gated scenario run.")
    print("Baseline settings: tolerance=0.0, comp_advantage=0, drt_advantage=0, irt_advantage=0")
    print(f"Total Java runs: {total_planned_runs}")
    if dry_run:
        print("[DRY RUN MODE - Java will not be executed]")
    print()

    with open(csv_path, "w", newline="", encoding="utf-8") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=CSV_FIELDS)
        writer.writeheader()
        csv_file.flush()

        try:
            for seed in seeds:
                if limit_runs > 0 and completed_runs >= limit_runs:
                    break

                run_number = completed_runs + 1
                log_path = os.path.join(logs_dir, f"seed_{seed}.log")

                properties = base_properties.copy()
                properties["random_seed"] = str(seed)
                properties["run_heft"] = "1"
                properties["run_dheft"] = "1"
                properties["run_nheft"] = "1"
                properties["run_nheft_mode2"] = "0"
                properties["nheft_mode2_enabled"] = "0"
                properties["nheft_vcpu_eft_tolerance"] = "0.0"
                properties["nheft_vcpu_open_requires_comp_advantage"] = "0"
                properties["nheft_vcpu_open_requires_drt_advantage"] = "0"
                properties["nheft_vcpu_open_requires_irt_advantage"] = "0"
                properties["nheft_vcpu_open_gate_logic"] = "all"

                temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".properties", mode="w", encoding="utf-8")
                temp_path = temp_file.name
                temp_file.close()
                write_props(properties, temp_path)
                command = java_command + [temp_path]

                print(f"[{run_number}/{total_planned_runs}] seed={seed}", end="", flush=True)
                rows = []
                try:
                    if dry_run:
                        print(" [DRY RUN]")
                        print(f"  {shlex.join(command)}")
                        rows.append(
                            build_baseline_row(
                                seed,
                                empty_algorithm_metrics(),
                                0.0,
                                None,
                                "dry_run",
                                log_path,
                                output_dir,
                            )
                        )
                        statuses["dry_run"] += 1
                    else:
                        start_time = time.time()
                        try:
                            process = subprocess.run(
                                command,
                                stdout=subprocess.PIPE,
                                stderr=subprocess.STDOUT,
                                text=True,
                                timeout=timeout,
                                check=False,
                            )
                            elapsed = time.time() - start_time
                            output = process.stdout
                            with open(log_path, "w", encoding="utf-8") as log_file:
                                log_file.write(output)

                            parsed = parse_output(output)
                            if process.returncode != 0:
                                status = f"java_error_{process.returncode}"
                            elif not has_required_metrics(parsed):
                                status = "parse_error"
                            else:
                                status = "ok"

                            rows.append(
                                build_baseline_row(
                                    seed,
                                    parsed,
                                    elapsed,
                                    process.returncode,
                                    status,
                                    log_path,
                                    output_dir,
                                )
                            )

                            if status == "ok":
                                print(
                                    " OK "
                                    f"({elapsed:.1f}s) "
                                    f"DHEFT={parsed['dheft_makespan']} vCPUs={parsed['dheft_vcpus']} / "
                                    f"NHEFT={parsed['nheft_makespan']} vCPUs={parsed['nheft_vcpus']}"
                                )
                            else:
                                print(f" {status}")
                            statuses[status] += 1
                        except subprocess.TimeoutExpired as exc:
                            partial_output = exc.stdout or ""
                            with open(log_path, "w", encoding="utf-8") as log_file:
                                log_file.write(partial_output)
                            rows.append(
                                build_baseline_row(
                                    seed,
                                    empty_algorithm_metrics(),
                                    timeout,
                                    None,
                                    "timeout",
                                    log_path,
                                    output_dir,
                                )
                            )
                            print(f" timeout (>{timeout}s)")
                            statuses["timeout"] += 1
                finally:
                    try:
                        os.unlink(temp_path)
                    except OSError:
                        pass

                for row in rows:
                    writer.writerow(row)
                csv_file.flush()
                completed_runs += 1
                manifest["completed_runs"] = completed_runs
                manifest["status_counts"] = dict(statuses)
                write_manifest(manifest_path, manifest)

        except KeyboardInterrupt:
            interrupted = True
            print("\nInterrupted by user. Partial results were preserved.")

    manifest["completed_runs"] = completed_runs
    manifest["status_counts"] = dict(statuses)
    manifest["interrupted"] = interrupted
    write_manifest(manifest_path, manifest)

    print()
    print(f"Output directory: {output_dir}")
    print(f"CSV: {csv_path}")
    print(f"Manifest: {manifest_path}")
    print(f"Completed Java runs: {completed_runs} / {total_planned_runs}")
    print("Status counts:")
    if statuses:
        for status, count in sorted(statuses.items()):
            print(f"  {status}: {count}")
    else:
        print("  (none)")
