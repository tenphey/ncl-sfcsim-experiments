#!/usr/bin/env python3
"""Generate paired DHEFT/NHEFT/GHEFT data for experiments/six.

Each seed is evaluated by one Java invocation.  The mode2 result is labeled
GHEFT and uses the IRT-only gate used by the current resource-aware design.
Scenario filtering is intentionally left to the analysis stage; raw rows are
kept so that the generated evidence is not discarded.
"""

import csv
import hashlib
import math
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
from pathlib import Path


FIVE_DIR = Path(__file__).resolve().parent
EXPERIMENTS_DIR = FIVE_DIR.parent
JAVA_RUNTIME_PROPS = EXPERIMENTS_DIR / "java_runtime.properties"
SEED_MANIFEST_PATH = FIVE_DIR / "seeds_500.json"

DEFAULT_MASTER_SEED = 151
DEFAULT_NUM_SEEDS = 500
DEFAULT_TIMEOUT_SECONDS = 180
DATA_REVISION = "schedule-state-20261004-v1"

ALGORITHM_LABELS = {
    "DHEFT": "dheft",
    "NHEFT": "nheft",
    "GHEFT": "gheft",
}

CSV_FIELDS = [
    "seed",
    "scenario",
    "bucket_index",
    "composition",
    "variant",
    "variant_display_label",
    "gheft_gate",
    "gheft_tolerance",
    "gheft_comp_gate",
    "gheft_drt_gate",
    "gheft_irt_gate",
    "ccr_data",
    "idr_image",
    "nccr_total",
]
for _algorithm in ("dheft", "nheft", "gheft"):
    CSV_FIELDS.extend(
        [
            f"{_algorithm}_makespan",
            f"{_algorithm}_slr",
            f"{_algorithm}_vcpus",
            f"{_algorithm}_hosts",
            f"{_algorithm}_instances",
            f"{_algorithm}_image_dl_total",
            f"{_algorithm}_image_from_repo",
            f"{_algorithm}_image_from_host",
        ]
    )
CSV_FIELDS.extend(["time_sec", "return_code", "status", "log_file"])

MAKESPAN_RE = re.compile(r"^\[(DHEFT|NHEFT|GHEFT)\]makespan:\s*([-+0-9.eE]+)\s*$")
RESOURCE_RE = re.compile(
    r"^\[(DHEFT|NHEFT|GHEFT)\]SLR:\s*([-+0-9.eE]+)\s*"
    r"/\s*# of vCPUs:\s*(\d+)\s*"
    r"/\s*# of Hosts:\s*(\d+)\s*"
    r"/# of Ins:\s*(\d+)\s*$"
)
IMAGE_RE = re.compile(
    r"^\[(DHEFT|NHEFT|GHEFT)\]imageDL_total=(\d+)\s*"
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


def write_props(props, path):
    with open(path, "w", encoding="utf-8") as target:
        for key, value in props.items():
            target.write(f"{key}={value}\n")


def require_prop(props, key, source_path):
    value = props.get(key, "").strip()
    if not value:
        raise RuntimeError(f"Missing required property '{key}' in {source_path}")
    return value


def resolve_runtime():
    runtime = read_props(JAVA_RUNTIME_PROPS)
    project_root_raw = require_prop(runtime, "project_root", JAVA_RUNTIME_PROPS)
    project_root = Path(project_root_raw)
    if not project_root.is_absolute():
        project_root = (EXPERIMENTS_DIR / project_root).resolve()

    java_bin = require_prop(runtime, "java_bin", JAVA_RUNTIME_PROPS)
    java_heap = require_prop(runtime, "java_heap", JAVA_RUNTIME_PROPS)
    classes_dir_rel = require_prop(runtime, "classes_dir_rel", JAVA_RUNTIME_PROPS)
    lib_glob_rel = require_prop(runtime, "lib_glob_rel", JAVA_RUNTIME_PROPS)
    main_class = require_prop(runtime, "main_class", JAVA_RUNTIME_PROPS)

    classpath = f"{project_root / classes_dir_rel}{os.pathsep}{project_root / lib_glob_rel}"
    command = [java_bin] + shlex.split(java_heap) + ["-cp", classpath, main_class]
    return project_root, command


def make_seed_list(master_seed, num_seeds):
    if num_seeds <= 0:
        raise ValueError("The number of seeds must be positive")
    return random.Random(master_seed).sample(range(1000, 1000000), num_seeds)


def load_or_create_shared_seeds(master_seed, num_seeds):
    """Use one seed list for all 24 scenarios in this experiment set."""
    if SEED_MANIFEST_PATH.exists():
        with open(SEED_MANIFEST_PATH, encoding="utf-8") as source:
            manifest = json.load(source)
        if manifest.get("master_seed") != master_seed or manifest.get("num_seeds") != num_seeds:
            raise RuntimeError(
                f"{SEED_MANIFEST_PATH} already uses master_seed="
                f"{manifest.get('master_seed')} and num_seeds={manifest.get('num_seeds')}; "
                "remove or rename it only if a new shared seed set is intended."
            )
        seeds = manifest.get("seeds")
        if (not isinstance(seeds, list) or len(seeds) != num_seeds
                or len(set(seeds)) != num_seeds or seeds != make_seed_list(master_seed, num_seeds)):
            raise RuntimeError(f"Invalid shared seed manifest: {SEED_MANIFEST_PATH}")
        return seeds

    seeds = make_seed_list(master_seed, num_seeds)
    # Publish a fully written file without replacing another scenario's seed list.
    with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=SEED_MANIFEST_PATH.parent,
                                     prefix=".seeds-", delete=False) as target:
        temporary_path = target.name
        json.dump(
            {
                "purpose": "Shared seeds for the 24 experiments/six scenarios",
                "master_seed": master_seed,
                "num_seeds": num_seeds,
                "seeds": seeds,
            },
            target,
            indent=2,
        )
        target.write("\n")
    try:
        try:
            os.link(temporary_path, SEED_MANIFEST_PATH)
        except FileExistsError:
            pass
    finally:
        os.unlink(temporary_path)
    return load_or_create_shared_seeds(master_seed, num_seeds)


def empty_metrics():
    metrics = {"ccr_data": None, "idr_image": None, "nccr_total": None}
    for algorithm in ALGORITHM_LABELS.values():
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
    parsed = empty_metrics()
    parsed["validated_algorithms"] = []
    parsed["data_revision"] = None
    for raw_line in output.splitlines():
        line = raw_line.strip()
        if line.startswith("[SIMULATOR-REVISION] "):
            parsed["data_revision"] = line.split(" ", 1)[1]
        for label in ALGORITHM_LABELS:
            if line == f"[{label}-VALIDATION] PASS":
                parsed["validated_algorithms"].append(label)
        communication_match = COMMUNICATION_RE.match(line)
        if communication_match:
            parsed["ccr_data"] = float(communication_match.group(1))
            parsed["idr_image"] = float(communication_match.group(2))
            parsed["nccr_total"] = float(communication_match.group(3))
            continue

        makespan_match = MAKESPAN_RE.match(line)
        if makespan_match:
            prefix = ALGORITHM_LABELS[makespan_match.group(1)]
            parsed[f"{prefix}_makespan"] = float(makespan_match.group(2))
            continue

        resource_match = RESOURCE_RE.match(line)
        if resource_match:
            prefix = ALGORITHM_LABELS[resource_match.group(1)]
            parsed[f"{prefix}_slr"] = float(resource_match.group(2))
            parsed[f"{prefix}_vcpus"] = int(resource_match.group(3))
            parsed[f"{prefix}_hosts"] = int(resource_match.group(4))
            parsed[f"{prefix}_instances"] = int(resource_match.group(5))
            continue

        image_match = IMAGE_RE.match(line)
        if image_match:
            prefix = ALGORITHM_LABELS[image_match.group(1)]
            parsed[f"{prefix}_image_dl_total"] = int(image_match.group(2))
            parsed[f"{prefix}_image_from_repo"] = int(image_match.group(3))
            parsed[f"{prefix}_image_from_host"] = int(image_match.group(4))
    return parsed


def has_required_metrics(parsed):
    required = ["ccr_data", "idr_image", "nccr_total"]
    for prefix in ALGORITHM_LABELS.values():
        required.extend([f"{prefix}_makespan", f"{prefix}_vcpus"])
    if not all(parsed.get(key) is not None and math.isfinite(parsed[key]) for key in required):
        return False
    return (all(parsed[key] >= 0 for key in ("ccr_data", "idr_image", "nccr_total"))
            and all(parsed[f"{prefix}_makespan"] > 0 and parsed[f"{prefix}_vcpus"] > 0
                    for prefix in ALGORITHM_LABELS.values()))


def fingerprint_files(paths, root):
    digest = hashlib.sha256()
    for path in sorted(paths):
        digest.update(str(path.relative_to(root)).encode("utf-8"))
        digest.update(b"\0")
        digest.update(path.read_bytes())
    return digest.hexdigest()


def freeze_runtime(project_root, command, output_dir):
    """Freeze class files and libraries so rebuilding cannot change a running batch."""
    command = list(command)
    cp_position = command.index("-cp") + 1
    entries = command[cp_position].split(os.pathsep)
    classes = Path(entries[0])
    if not (classes / "net/gripps/cloud/nfv/main/NFVSchedulingTest.class").is_file():
        raise RuntimeError("Compiled simulator missing; run ant build before starting experiments")
    source_root = project_root / "src"
    for source in source_root.rglob("*.java"):
        compiled = classes / source.relative_to(source_root).with_suffix(".class")
        if not compiled.is_file() or source.stat().st_mtime_ns > compiled.stat().st_mtime_ns:
            raise RuntimeError(f"Simulator classes are stale for {source}; run ant build before experiments")
    snapshot = output_dir / "classes_snapshot"
    before = fingerprint_files(classes.rglob("*.class"), classes)
    shutil.copytree(classes, snapshot)
    after = fingerprint_files(classes.rglob("*.class"), classes)
    frozen = fingerprint_files(snapshot.rglob("*.class"), snapshot)
    if before != after or frozen != before:
        raise RuntimeError("Class files changed while creating the snapshot; retry after the build finishes")
    entries[0] = str(snapshot)
    command[cp_position] = os.pathsep.join(entries)
    jars = []
    for index, entry in enumerate(entries[1:]):
        path = Path(entry)
        dependencies = sorted(path.parent.glob("*.jar")) if path.name == "*" else [path]
        if not dependencies or not all(dependency.is_file() for dependency in dependencies):
            raise RuntimeError(f"Unsupported or missing runtime dependency: {entry}")
        library_snapshot = output_dir / f"libraries_snapshot_{index}"
        library_snapshot.mkdir()
        for dependency in dependencies:
            shutil.copy2(dependency, library_snapshot / dependency.name)
        if path.name == "*":
            entries[index + 1] = str(library_snapshot / "*")
        else:
            entries[index + 1] = str(library_snapshot / path.name)
        originals = fingerprint_files(dependencies, path.parent)
        copied = fingerprint_files(library_snapshot.iterdir(), library_snapshot)
        if originals != copied:
            raise RuntimeError("Dependencies changed during snapshot creation")
        jars.extend(library_snapshot.iterdir())
    command[cp_position] = os.pathsep.join(entries)
    # Every process in this batch loads the same frozen classes and dependencies.
    git_commit = subprocess.run(["git", "rev-parse", "HEAD"], cwd=project_root,
                                capture_output=True, text=True, check=False).stdout.strip()
    git_diff = subprocess.run(["git", "diff", "HEAD", "--", "src"], cwd=project_root,
                              capture_output=True, check=False).stdout
    metadata = {
        "data_revision": DATA_REVISION,
        "classes_sha256": frozen,
        "sources_sha256": fingerprint_files(source_root.rglob("*.java"), source_root),
        "libraries_sha256": fingerprint_files(jars, output_dir),
        "git_commit": git_commit,
        "source_diff_sha256": hashlib.sha256(git_diff).hexdigest(),
        "runner_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "java_version": subprocess.run([command[0], "-version"], capture_output=True, text=True, check=True).stderr.strip(),
        "java_command": command,
        "nheft_bandwidth_model": "logical host-pair and DC-pair slots; not aggregate endpoint egress",
        "dheft_bandwidth_model": "serialized host queues; cached-VM transfer uses host bottleneck",
        "validation_required": True,
    }
    return command, metadata


def write_manifest(path, manifest):
    temporary_path = str(path) + ".tmp"
    with open(temporary_path, "w", encoding="utf-8") as target:
        json.dump(manifest, target, indent=2)
        target.write("\n")
    os.replace(temporary_path, path)


def build_row(seed, scenario, parsed, elapsed, return_code, status, log_path, output_dir):
    bucket_index = int(scenario[1:3])
    composition = scenario[-1]
    row = {field: None for field in CSV_FIELDS}
    row.update(
        {
            "seed": seed,
            "scenario": scenario,
            "bucket_index": bucket_index,
            "composition": composition,
            "variant": "baseline_plus_gheft",
            "variant_display_label": "DHEFT/NHEFT/GHEFT",
            "gheft_gate": "IRT-only",
            "gheft_tolerance": 0.0,
            "gheft_comp_gate": 0,
            "gheft_drt_gate": 0,
            "gheft_irt_gate": 1,
            "ccr_data": parsed.get("ccr_data"),
            "idr_image": parsed.get("idr_image"),
            "nccr_total": parsed.get("nccr_total"),
            "time_sec": round(elapsed, 6) if elapsed is not None else None,
            "return_code": return_code,
            "status": status,
            "log_file": os.path.relpath(log_path, output_dir),
        }
    )
    for prefix in ALGORITHM_LABELS.values():
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


def run_scenario(scenario, experiment_dir, base_properties_path, raw_csv_name=None):
    """Run one of E01X--E08Z and preserve partial output on Ctrl+C."""
    experiment_dir = Path(experiment_dir).resolve()
    base_properties_path = Path(base_properties_path).resolve()
    if not base_properties_path.is_file():
        raise FileNotFoundError(f"Base properties file not found: {base_properties_path}")

    master_seed = int(os.getenv("FIVE_MASTER_SEED", str(DEFAULT_MASTER_SEED)))
    num_seeds = int(os.getenv("FIVE_NUM_SEEDS", str(DEFAULT_NUM_SEEDS)))
    limit_runs = int(os.getenv("FIVE_LIMIT_RUNS", "0"))
    timeout = int(os.getenv("FIVE_TIMEOUT", str(DEFAULT_TIMEOUT_SECONDS)))
    dry_run = os.getenv("FIVE_DRY_RUN", "0") == "1"

    project_root, java_command = resolve_runtime()
    base_properties = read_props(base_properties_path)
    seeds = load_or_create_shared_seeds(master_seed, num_seeds)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    output_dir = experiment_dir / f"run_{timestamp}_{master_seed}_{num_seeds}"
    logs_dir = output_dir / "logs"
    output_dir.mkdir(parents=True, exist_ok=False)
    logs_dir.mkdir(parents=True, exist_ok=True)
    raw_csv_name = raw_csv_name or f"{scenario}_results.csv"
    csv_path = output_dir / raw_csv_name
    manifest_path = output_dir / "run_manifest.json"

    manifest = {
        "experiment": scenario,
        "purpose": "Paired raw data for DHEFT, NHEFT, and IRT-gated GHEFT",
        "timestamp": timestamp,
        "project_root": str(project_root),
        "base_properties": str(base_properties_path),
        "java_runtime_properties": str(JAVA_RUNTIME_PROPS),
        "master_seed": master_seed,
        "num_seeds": num_seeds,
        "shared_seed_manifest": str(SEED_MANIFEST_PATH),
        "seeds_used": seeds,
        "algorithms": ["DHEFT", "NHEFT", "GHEFT"],
        "gheft_gate": {
            "label": "IRT-only",
            "tolerance": 0.0,
            "comp_advantage": 0,
            "drt_advantage": 0,
            "irt_advantage": 1,
            "gate_logic": "all",
        },
        "filter_policy": {
            "nccr_buckets": "(0.10,0.18] ... (5.62,10.00]",
            "balanced_relative_gap_max_percent": 10.0,
            "image_dominant_relative_gap_min_percent": 20.0,
            "data_dominant_relative_gap_min_percent": 20.0,
            "raw_rows_are_not_filtered": True,
        },
        "loop_order": "one_java_invocation_per_seed_with_three_algorithms",
        "total_planned_runs": len(seeds),
        "completed_runs": 0,
        "status_counts": {},
        "timeout_seconds": timeout,
        "dry_run": dry_run,
        "interrupted": False,
        "complete": False,
    }
    if not dry_run:
        java_command, runtime_metadata = freeze_runtime(project_root, java_command, output_dir)
        manifest.update(runtime_metadata)
    manifest["base_properties_sha256"] = hashlib.sha256(base_properties_path.read_bytes()).hexdigest()
    write_manifest(manifest_path, manifest)
    shutil.copy2(base_properties_path, output_dir / "base_properties_snapshot.properties")
    shutil.copy2(JAVA_RUNTIME_PROPS, output_dir / "java_runtime_snapshot.properties")

    statuses = Counter()
    completed_runs = 0
    interrupted = False
    total_planned_runs = len(seeds)

    print(f"=== {scenario}: DHEFT/NHEFT/GHEFT ===")
    print(f"Base properties: {base_properties_path}")
    print(f"Shared seeds: {SEED_MANIFEST_PATH} ({num_seeds} seeds, master={master_seed})")
    print("GHEFT gate: IRT-only; tolerance=0.0")
    print("One Java invocation per seed; all three algorithm results are paired.")
    print("Raw rows are preserved; NCCR/CCR/IDR filtering is applied later by analysis.")
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
                log_path = logs_dir / f"seed_{seed}.log"
                properties = base_properties.copy()
                properties.update(
                    {
                        "random_seed": str(seed),
                        # Only the three paired download-aware methods run in six.
                        "run_heft": "0",
                        "run_random_clustering": "0",
                        "run_dheft": "1",
                        "run_nheft": "1",
                        "run_nheft_mode2": "1",
                        "nheft_mode2_enabled": "1",
                        "nheft_mode2_label": "GHEFT",
                        "nheft_vcpu_eft_tolerance": "0.0",
                        "nheft_vcpu_open_requires_comp_advantage": "0",
                        "nheft_vcpu_open_requires_drt_advantage": "0",
                        "nheft_vcpu_open_requires_irt_advantage": "0",
                        "nheft_vcpu_open_gate_logic": "all",
                        "nheft_mode2_vcpu_eft_tolerance": "0.0",
                        "nheft_mode2_open_requires_comp_advantage": "0",
                        "nheft_mode2_open_requires_drt_advantage": "0",
                        "nheft_mode2_open_requires_irt_advantage": "1",
                        "nheft_mode2_open_gate_logic": "all",
                    }
                )

                temp_path = None
                try:
                    with tempfile.NamedTemporaryFile(
                        delete=False, suffix=".properties", mode="w", encoding="utf-8"
                    ) as temp_file:
                        temp_path = temp_file.name
                    write_props(properties, temp_path)
                    if completed_runs == 0:
                        write_props(properties, output_dir / "effective_properties_snapshot.properties")
                    command = java_command + [temp_path]
                    print(f"[{run_number}/{total_planned_runs}] seed={seed}", end="", flush=True)

                    if dry_run:
                        parsed = empty_metrics()
                        elapsed = 0.0
                        return_code = None
                        status = "dry_run"
                        print(" [DRY RUN]")
                        print(f"  {shlex.join(command)}")
                    else:
                        start_time = time.time()
                        try:
                            process = subprocess.run(
                                command,
                                stdout=subprocess.PIPE,
                                stderr=subprocess.STDOUT,
                                text=True,
                                timeout=timeout,
                                cwd=str(project_root),
                                check=False,
                            )
                            elapsed = time.time() - start_time
                            output = process.stdout or ""
                            log_path.write_text(output, encoding="utf-8")
                            parsed = parse_output(output)
                            return_code = process.returncode
                            if return_code != 0:
                                status = f"java_error_{return_code}"
                            elif not has_required_metrics(parsed):
                                status = "parse_error"
                            elif (parsed.get("data_revision") != DATA_REVISION
                                  or set(parsed.get("validated_algorithms", [])) != set(ALGORITHM_LABELS)):
                                status = "validation_missing"
                            else:
                                status = "ok"
                            if status == "ok":
                                print(
                                    " OK "
                                    f"({elapsed:.1f}s) "
                                    f"DHEFT={parsed['dheft_makespan']} / "
                                    f"NHEFT={parsed['nheft_makespan']} / "
                                    f"GHEFT={parsed['gheft_makespan']} "
                                    f"vCPUs={parsed['gheft_vcpus']}"
                                )
                            else:
                                print(f" {status}")
                        except subprocess.TimeoutExpired as exc:
                            elapsed = timeout
                            partial_output = exc.stdout or ""
                            if isinstance(partial_output, bytes):
                                partial_output = partial_output.decode(errors="replace")
                            log_path.write_text(partial_output, encoding="utf-8")
                            parsed = parse_output(partial_output)
                            return_code = None
                            status = "timeout"
                            print(f" timeout (>{timeout}s)")

                    row = build_row(
                        seed,
                        scenario,
                        parsed,
                        elapsed,
                        return_code,
                        status,
                        log_path,
                        output_dir,
                    )
                    writer.writerow(row)
                    csv_file.flush()
                    statuses[status] += 1
                finally:
                    if temp_path:
                        try:
                            os.unlink(temp_path)
                        except OSError:
                            pass

                completed_runs += 1
                manifest["completed_runs"] = completed_runs
                manifest["status_counts"] = dict(statuses)
                write_manifest(manifest_path, manifest)
                if not dry_run and status != "ok":
                    raise RuntimeError(f"Stopped after seed {seed}: {status}; inspect {log_path}")
        except KeyboardInterrupt:
            interrupted = True
            print("\nInterrupted by user. Partial results were preserved.")

    manifest["completed_runs"] = completed_runs
    manifest["status_counts"] = dict(statuses)
    manifest["interrupted"] = interrupted
    manifest["complete"] = not interrupted and completed_runs == total_planned_runs and statuses.get("ok", 0) == total_planned_runs
    write_manifest(manifest_path, manifest)
    print()
    print(f"Output directory: {output_dir}")
    print(f"CSV: {csv_path}")
    print(f"Completed Java runs: {completed_runs} / {total_planned_runs}")
    print("Status counts:")
    for status, count in sorted(statuses.items()):
        print(f"  {status}: {count}")
    if interrupted:
        raise SystemExit(130)
