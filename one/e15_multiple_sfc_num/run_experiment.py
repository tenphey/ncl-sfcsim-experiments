#!/usr/bin/env python3
"""
E15 Experiment: Download Concurrency Opportunity Impact (NHEFT Advantage)

Core idea:
- Keep effective total workload scale controlled.
- Sweep multiple_sfc_num to change concurrent download opportunity.
- Use download-pressure settings so NHEFT's slot-based model is easier to observe.

Expected: as multiple_sfc_num increases, NHEFT should more consistently beat DHEFT.

Usage:
  python3 run_experiment.py
  E15_DRY_RUN=1 python3 run_experiment.py
  E15_NUM_SEEDS=10 python3 run_experiment.py
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

JAVA_CMD_BASE = [
    'java',
    '-Xmx1000m',
    '-cp', f'{REPO_ROOT}/classes:{REPO_ROOT}/lib/*',
    'net.gripps.cloud.nfv.main.NFVSchedulingTest',
]


def env_int(*names, default=0):
    for name in names:
        value = os.getenv(name)
        if value is not None:
            return int(value)
    return default


# Grid parameter (single variable)
MULTI_SFC_LEVELS = [1, 2, 4, 8]

# Fixed knobs (designed to highlight download scheduling)
VNF_TYPE_MIN = env_int('E15_VNF_TYPE_MIN', default=1)
VNF_TYPE_MAX = env_int('E15_VNF_TYPE_MAX', default=12)
EFFECTIVE_TOTAL_VNF_NUM = env_int('E15_TOTAL_VNF_NUM', default=320)
REPOSITORY_BW = env_int('E15_REPOSITORY_BW', default=200)
VNF_IMAGE_SIZE_MIN = env_int('E15_IMAGE_MIN', default=6000)
VNF_IMAGE_SIZE_MAX = env_int('E15_IMAGE_MAX', default=12000)

DRY_RUN = env_int('E15_DRY_RUN', default=0) == 1
LIMIT_RUNS = env_int('E15_LIMIT_RUNS', default=0)

MASTER_SEED = env_int('E15_MASTER_SEED', default=150)
NUM_SEEDS_DEFAULT = 100
NUM_SEEDS = env_int('E15_NUM_SEEDS', default=NUM_SEEDS_DEFAULT)

random.seed(MASTER_SEED)
SEEDS = random.sample(range(1000, 9999), NUM_SEEDS)

TIMEOUT = 120


def read_props(path):
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
    with open(path, 'w') as f:
        for k, v in props.items():
            f.write(f'{k}={v}\n')


def extract_makespans(output):
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

    csv_path = os.path.join(out_dir, 'grid_e15_results.csv')
    results = []
    base = read_props(BASE_PROPS)

    total_runs = len(MULTI_SFC_LEVELS) * len(SEEDS)
    run_count = 0

    print('=== E15 Experiment: Download Concurrency Opportunity Impact ===')
    print(f'Master seed: {MASTER_SEED}')
    print(f'Number of seeds: {NUM_SEEDS}')
    print(f'multiple_sfc_num levels: {MULTI_SFC_LEVELS}')
    print(f'effective_total_vnf_num: {EFFECTIVE_TOTAL_VNF_NUM}')
    print(f'vnf_type range: {VNF_TYPE_MIN}-{VNF_TYPE_MAX}')
    print(f'image_size range: {VNF_IMAGE_SIZE_MIN}-{VNF_IMAGE_SIZE_MAX}')
    print(f'repository_bw: {REPOSITORY_BW}')
    print(f'Total runs: {total_runs}')
    if DRY_RUN:
        print('[DRY RUN MODE - will not execute Java]')
    print()

    for msfc in MULTI_SFC_LEVELS:
        if EFFECTIVE_TOTAL_VNF_NUM % msfc != 0:
            raise ValueError(
                f'EFFECTIVE_TOTAL_VNF_NUM={EFFECTIVE_TOTAL_VNF_NUM} is not divisible by multiple_sfc_num={msfc}'
            )
        per_sfc_vnf_num = EFFECTIVE_TOTAL_VNF_NUM // msfc

        for s in SEEDS:
            run_count += 1
            if LIMIT_RUNS > 0 and run_count > LIMIT_RUNS:
                print(f'[{run_count}/{total_runs}] Limit reached, stopping.')
                break

            props = base.copy()
            props['vnf_type_min'] = str(VNF_TYPE_MIN)
            props['vnf_type_max'] = str(VNF_TYPE_MAX)
            props['sfc_vnf_num'] = str(EFFECTIVE_TOTAL_VNF_NUM)
            props['multiple_sfc_num'] = str(msfc)
            props['multiple_sfc_vnf_num_min'] = str(per_sfc_vnf_num)
            props['multiple_sfc_vnf_num_max'] = str(per_sfc_vnf_num)
            props['vnf_image_size_min'] = str(VNF_IMAGE_SIZE_MIN)
            props['vnf_image_size_max'] = str(VNF_IMAGE_SIZE_MAX)
            props['repository_bw'] = str(REPOSITORY_BW)
            props['random_seed'] = str(s)

            tmp = tempfile.NamedTemporaryFile(delete=False, suffix='.properties', mode='w')
            write_props(props, tmp.name)
            tmp.close()

            cmd = JAVA_CMD_BASE + [tmp.name]

            print(
                f'[{run_count}/{total_runs}] '
                f'multiple_sfc_num={msfc} per_sfc={per_sfc_vnf_num} seed={s}',
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

                    log_name = os.path.join(
                        logs_dir,
                        f'run_{MASTER_SEED}_seed_{s}_msfc_{msfc}_per_{per_sfc_vnf_num}.log',
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
                'multiple_sfc_num': msfc,
                'per_sfc_vnf_num': per_sfc_vnf_num,
                'effective_total_vnf_num': EFFECTIVE_TOTAL_VNF_NUM,
                'vnf_type_min': VNF_TYPE_MIN,
                'vnf_type_max': VNF_TYPE_MAX,
                'vnf_image_size_min': VNF_IMAGE_SIZE_MIN,
                'vnf_image_size_max': VNF_IMAGE_SIZE_MAX,
                'repository_bw': REPOSITORY_BW,
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
            fieldnames=[
                'multiple_sfc_num',
                'per_sfc_vnf_num',
                'effective_total_vnf_num',
                'vnf_type_min',
                'vnf_type_max',
                'vnf_image_size_min',
                'vnf_image_size_max',
                'repository_bw',
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

    manifest = {
        'experiment': 'E15 - Download Concurrency Opportunity Impact',
        'timestamp': timestamp,
        'master_seed': MASTER_SEED,
        'num_seeds': NUM_SEEDS,
        'seeds_used': SEEDS,
        'multiple_sfc_levels': MULTI_SFC_LEVELS,
        'effective_total_vnf_num': EFFECTIVE_TOTAL_VNF_NUM,
        'fixed_vnf_type_min': VNF_TYPE_MIN,
        'fixed_vnf_type_max': VNF_TYPE_MAX,
        'fixed_vnf_image_size_min': VNF_IMAGE_SIZE_MIN,
        'fixed_vnf_image_size_max': VNF_IMAGE_SIZE_MAX,
        'fixed_repository_bw': REPOSITORY_BW,
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
