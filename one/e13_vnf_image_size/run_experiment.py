#!/usr/bin/env python3
"""
E13 Experiment: VNF Image Size Impact (H2 Verification)

Scans vnf_image_size_min / vnf_image_size_max across several image-size ranges
while keeping all other parameters the same as base.properties.
Generates grid_e13_results.csv for downstream analysis.

Usage:
  python3 run_experiment.py                    # Normal run
  E13_DRY_RUN=1 python3 run_experiment.py      # Dry run (print commands only)
  E13_NUM_SEEDS=10 python3 run_experiment.py   # Use 10 seeds instead of default
"""

import os
import subprocess
import tempfile
import csv
import json
import time
import random
from datetime import datetime

# Configuration
REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
EXPERIMENTS_DIR = os.path.join(REPO_ROOT, 'experiments')
THIS_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_PROPS = os.path.join(EXPERIMENTS_DIR, 'base.properties')

# Java command
JAVA_CMD_BASE = [
    'java',
    '-Xmx1000m',
    '-cp', f'{REPO_ROOT}/classes:{REPO_ROOT}/lib/*',
    'net.gripps.cloud.nfv.main.NFVSchedulingTest'
]


def env_int(*names, default=0):
    for name in names:
        value = os.getenv(name)
        if value is not None:
            return int(value)
    return default


# Grid scan parameters
# Chosen as a monotonic progression from low to high image-size pressure:
#   500-2000, 2000-4000, 4000-8000, 8000-10000
# This gives a stronger contrast between light and heavy download conditions.
IMAGE_SIZE_LEVELS = [
    (1000, 3000),
    (3000, 5000),
    (5000, 7000),
    (7000, 9000),
]
DRY_RUN = env_int('E13_DRY_RUN', default=0) == 1
LIMIT_RUNS = env_int('E13_LIMIT_RUNS', default=0)

# Seeding
MASTER_SEED = env_int('E13_MASTER_SEED', default=150)
NUM_SEEDS_DEFAULT = 100
NUM_SEEDS = env_int('E13_NUM_SEEDS', default=NUM_SEEDS_DEFAULT)

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
                if not line or line.startswith('#'):
                    continue
                if '=' in line:
                    k, v = line.split('=', 1)
                    props[k.strip()] = v.strip()
    return props


def write_props(props, path):
    """Write properties dict to file."""
    with open(path, 'w') as f:
        for k, v in props.items():
            f.write(f'{k}={v}\n')


def extract_makespans(output):
    """Extract HEFT, DHEFT, NHEFT makespans from Java output."""
    heft = dheft = nheft = None
    for line in output.split('\n'):
        if '[HEFT]makespan' in line and ':' in line:
            try:
                heft = float(line.split(':')[-1].strip())
            except Exception:
                pass
        elif '[DHEFT]makespan' in line and ':' in line:
            try:
                dheft = float(line.split(':')[-1].strip())
            except Exception:
                pass
        elif '[NHEFT]makespan' in line and ':' in line:
            try:
                nheft = float(line.split(':')[-1].strip())
            except Exception:
                pass
    return heft, dheft, nheft


def main():
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    out_dir = os.path.join(THIS_DIR, f'run_{timestamp}_{MASTER_SEED}_{NUM_SEEDS_DEFAULT}')
    os.makedirs(out_dir, exist_ok=True)
    logs_dir = os.path.join(out_dir, 'logs')
    os.makedirs(logs_dir, exist_ok=True)

    csv_path = os.path.join(out_dir, 'grid_e13_results.csv')
    results = []

    base = read_props(BASE_PROPS)

    total_runs = len(IMAGE_SIZE_LEVELS) * len(SEEDS)
    run_count = 0

    print('=== E13 Experiment: VNF Image Size Impact ===')
    print(f'Master seed: {MASTER_SEED}')
    print(f'Number of seeds: {NUM_SEEDS}')
    print('Image size ranges: ' + ', '.join([f'{mn}-{mx}' for mn, mx in IMAGE_SIZE_LEVELS]))
    print(f'Total runs: {total_runs}')
    if DRY_RUN:
        print('[DRY RUN MODE - will not execute Java]')
    print()

    for img_min, img_max in IMAGE_SIZE_LEVELS:
        for s in SEEDS:
            run_count += 1
            if LIMIT_RUNS > 0 and run_count > LIMIT_RUNS:
                print(f'[{run_count}/{total_runs}] Limit reached, stopping.')
                break

            props = base.copy()
            props['vnf_image_size_min'] = str(img_min)
            props['vnf_image_size_max'] = str(img_max)
            props['random_seed'] = str(s)

            tmp = tempfile.NamedTemporaryFile(delete=False, suffix='.properties', mode='w')
            write_props(props, tmp.name)
            tmp.close()

            cmd = JAVA_CMD_BASE + [tmp.name]

            print(f'[{run_count}/{total_runs}] vnf_image_size={img_min}-{img_max} seed={s}', end='')

            if DRY_RUN:
                print(' [DRY RUN CMD]')
                print(f'  {" ".join(cmd)}')
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

                    log_name = os.path.join(logs_dir, f'run_seed_{s}_img_{img_min}_{img_max}.log')
                    try:
                        with open(log_name, 'w') as lf:
                            lf.write(output)
                    except Exception:
                        pass

                    heft, dheft, nheft = extract_makespans(output)
                    if heft is not None and dheft is not None and nheft is not None:
                        print(f' OK ({elapsed:.1f}s)')
                        time_sec = elapsed
                    else:
                        print(f' PARSE ERROR (see {log_name})')
                        heft = dheft = nheft = time_sec = 0
                except subprocess.TimeoutExpired:
                    print(' TIMEOUT')
                    heft = dheft = nheft = time_sec = 0
                except Exception as e:
                    print(f' ERROR: {e}')
                    heft = dheft = nheft = time_sec = 0

            results.append({
                'vnf_image_size_min': img_min,
                'vnf_image_size_max': img_max,
                'seed': s,
                'HEFT': heft if heft else 0,
                'DHEFT': dheft if dheft else 0,
                'NHEFT': nheft if nheft else 0,
                'time_sec': time_sec,
            })

            try:
                os.remove(tmp.name)
            except Exception:
                pass

        if LIMIT_RUNS > 0 and run_count > LIMIT_RUNS:
            break

    with open(csv_path, 'w', newline='') as f:
        writer = csv.DictWriter(
            f,
            fieldnames=['vnf_image_size_min', 'vnf_image_size_max', 'seed', 'HEFT', 'DHEFT', 'NHEFT', 'time_sec'],
        )
        writer.writeheader()
        writer.writerows(results)

    print(f'\nResults written to: {csv_path}')
    print(f'RESULT_DIR={out_dir}')

    manifest = {
        'experiment': 'E13 - VNF Image Size Impact (H2)',
        'timestamp': timestamp,
        'master_seed': MASTER_SEED,
        'num_seeds': NUM_SEEDS,
        'seeds_used': SEEDS,
        'image_size_levels': IMAGE_SIZE_LEVELS,
        'image_size_mins': [mn for mn, _ in IMAGE_SIZE_LEVELS],
        'image_size_maxs': [mx for _, mx in IMAGE_SIZE_LEVELS],
        'total_runs': len(results),
        'dry_run': DRY_RUN,
    }
    with open(os.path.join(out_dir, 'run_manifest.json'), 'w') as f:
        json.dump(manifest, f, indent=2)

    with open(BASE_PROPS) as src:
        content = src.read()
    with open(os.path.join(out_dir, 'base_properties_snapshot.properties'), 'w') as dst:
        dst.write(content)


if __name__ == '__main__':
    main()
