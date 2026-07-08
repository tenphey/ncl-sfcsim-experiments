#!/usr/bin/env python3
"""
Generic Single-Seed Deep Dive Analysis with DAG export

用途:
  根据任意实验 properties 文件，重新运行某个单独 seed，
  导出完整日志、properties 快照和 DAG 元数据，便于复盘 NHEFT 失利案例。

使用方法:
  python3 experiments/analyze_single_seed_with_dag.py <seed> <properties> [--dag|--no-dag]

例子:
  python3 experiments/analyze_single_seed_with_dag.py 1769 experiments/e48/b48.properties
  python3 experiments/analyze_single_seed_with_dag.py 1769 experiments/e48/b48.properties --no-dag

输出:
  - HEFT / DHEFT / NHEFT makespan
  - CCR_data / IDR_image / NCCR_total
  - 完整原始日志
  - 本次执行的 properties 快照
  - DAG 输出目录指针（如果开启 DAG）

输出目录规则:
  - 调试输出会保存到 <properties所在目录>/debug_<seed>_<properties文件名去后缀>/
"""

import os
import re
import sys
import subprocess
import tempfile
from datetime import datetime


REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
THIS_DIR = os.path.dirname(os.path.abspath(__file__))

JAVA_CMD_BASE = [
    "java",
    "-Xmx1000m",
    "-cp",
    f"{REPO_ROOT}/classes:{REPO_ROOT}/lib/*",
    "net.gripps.cloud.nfv.main.NFVSchedulingTest",
]

TIMEOUT = 120
FLOAT_PAT = r"[-+]?(?:\d+\.?\d*|\.\d+)(?:[eE][-+]?\d+)?"
CCR_LINE_RE = re.compile(
    rf"CCR_data:\s*({FLOAT_PAT})\s*/\s*IDR_image:\s*({FLOAT_PAT})\s*/\s*NCCR_total:\s*({FLOAT_PAT})"
)
DAG_OUT_RE = re.compile(r"\[DAG-EXPORT\]\s*outputDir=(.+)")


def resolve_props_path(arg):
    if os.path.isabs(arg):
        return arg if os.path.exists(arg) else None
    candidate = os.path.join(REPO_ROOT, arg)
    if os.path.exists(candidate):
        return candidate
    candidate = os.path.join(THIS_DIR, arg)
    if os.path.exists(candidate):
        return candidate
    return None


def read_props(path):
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
    with open(path, "w") as f:
        for k, v in props.items():
            f.write(f"{k}={v}\n")


def extract_makespans(output):
    results = {
        "HEFT": None,
        "DHEFT": None,
        "NHEFT": None,
    }
    for line in output.split("\n"):
        if "[HEFT]makespan" in line and ":" in line:
            try:
                results["HEFT"] = float(line.split(":")[-1].strip())
            except Exception:
                pass
        elif "[DHEFT]makespan" in line and ":" in line:
            try:
                results["DHEFT"] = float(line.split(":")[-1].strip())
            except Exception:
                pass
        elif "[NHEFT]makespan" in line and ":" in line:
            try:
                results["NHEFT"] = float(line.split(":")[-1].strip())
            except Exception:
                pass
    return results


def extract_ccr_idr_nccr(output):
    ccr = idr = nccr = None
    for line in output.split("\n"):
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
    Default: DAG export ON.
    Supports:
      --dag / dag / on / true / 1
      --no-dag / off / false / 0
    """
    dag_enabled = True
    if len(argv) < 4:
        return dag_enabled

    raw = argv[3].strip().lower()
    if raw in {"--no-dag", "no-dag", "off", "false", "0"}:
        return False
    if raw in {"--dag", "dag", "on", "true", "1"}:
        return True
    return dag_enabled


def extract_dag_output_dir(output):
    for line in output.split("\n"):
        m = DAG_OUT_RE.search(line)
        if m:
            return m.group(1).strip()
    return None


def detect_scenario_hint(props_path):
    """
    从 properties 文件顶部注释里尽量提取一句实验条件说明。
    如果没法提取，就退化成文件名。
    """
    try:
        with open(props_path, "r", errors="ignore") as f:
            for line in f:
                s = line.strip()
                if s.startswith("#") and "NCCR_total" in s and "CCR_data" in s:
                    return s.lstrip("#").strip()
    except Exception:
        pass
    return os.path.basename(props_path)


def analyze():
    if len(sys.argv) < 3:
        print("Usage: python3 experiments/analyze_single_seed_with_dag.py <seed> <properties> [--dag|--no-dag]")
        print("Example: python3 experiments/analyze_single_seed_with_dag.py 1769 experiments/e48/b48.properties")
        sys.exit(1)

    seed = int(sys.argv[1])
    props_path = resolve_props_path(sys.argv[2])
    if not props_path:
        print(f"ERROR: properties file not found: {sys.argv[2]}")
        sys.exit(1)

    dag_enabled = parse_dag_flag(sys.argv)
    scenario_hint = detect_scenario_hint(props_path)

    props_dir = os.path.dirname(props_path)
    props_stem = os.path.splitext(os.path.basename(props_path))[0]

    print(f'\n{"="*78}')
    print("Generic Single-Seed Deep Dive Analysis")
    print(f'{"="*78}')
    print(f"Seed: {seed}")
    print(f"Properties: {props_path}")
    print(f"Scenario hint: {scenario_hint}")
    print(f'DAG export: {"ON" if dag_enabled else "OFF"}')
    print(f'{"="*78}\n')

    base = read_props(props_path)
    base["random_seed"] = str(seed)
    base["debug_nheft"] = "1"

    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".properties", mode="w")
    write_props(base, tmp.name)
    tmp.close()

    cmd = JAVA_CMD_BASE + [tmp.name]
    if dag_enabled:
        cmd.append("DAG")

    print("Running Java simulator...\n")

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

        print(f'{"-"*78}')
        print("RESULTS")
        print(f'{"-"*78}')

        if metrics["HEFT"] is not None:
            print(f'HEFT makespan:  {metrics["HEFT"]:.4f} seconds')
        else:
            print("HEFT makespan:  (not parsed)")

        if metrics["DHEFT"] is not None:
            print(f'DHEFT makespan: {metrics["DHEFT"]:.4f} seconds')
        else:
            print("DHEFT makespan: (not parsed)")

        if metrics["NHEFT"] is not None:
            print(f'NHEFT makespan: {metrics["NHEFT"]:.4f} seconds')
        else:
            print("NHEFT makespan: (not parsed)")

        if metrics["DHEFT"] is not None and metrics["NHEFT"] is not None:
            diff = metrics["NHEFT"] - metrics["DHEFT"]
            pct = (diff / metrics["DHEFT"]) * 100 if metrics["DHEFT"] != 0 else float("nan")
            status = "NHEFT WINS ✓" if diff < 0 else "NHEFT FAILS ✗"
            print(f'\n{"-"*78}')
            print("Comparison: NHEFT vs DHEFT")
            print(f'{"-"*78}')
            print(f"Difference (NHEFT - DHEFT): {diff:.4f} seconds ({pct:+.2f}%)")
            print(f"Status: {status}")

        print(f'\n{"-"*78}')
        print("CCR / IDR / NCCR")
        print(f'{"-"*78}')
        if ccr_data is None or idr_image is None or nccr_total is None:
            print("CCR/IDR/NCCR: (not parsed)")
        else:
            print(f"CCR_data:   {ccr_data:.4f}")
            print(f"IDR_image:  {idr_image:.4f}")
            print(f"NCCR_total: {nccr_total:.4f}")
            print(f"CCR - IDR:  {ccr_data - idr_image:+.4f}")

        print(f"\nExecution time: {elapsed:.2f} seconds")

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        debug_dir = os.path.join(props_dir, f"debug_{seed}_{props_stem}")
        os.makedirs(debug_dir, exist_ok=True)

        out_log = os.path.join(debug_dir, f"single_seed_seed{seed}_{props_stem}_{timestamp}.log")
        with open(out_log, "w") as f:
            f.write(output)

        out_props = os.path.join(debug_dir, f"single_seed_seed{seed}_{props_stem}_{timestamp}.properties")
        write_props(base, out_props)

        info_md = os.path.join(debug_dir, "README.txt")
        with open(info_md, "w") as f:
            f.write(f"seed={seed}\n")
            f.write(f"properties={props_path}\n")
            f.write(f"scenario_hint={scenario_hint}\n")
            f.write(f"dag_enabled={dag_enabled}\n")
            f.write(f"log={out_log}\n")
            f.write(f"props_snapshot={out_props}\n")

        print(f"\nFull output saved to: {out_log}")
        print(f"Run properties saved to: {out_props}")
        print(f"Debug directory: {debug_dir}")

        if dag_enabled:
            if dag_output_dir:
                out_dag = os.path.join(debug_dir, f"single_seed_seed{seed}_{props_stem}_{timestamp}.dag_output.txt")
                with open(out_dag, "w") as f:
                    f.write(dag_output_dir + "\n")
                print(f"DAG metadata output dir: {dag_output_dir}")
                print(f"DAG output pointer saved to: {out_dag}")
            else:
                print("WARNING: DAG export enabled but output directory was not found in Java output.")

        print(f'\n{"-"*78}')
        print("RAW OUTPUT (last 30 lines)")
        print(f'{"-"*78}')
        lines = output.split("\n")
        for line in lines[-30:]:
            if line.strip():
                print(line)

    except subprocess.TimeoutExpired:
        print(f"ERROR: Simulation timed out after {TIMEOUT} seconds")
        sys.exit(1)
    except Exception as e:
        print(f"ERROR: {e}")
        sys.exit(1)
    finally:
        try:
            os.remove(tmp.name)
        except Exception:
            pass

    print(f'\n{"="*78}\n')


if __name__ == "__main__":
    analyze()
