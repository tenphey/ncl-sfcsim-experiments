#!/usr/bin/env python3
"""
Single Seed Deep Dive Analysis for E23 (B3 Fixed Scenario)

【用途】分析单个 seed 的调度详情（HEFT / DHEFT / NHEFT 对比）

【使用方法】
  python3 analyze_single_seed_with_dag.py <seed> [--dag|--no-dag]

【参数说明】
  - <seed>: 随机数种子（例如 7476）
  - --dag / --no-dag: 是否开启 DAG 元数据导出（默认开启）

【使用例子】
  python3 analyze_single_seed_with_dag.py 7476
  python3 analyze_single_seed_with_dag.py 7476 --no-dag

【输出说明】
  - 三个算法的 makespan 对比 (HEFT vs DHEFT vs NHEFT)
  - CCR_data / IDR_image / NCCR_total
  - 该 seed 是否满足 b3 条件：0 < NCCR_total < 1 AND CCR_data < IDR_image
  - 详细日志保存到 debug_{seed}/ 目录
"""

import os
import re
import sys
import subprocess
import tempfile
from datetime import datetime

# ============================================================================
# 路径配置
# ============================================================================
REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
THIS_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_PROPS = os.path.join(THIS_DIR, 'b3.properties')

# ============================================================================
# Java 执行命令
# ============================================================================
JAVA_CMD_BASE = [
    'java',
    '-Xmx1000m',
    '-cp', f'{REPO_ROOT}/classes:{REPO_ROOT}/lib/*',
    'net.gripps.cloud.nfv.main.NFVSchedulingTest'
]

TIMEOUT = 120
FLOAT_PAT = r"[-+]?(?:\d+\.?\d*|\.\d+)(?:[eE][-+]?\d+)?"
CCR_LINE_RE = re.compile(
    rf"CCR_data:\s*({FLOAT_PAT})\s*/\s*IDR_image:\s*({FLOAT_PAT})\s*/\s*NCCR_total:\s*({FLOAT_PAT})"
)
DAG_OUT_RE = re.compile(r"\[DAG-EXPORT\]\s*outputDir=(.+)")


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
    results = {
        'HEFT': None,
        'DHEFT': None,
        'NHEFT': None,
    }
    for line in output.split('\n'):
        if '[HEFT]makespan' in line and ':' in line:
            try:
                results['HEFT'] = float(line.split(':')[-1].strip())
            except Exception:
                pass
        elif '[DHEFT]makespan' in line and ':' in line:
            try:
                results['DHEFT'] = float(line.split(':')[-1].strip())
            except Exception:
                pass
        elif '[NHEFT]makespan' in line and ':' in line:
            try:
                results['NHEFT'] = float(line.split(':')[-1].strip())
            except Exception:
                pass
    return results


def extract_ccr_idr_nccr(output):
    ccr = idr = nccr = None
    for line in output.split('\n'):
        m = CCR_LINE_RE.search(line)
        if m:
            try:
                ccr = float(m.group(1))
                idr = float(m.group(2))
                nccr = float(m.group(3))
            except Exception:
                pass
    return ccr, idr, nccr


def parse_dag_flag(argv):
    """
    Default: DAG export ON for analyze_single_seed_with_dag.
    Supports:
      --dag / dag / on / true / 1
      --no-dag / off / false / 0
    """
    dag_enabled = True
    if len(argv) < 3:
        return dag_enabled

    raw = argv[2].strip().lower()
    if raw in {'--no-dag', 'no-dag', 'off', 'false', '0'}:
        return False
    if raw in {'--dag', 'dag', 'on', 'true', '1'}:
        return True
    return dag_enabled


def extract_dag_output_dir(output):
    for line in output.split('\n'):
        m = DAG_OUT_RE.search(line)
        if m:
            return m.group(1).strip()
    return None


def analyze():
    if len(sys.argv) < 2:
        print('Usage: python3 analyze_single_seed_with_dag.py <seed> [--dag|--no-dag]')
        print('Example: python3 analyze_single_seed_with_dag.py 7476')
        sys.exit(1)

    seed = int(sys.argv[1])
    dag_enabled = parse_dag_flag(sys.argv)

    print(f'\n{"="*70}')
    print('Single Seed Deep Dive Analysis for E23 (B3 Fixed Scenario)')
    print(f'{"="*70}')
    print(f'Seed: {seed}')
    print('B3 target: 0 < NCCR_total < 1 AND CCR_data < IDR_image')
    print(f'DAG export: {"ON" if dag_enabled else "OFF"}')
    print(f'{"="*70}\n')

    base = read_props(BASE_PROPS)
    base['random_seed'] = str(seed)
    base['debug_nheft'] = '1'

    tmp = tempfile.NamedTemporaryFile(delete=False, suffix='.properties', mode='w')
    write_props(base, tmp.name)
    tmp.close()

    cmd = JAVA_CMD_BASE + [tmp.name]
    if dag_enabled:
        cmd.append('DAG')

    print('Running Java simulator...\n')

    try:
        start_time = datetime.now()
        result = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            universal_newlines=True,
            timeout=TIMEOUT,
        )
        elapsed = (datetime.now() - start_time).total_seconds()
        output = result.stdout

        metrics = extract_makespans(output)
        ccr_data, idr_image, nccr_total = extract_ccr_idr_nccr(output)
        dag_output_dir = extract_dag_output_dir(output)

        print(f'{"-"*70}')
        print('RESULTS（结果对比）')
        print(f'{"-"*70}')

        if metrics['HEFT'] is not None:
            print(f'HEFT makespan:  {metrics["HEFT"]:.4f} seconds')
        else:
            print('HEFT makespan:  (not parsed)')

        if metrics['DHEFT'] is not None:
            print(f'DHEFT makespan: {metrics["DHEFT"]:.4f} seconds')
        else:
            print('DHEFT makespan: (not parsed)')

        if metrics['NHEFT'] is not None:
            print(f'NHEFT makespan: {metrics["NHEFT"]:.4f} seconds')
        else:
            print('NHEFT makespan: (not parsed)')

        if metrics['DHEFT'] is not None and metrics['NHEFT'] is not None:
            diff = metrics['NHEFT'] - metrics['DHEFT']
            pct = (diff / metrics['DHEFT']) * 100 if metrics['DHEFT'] != 0 else float('nan')
            status = 'NHEFT WINS ✓' if diff < 0 else 'NHEFT FAILS ✗'
            print(f'\n{"-"*70}')
            print('Comparison: NHEFT vs DHEFT（对比结果）')
            print(f'{"-"*70}')
            print(f'Difference (NHEFT - DHEFT): {diff:.4f} seconds ({pct:+.2f}%)')
            print(f'Status: {status}')

        print(f'\n{"-"*70}')
        print('B3 Condition Check')
        print(f'{"-"*70}')
        if ccr_data is None or idr_image is None or nccr_total is None:
            print('CCR/IDR/NCCR: (not parsed)')
            b3_match = None
        else:
            print(f'CCR_data:   {ccr_data:.4f}')
            print(f'IDR_image:  {idr_image:.4f}')
            print(f'NCCR_total: {nccr_total:.4f}')
            print(f'CCR_data - IDR_image: {ccr_data - idr_image:+.4f}')
            b3_match = (nccr_total > 0.0) and (nccr_total < 1.0) and (ccr_data < idr_image)
            print('B3 match (0 < NCCR < 1 and CCR_data < IDR_image): ' + str(b3_match))

        print(f'\nExecution time: {elapsed:.2f} seconds')

        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        debug_dir = os.path.join(THIS_DIR, f'debug_{seed}')
        os.makedirs(debug_dir, exist_ok=True)

        out_log = os.path.join(debug_dir, f'single_seed_seed{seed}_{timestamp}.log')
        with open(out_log, 'w') as f:
            f.write(output)

        out_props = os.path.join(debug_dir, f'single_seed_seed{seed}_{timestamp}.properties')
        write_props(base, out_props)

        print(f'\nFull output saved to: {out_log}')
        print(f'Run properties saved to: {out_props}')
        if dag_enabled:
            if dag_output_dir:
                out_dag = os.path.join(debug_dir, f'single_seed_seed{seed}_{timestamp}.dag_output.txt')
                with open(out_dag, 'w') as f:
                    f.write(dag_output_dir + '\n')
                print(f'DAG metadata output dir: {dag_output_dir}')
                print(f'DAG output pointer saved to: {out_dag}')
            else:
                print('WARNING: DAG export enabled but output directory was not found in Java output.')

        print(f'\n{"-"*70}')
        print('RAW OUTPUT (last 30 lines)（原始输出最后 30 行）')
        print(f'{"-"*70}')
        lines = output.split('\n')
        for line in lines[-30:]:
            if line.strip():
                print(line)

    except subprocess.TimeoutExpired:
        print(f'ERROR: Simulation timed out after {TIMEOUT} seconds')
        sys.exit(1)
    except Exception as e:
        print(f'ERROR: {e}')
        sys.exit(1)
    finally:
        try:
            os.remove(tmp.name)
        except Exception:
            pass

    print(f'\n{"="*70}\n')


if __name__ == '__main__':
    analyze()
