#!/usr/bin/env python3
"""
E18 Experiment: High Repository BW x SFC Fragmentation Trade-off

Goal:
- Refine E17 by focusing only on higher repository bandwidth levels.
- Keep total workload size fixed.
- Sweep multiple_sfc_num while explicitly treating it as a fragmentation trade-off:
  more concurrent SFCs, but shorter per-SFC chains.

Hypothesis:
- Under sufficiently high repository bandwidth, NHEFT should maintain a clearer
  advantage over DHEFT.
- multiple_sfc_num may not be monotonic, because it changes both overlap
  opportunity and single-SFC chain length.

Usage:
  python3 run_experiment.py
  E18_DRY_RUN=1 python3 run_experiment.py
  E18_NUM_SEEDS=10 python3 run_experiment.py
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
REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
EXPERIMENTS_DIR = os.path.join(REPO_ROOT, "experiments")
THIS_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_PROPS = os.path.join(EXPERIMENTS_DIR, "base.properties")

JAVA_CMD_BASE = [
    "java",
    "-Xmx1000m",
    "-cp",
    f"{REPO_ROOT}/classes:{REPO_ROOT}/lib/*",
    "net.gripps.cloud.nfv.main.NFVSchedulingTest",
]


def env_int(*names, default=0):
    for name in names:
        value = os.getenv(name)
        if value is not None:
            return int(value)
    return default


def env_int_list(*names, default):
    for name in names:
        value = os.getenv(name)
        if value is None:
            continue
        items = [x.strip() for x in value.split(",") if x.strip()]
        if items:
            return [int(x) for x in items]
    return list(default)


# Grid scan parameters
REPO_BWS = env_int_list("E18_REPO_BWS", default=[600, 900])
MULTI_SFC_LEVELS = env_int_list("E18_MULTI_SFC_LEVELS", default=[1, 2, 4, 8])

# Fixed knobs: strong download pressure, but avoid the overly extreme image range
EFFECTIVE_TOTAL_VNF_NUM = env_int("E18_TOTAL_VNF_NUM", default=320)
VNF_TYPE_MIN = env_int("E18_VNF_TYPE_MIN", default=1)
VNF_TYPE_MAX = env_int("E18_VNF_TYPE_MAX", default=20)
VNF_IMAGE_SIZE_MIN = env_int("E18_IMAGE_MIN", default=5000)
VNF_IMAGE_SIZE_MAX = env_int("E18_IMAGE_MAX", default=7000)
DATACENTER_EXTERNALBW_MIN = env_int("E18_DATACENTER_EXTERNALBW_MIN", default=500)
DATACENTER_EXTERNALBW_MAX = env_int("E18_DATACENTER_EXTERNALBW_MAX", default=1000)
HOST_BW_MIN = env_int("E18_HOST_BW_MIN", default=1000)
HOST_BW_MAX = env_int("E18_HOST_BW_MAX", default=2000)

DRY_RUN = env_int("E18_DRY_RUN", default=0) == 1
LIMIT_RUNS = env_int("E18_LIMIT_RUNS", default=0)

# Seeding
MASTER_SEED = env_int("E18_MASTER_SEED", default=150)
NUM_SEEDS_DEFAULT = 30
NUM_SEEDS = env_int("E18_NUM_SEEDS", default=NUM_SEEDS_DEFAULT)

random.seed(MASTER_SEED)
SEEDS = random.sample(range(1000, 9999), NUM_SEEDS)

TIMEOUT = 180  # seconds per run


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
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_dir = os.path.join(THIS_DIR, f"run_{timestamp}_{MASTER_SEED}_{NUM_SEEDS_DEFAULT}")
    os.makedirs(out_dir, exist_ok=True)
    logs_dir = os.path.join(out_dir, "logs")
    os.makedirs(logs_dir, exist_ok=True)

    csv_path = os.path.join(out_dir, "grid_e18_results.csv")
    results = []
    base = read_props(BASE_PROPS)

    total_runs = len(REPO_BWS) * len(MULTI_SFC_LEVELS) * len(SEEDS)
    run_count = 0

    print("=== E18 Experiment: High Repository BW x SFC Fragmentation Trade-off ===")
    print(f"Master seed: {MASTER_SEED}")
    print(f"Number of seeds: {NUM_SEEDS}")
    print(f"Repository BWs: {REPO_BWS}")
    print(f"multiple_sfc_num levels: {MULTI_SFC_LEVELS}")
    print(f"effective_total_vnf_num: {EFFECTIVE_TOTAL_VNF_NUM}")
    print(f"vnf_type range: {VNF_TYPE_MIN}-{VNF_TYPE_MAX}")
    print(f"image_size range: {VNF_IMAGE_SIZE_MIN}-{VNF_IMAGE_SIZE_MAX}")
    print(f"DC external BW: {DATACENTER_EXTERNALBW_MIN}-{DATACENTER_EXTERNALBW_MAX}")
    print(f"Host BW: {HOST_BW_MIN}-{HOST_BW_MAX}")
    print(f"Total runs: {total_runs}")
    if DRY_RUN:
        print("[DRY RUN MODE - will not execute Java]")
    print()

    for rb in REPO_BWS:
        for msfc in MULTI_SFC_LEVELS:
            if EFFECTIVE_TOTAL_VNF_NUM % msfc != 0:
                raise ValueError(
                    f"EFFECTIVE_TOTAL_VNF_NUM={EFFECTIVE_TOTAL_VNF_NUM} "
                    f"is not divisible by multiple_sfc_num={msfc}"
                )
            per_sfc_vnf_num = EFFECTIVE_TOTAL_VNF_NUM // msfc

            for s in SEEDS:
                run_count += 1
                if LIMIT_RUNS > 0 and run_count > LIMIT_RUNS:
                    print(f"[{run_count}/{total_runs}] Limit reached, stopping.")
                    break

                props = base.copy()
                props["vnf_type_min"] = str(VNF_TYPE_MIN)
                props["vnf_type_max"] = str(VNF_TYPE_MAX)
                props["sfc_vnf_num"] = str(EFFECTIVE_TOTAL_VNF_NUM)
                props["multiple_sfc_num"] = str(msfc)
                props["multiple_sfc_vnf_num_min"] = str(per_sfc_vnf_num)
                props["multiple_sfc_vnf_num_max"] = str(per_sfc_vnf_num)
                props["vnf_image_size_min"] = str(VNF_IMAGE_SIZE_MIN)
                props["vnf_image_size_max"] = str(VNF_IMAGE_SIZE_MAX)
                props["repository_bw"] = str(rb)
                props["datacenter_externalbw_min"] = str(DATACENTER_EXTERNALBW_MIN)
                props["datacenter_externalbw_max"] = str(DATACENTER_EXTERNALBW_MAX)
                props["host_bw_min"] = str(HOST_BW_MIN)
                props["host_bw_max"] = str(HOST_BW_MAX)
                props["random_seed"] = str(s)

                tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".properties", mode="w")
                write_props(props, tmp.name)
                tmp.close()

                cmd = JAVA_CMD_BASE + [tmp.name]

                print(
                    f"[{run_count}/{total_runs}] "
                    f"repo_bw={rb} multiple_sfc_num={msfc} per_sfc={per_sfc_vnf_num} seed={s}",
                    end="",
                )

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

                        log_name = os.path.join(
                            logs_dir,
                            f"run_seed_{s}_rb_{rb}_msfc_{msfc}_per_{per_sfc_vnf_num}.log",
                        )
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
                        "repository_bw": rb,
                        "multiple_sfc_num": msfc,
                        "per_sfc_vnf_num": per_sfc_vnf_num,
                        "effective_total_vnf_num": EFFECTIVE_TOTAL_VNF_NUM,
                        "vnf_type_min": VNF_TYPE_MIN,
                        "vnf_type_max": VNF_TYPE_MAX,
                        "vnf_image_size_min": VNF_IMAGE_SIZE_MIN,
                        "vnf_image_size_max": VNF_IMAGE_SIZE_MAX,
                        "datacenter_externalbw_min": DATACENTER_EXTERNALBW_MIN,
                        "datacenter_externalbw_max": DATACENTER_EXTERNALBW_MAX,
                        "host_bw_min": HOST_BW_MIN,
                        "host_bw_max": HOST_BW_MAX,
                        "seed": s,
                        "HEFT": heft if heft else 0,
                        "DHEFT": dheft if dheft else 0,
                        "NHEFT": nheft if nheft else 0,
                        "time_sec": time_sec,
                    }
                )

                try:
                    os.remove(tmp.name)
                except Exception:
                    pass

            if LIMIT_RUNS > 0 and run_count > LIMIT_RUNS:
                break

        if LIMIT_RUNS > 0 and run_count > LIMIT_RUNS:
            break

    with open(csv_path, "w", newline="") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "repository_bw",
                "multiple_sfc_num",
                "per_sfc_vnf_num",
                "effective_total_vnf_num",
                "vnf_type_min",
                "vnf_type_max",
                "vnf_image_size_min",
                "vnf_image_size_max",
                "datacenter_externalbw_min",
                "datacenter_externalbw_max",
                "host_bw_min",
                "host_bw_max",
                "seed",
                "HEFT",
                "DHEFT",
                "NHEFT",
                "time_sec",
            ],
        )
        writer.writeheader()
        writer.writerows(results)

    print(f"\nResults written to: {csv_path}")
    print(f"RESULT_DIR={out_dir}")

    manifest = {
        "experiment": "E18 - High Repository BW x SFC Fragmentation Trade-off",
        "timestamp": timestamp,
        "master_seed": MASTER_SEED,
        "num_seeds": NUM_SEEDS,
        "seeds_used": SEEDS,
        "repository_bws": REPO_BWS,
        "multiple_sfc_levels": MULTI_SFC_LEVELS,
        "effective_total_vnf_num": EFFECTIVE_TOTAL_VNF_NUM,
        "fixed_vnf_type_min": VNF_TYPE_MIN,
        "fixed_vnf_type_max": VNF_TYPE_MAX,
        "fixed_vnf_image_size_min": VNF_IMAGE_SIZE_MIN,
        "fixed_vnf_image_size_max": VNF_IMAGE_SIZE_MAX,
        "fixed_datacenter_externalbw_min": DATACENTER_EXTERNALBW_MIN,
        "fixed_datacenter_externalbw_max": DATACENTER_EXTERNALBW_MAX,
        "fixed_host_bw_min": HOST_BW_MIN,
        "fixed_host_bw_max": HOST_BW_MAX,
        "total_runs": len(results),
        "dry_run": DRY_RUN,
    }
    with open(os.path.join(out_dir, "run_manifest.json"), "w") as f:
        json.dump(manifest, f, indent=2)

    with open(BASE_PROPS) as src:
        content = src.read()
    with open(os.path.join(out_dir, "base_properties_snapshot.properties"), "w") as dst:
        dst.write(content)


if __name__ == "__main__":
    main()
