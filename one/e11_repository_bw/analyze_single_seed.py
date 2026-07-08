#!/usr/bin/env python3
"""
Single Seed Deep Dive Analysis for E11

【用途】分析单个 seed 的调度详情（DHEFT vs NHEFT 对比）

【使用方法】
  python3 analyze_single_seed.py <seed> <repo_bw>

【参数说明】
  - <seed>: 随机数种子（例如 7476）
  - <repo_bw>: 仓库带宽 MBps（例如 60, 120, 240, 480）

【使用例子】
  # 分析最差的情况 (seed=7476, repo_bw=60)
  python3 analyze_single_seed.py 7476 60

  # 尝试高带宽情况 (repo_bw=480 能否改善?)
  python3 analyze_single_seed.py 7476 480

  # 检查一个成功的 seed (seed=9236)
  python3 analyze_single_seed.py 9236 60

【输出说明】
  - 三个算法的 makespan 对比 (HEFT vs DHEFT vs NHEFT)
  - 资源使用对比 (vCPU 数量、Host 数量等)
  - 详细日志保存到文件

【修改说明】
  - 改动 seed / repo_bw: 直接修改命令行参数
  - 如需改基础参数（非 seed / repo_bw）: 见下方 【参数修改位置】注释
"""

import os
import sys
import subprocess
import tempfile
from datetime import datetime

# ============================================================================
# 【参数修改位置 1】目录和文件路径配置
# 一般不需要改，除非项目目录结构变了
# ============================================================================
REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
EXPERIMENTS_DIR = os.path.join(REPO_ROOT, 'experiments')
THIS_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_PROPS = os.path.join(EXPERIMENTS_DIR, 'base.properties')  # 基础配置文件位置

# ============================================================================
# 【参数修改位置 2】Java 执行命令
# 一般不需要改，除非 Java 或类路径变了
# ============================================================================
JAVA_CMD_BASE = [
    'java',
    '-Xmx1000m',  # ← 可改：堆内存大小（如果 OOM，改大这个值）
    '-cp', f'{REPO_ROOT}/classes:{REPO_ROOT}/lib/*',  # classpath
    'net.gripps.cloud.nfv.main.NFVSchedulingTest'  # 入口类
]

# ============================================================================
# 【参数修改位置 3】超时时间
# ============================================================================
TIMEOUT = 120  # ← 可改：每次运行的最长等待时间（秒），默认 120 秒


def read_props(path):
    """
    【说明】读取 properties 配置文件
    【参数】path: 配置文件路径（通常是 base.properties）
    【返回】dict: 键值对字典
    """
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
    """
    【说明】将配置字典写入临时 properties 文件
    【参数】
      - props: 配置字典
      - path: 输出文件路径（通常是临时文件）
    """
    with open(path, 'w') as f:
        for k, v in props.items():
            f.write(f'{k}={v}\n')


def extract_makespans_and_metrics(output):
    """
    【说明】从 Java 程序输出中提取三个算法的 makespan 和指标
    【输出格式】
      Java 程序输出类似：
        [HEFT]makespan:3.8977
        [DHEFT]makespan:3.8977
        [NHEFT]makespan:8.8129
      ↓
      本函数提取这些值

    【参数】output: Java 程序的完整标准输出字符串
    【返回】dict: {'HEFT': float, 'DHEFT': float, 'NHEFT': float, 'raw_output': str}
    """
    results = {
        'HEFT': None,
        'DHEFT': None,
        'NHEFT': None,
        'raw_output': output
    }

    for line in output.split('\n'):
        if '[HEFT]makespan' in line and ':' in line:
            try:
                results['HEFT'] = float(line.split(':')[-1].strip())
            except:
                pass
        elif '[DHEFT]makespan' in line and ':' in line:
            try:
                results['DHEFT'] = float(line.split(':')[-1].strip())
            except:
                pass
        elif '[NHEFT]makespan' in line and ':' in line:
            try:
                results['NHEFT'] = float(line.split(':')[-1].strip())
            except:
                pass

    return results


def analyze():
    """
    【主程序逻辑】
    1. 解析命令行参数 (seed 和 repo_bw)
    2. 读取 base.properties 的基础配置
    3. 修改 seed 和 repo_bw，生成临时配置文件
    4. 调用 Java 程序运行模拟
    5. 提取结果，打印对比
    6. 保存完整日志到文件
    """

    # ========================================================================
    # 【步骤 1】解析命令行参数
    # ========================================================================
    if len(sys.argv) < 3:
        print('Usage: python3 analyze_single_seed.py <seed> <repo_bw>')
        print('Example: python3 analyze_single_seed.py 7476 60')
        sys.exit(1)

    # 【参数修改】如果在脚本内部硬编码参数，改这两行
    seed = int(sys.argv[1])      # ← 命令行参数 1: 随机数种子
    repo_bw = int(sys.argv[2])   # ← 命令行参数 2: 仓库带宽 MBps

    print(f'\n{"="*70}')
    print(f'Single Seed Deep Dive Analysis for E11')
    print(f'{"="*70}')
    print(f'Seed: {seed}')
    print(f'Repository Bandwidth: {repo_bw} MBps')
    print(f'{"="*70}\n')

    # ========================================================================
    # 【步骤 2】读取基础配置
    # ========================================================================
    base = read_props(BASE_PROPS)

    # ========================================================================
    # 【步骤 3】修改运行参数（这是实验真正发生变化的地方）
    # ========================================================================
    base['repository_bw'] = str(repo_bw)  # ← 设置仓库带宽
    base['random_seed'] = str(seed)        # ← 设置随机数种子
    base['debug_nheft'] = '1'              # ← 打开详细调度 trace（逐步日志）

    # 【可选修改】如果想在这里改其他 base.properties 的参数，在下面加：
    # base['vnf_type_max'] = '20'
    # base['sfc_vnf_num'] = '200'
    # 等等...

    # ========================================================================
    # 【步骤 4】生成临时配置文件并启动 Java 程序
    # ========================================================================
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix='.properties', mode='w')
    write_props(base, tmp.name)
    tmp.close()

    cmd = JAVA_CMD_BASE + [tmp.name]

    print(f'Running Java simulator...\n')

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

        # ====================================================================
        # 【步骤 5】提取结果并打印对比
        # ====================================================================
        metrics = extract_makespans_and_metrics(output)

        print(f'{"-"*70}')
        print(f'RESULTS（结果对比）')
        print(f'{"-"*70}')

        if metrics['HEFT'] is not None:
            print(f'HEFT makespan:  {metrics["HEFT"]:.4f} seconds')
        else:
            print(f'HEFT makespan:  (not parsed)')

        if metrics['DHEFT'] is not None:
            print(f'DHEFT makespan: {metrics["DHEFT"]:.4f} seconds')
        else:
            print(f'DHEFT makespan: (not parsed)')

        if metrics['NHEFT'] is not None:
            print(f'NHEFT makespan: {metrics["NHEFT"]:.4f} seconds')
        else:
            print(f'NHEFT makespan: (not parsed)')

        # 计算 NHEFT vs DHEFT 的差异
        if metrics['DHEFT'] and metrics['NHEFT']:
            diff = metrics['NHEFT'] - metrics['DHEFT']
            pct = (diff / metrics['DHEFT']) * 100
            status = "NHEFT WINS ✓" if diff < 0 else "NHEFT FAILS ✗"
            print(f'\n{"-"*70}')
            print(f'Comparison: NHEFT vs DHEFT（对比结果）')
            print(f'{"-"*70}')
            print(f'Difference (NHEFT - DHEFT): {diff:.4f} seconds ({pct:+.2f}%)')
            print(f'Status: {status}')

        print(f'\nExecution time: {elapsed:.2f} seconds')

        # ====================================================================
        # 【步骤 6】保存完整日志到文件
        # ====================================================================

        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        debug_dir = os.path.join(THIS_DIR, f'debug_{seed}_{repo_bw}')
        os.makedirs(debug_dir, exist_ok=True)
        out_file = os.path.join(
            debug_dir,
            f'single_seed_seed{seed}_rb{repo_bw}_{timestamp}.log',
        )
        with open(out_file, 'w') as f:
            f.write(output)
        print(f'\nFull output saved to: {out_file}')
        print(f'（完整输出已保存到上述文件，包括所有 VNF 的详细信息）')

        # 打印输出的最后 30 行（通常包含 makespan 和资源统计）
        print(f'\n{"-"*70}')
        print(f'RAW OUTPUT (last 30 lines)（原始输出最后 30 行）')
        print(f'{"-"*70}')
        lines = output.split('\n')
        for line in lines[-30:]:
            if line.strip():
                print(line)

    except subprocess.TimeoutExpired:
        print(f'ERROR: Simulation timed out after {TIMEOUT} seconds')
        print(f'（错误：模拟超时，可以尝试增大 TIMEOUT 值）')
        sys.exit(1)
    except Exception as e:
        print(f'ERROR: {e}')
        sys.exit(1)
    finally:
        # 清理临时文件
        try:
            os.remove(tmp.name)
        except:
            pass

    print(f'\n{"="*70}\n')


if __name__ == '__main__':
    # ========================================================================
    # 【程序入口】
    # ========================================================================
    analyze()

    # ========================================================================
    # 【总结：如何修改参数】
    # ========================================================================
    #
    # 1️⃣  【最简单】改变 seed 和 repo_bw（命令行运行）
    #    $ python3 analyze_single_seed.py <seed> <repo_bw>
    #    例如：
    #      python3 analyze_single_seed.py 7476 60      # 分析最差情况
    #      python3 analyze_single_seed.py 9236 60      # 分析成功情况
    #      python3 analyze_single_seed.py 7476 480     # 尝试高带宽
    #
    # 2️⃣  【中等】改变其他基础参数（需编辑脚本）
    #    在 analyze() 函数中找到下面这行：
    #      base['repository_bw'] = str(repo_bw)
    #    在其后面加上（例如改 vnf_type_max）：
    #      base['vnf_type_max'] = '20'
    #      base['vnf_image_size_min'] = '1500'
    #    然后重新运行脚本
    #
    # 3️⃣  【改 MASTER_SEED】
    #    这个脚本只关心 seed（单个运行的随机数），不涉及 MASTER_SEED
    #    MASTER_SEED 是用来生成 seed 列表的（属于 run_experiment.py）
    #    如果要在这里用特定的 seed 列表，改 SEEDS = [7476, 9236, ...]
    #    但这个脚本设计是分析单个 seed，所以不需要 MASTER_SEED
    #
    # ========================================================================
