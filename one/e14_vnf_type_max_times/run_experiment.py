#!/usr/bin/env python3
"""
E14 Experiment: Task-Type Diversity with Controlled Repetition Density

Varies vnf_type_max while keeping effective repetition density controlled:
effective_total_vnf_num = 10 * vnf_type_max.
When multiple_sfc_num > 1, each child SFC gets:
per_sfc_vnf_num = effective_total_vnf_num / multiple_sfc_num.
All other parameters are inherited from base.properties.

This follows the advisor's guidance: when the number of task types increases,
the total number of tasks should also increase accordingly.

Usage:
  python3 run_experiment.py                    # Normal run
  E14_DRY_RUN=1 python3 run_experiment.py      # Dry run (print commands only)
  E14_NUM_SEEDS=10 python3 run_experiment.py   # Use 10 seeds instead of default
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
VNF_TYPE_MAXS = [4, 8, 12, 20]
TASKS_PER_TYPE = 10
DRY_RUN = env_int('E14_DRY_RUN', default=0) == 1
LIMIT_RUNS = env_int('E14_LIMIT_RUNS', default=0)

# Seeding
MASTER_SEED = env_int('E14_MASTER_SEED', default=150)
NUM_SEEDS_DEFAULT = 100
NUM_SEEDS = env_int('E14_NUM_SEEDS', default=NUM_SEEDS_DEFAULT)

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

    csv_path = os.path.join(out_dir, 'grid_e14_results.csv')
    results = []

    base = read_props(BASE_PROPS)

    base_multiple_sfc_num = int(base.get('multiple_sfc_num', '1'))
    multiple_sfc_num = env_int('E14_MULTIPLE_SFC_NUM', default=base_multiple_sfc_num)
    if multiple_sfc_num <= 0:
        raise ValueError('multiple_sfc_num must be >= 1')

    total_runs = len(VNF_TYPE_MAXS) * len(SEEDS)
    run_count = 0

    print('=== E14 Experiment: Task-Type Diversity with Controlled Repetition Density ===')
    print(f'Master seed: {MASTER_SEED}')
    print(f'Number of seeds: {NUM_SEEDS}')
    print(f'VNF_TYPE_MAXS: {VNF_TYPE_MAXS}')
    print(f'TASKS_PER_TYPE: {TASKS_PER_TYPE}')
    print(f'multiple_sfc_num: {multiple_sfc_num}')
    print(f'Total runs: {total_runs}')
    if DRY_RUN:
        print('[DRY RUN MODE - will not execute Java]')
    print()

    for vtm in VNF_TYPE_MAXS:
        effective_total_vnf_num = vtm * TASKS_PER_TYPE
        if effective_total_vnf_num % multiple_sfc_num != 0:
            raise ValueError(
                f'Incompatible setting: effective_total_vnf_num={effective_total_vnf_num} '
                f'is not divisible by multiple_sfc_num={multiple_sfc_num}.'
            )
        per_sfc_vnf_num = effective_total_vnf_num // multiple_sfc_num
        for s in SEEDS:
            run_count += 1
            if LIMIT_RUNS > 0 and run_count > LIMIT_RUNS:
                print(f'[{run_count}/{total_runs}] Limit reached, stopping.')
                break

            props = base.copy()
            props['vnf_type_min'] = '1'
            props['vnf_type_max'] = str(vtm)
            # Keep this in sync with effective total for traceability.
            props['sfc_vnf_num'] = str(effective_total_vnf_num)
            props['multiple_sfc_num'] = str(multiple_sfc_num)
            props['multiple_sfc_vnf_num_min'] = str(per_sfc_vnf_num)
            props['multiple_sfc_vnf_num_max'] = str(per_sfc_vnf_num)
            props['random_seed'] = str(s)

            # Write temp properties
            tmp = tempfile.NamedTemporaryFile(delete=False, suffix='.properties', mode='w')
            write_props(props, tmp.name)
            tmp.close()

            cmd = JAVA_CMD_BASE + [tmp.name]

            print(
                f'[{run_count}/{total_runs}] '
                f'vnf_type_max={vtm} total={effective_total_vnf_num} '
                f'multiple_sfc_num={multiple_sfc_num} per_sfc={per_sfc_vnf_num} seed={s}',
                end=''
            )

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

                    # Save raw stdout for debugging (one file per run)
                    log_name = os.path.join(
                        logs_dir,
                        f'run_{MASTER_SEED}_seed_{s}_vtm_{vtm}_tasks_{effective_total_vnf_num}.log'
                    )
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
                'vnf_type_max': vtm,
                'sfc_vnf_num': effective_total_vnf_num,
                'multiple_sfc_num': multiple_sfc_num,
                'per_sfc_vnf_num': per_sfc_vnf_num,
                'expected_tasks_per_type': TASKS_PER_TYPE,
                'seed': s,
                'HEFT': heft if heft else 0,
                'DHEFT': dheft if dheft else 0,
                'NHEFT': nheft if nheft else 0,
                'time_sec': time_sec,
            })

            # Cleanup temp file
            try:
                os.remove(tmp.name)
            except Exception:
                pass

        if LIMIT_RUNS > 0 and run_count > LIMIT_RUNS:
            break

    # Write results CSV
    with open(csv_path, 'w', newline='') as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                'vnf_type_max',
                'sfc_vnf_num',
                'multiple_sfc_num',
                'per_sfc_vnf_num',
                'expected_tasks_per_type',
                'seed',
                'HEFT',
                'DHEFT',
                'NHEFT',
                'time_sec',
            ],
        )
        writer.writeheader()
        writer.writerows(results)

    print(f'\nResults written to: {csv_path}')
    print(f'RESULT_DIR={out_dir}')

    # Write manifest
    manifest = {
        'experiment': 'E14 - Task-Type Diversity with Controlled Repetition Density',
        'timestamp': timestamp,
        'master_seed': MASTER_SEED,
        'num_seeds': NUM_SEEDS,
        'seeds_used': SEEDS,
        'vnf_type_maxs': VNF_TYPE_MAXS,
        'multiple_sfc_num': multiple_sfc_num,
        'tasks_per_type': TASKS_PER_TYPE,
        'total_runs': len(results),
        'dry_run': DRY_RUN,
    }
    with open(os.path.join(out_dir, 'run_manifest.json'), 'w') as f:
        json.dump(manifest, f, indent=2)

    # Copy base properties
    with open(BASE_PROPS) as src:
        content = src.read()
    with open(os.path.join(out_dir, 'base_properties_snapshot.properties'), 'w') as dst:
        dst.write(content)


if __name__ == '__main__':
    main()
