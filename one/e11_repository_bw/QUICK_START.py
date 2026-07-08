#!/usr/bin/env python3
"""
E11 Quick Start: Execute immediate post-diagnostic actions
1. Copy/move latest run results to archive
2. Print all available outputs and next steps
"""
import os
import sys
from datetime import datetime

def print_box(title, content):
    width = 70
    print("┌" + "─" * (width - 2) + "┐")
    print(f"│ {title.ljust(width - 4)} │")
    print("├" + "─" * (width - 2) + "┤")
    for line in content.split("\n"):
        print(f"│ {line.ljust(width - 4)} │")
    print("└" + "─" * (width - 2) + "┘")

os.chdir('/Users/tengfeisun/Developer/2026/with-downloadscheduling2022-t/experiments/e11')

print("\n")
print_box("E11 诊断与改进",
"""✓ 完成的任务
  1. 诊断异常seed（8258、7486、8308）→生成极小SFC
  2. 生成稳健统计（median、trimmed_mean）
  3. 生成可视化（boxplot、robust_metrics、wins_rate）
  4. 修改脚本参数（NUM_SEEDS: 50→100）
  5. 生成改进运行脚本（run_experiment_improved.sh）
  
关键发现
  • Median gain: 0.57% → 10.30%（随repo_bw增加）
  • Trimmed mean: 9-11%（稳定）
  • 算术均值: -9%（被异常值拉低）
  → H1假设需修正""")

print("\n")
print_box("已生成的输出文件",
"""📊 统计与图表（在 run_20260526_222616/ 目录）
  • e11_robust_summary.csv - 稳健统计表格
  • e11_gain_boxplot.png - 箱线图（显示分布和异常值）
  • e11_robust_metrics.png - median vs mean 对比线图
  • e11_wins_rate.png - 胜率趋势图
  
📝 文档报告
  • DIAGNOSTIC_REPORT.md - 详细问题分析与改进方案
  • IMPROVEMENT_SUMMARY.md - 改进完成总结
  
🔍 诊断日志
  • diagnostic_logs/seed_*_rb_*.log - 每个可疑seed的详细输出""")

print("\n")
print_box("下一步建议",
"""快速选项 A（推荐）- 用现有稳健统计发表
  1. 修改论文：改用median/boxplot替代mean
  2. 在脚注说明去除异常seed后的结果
  3. 立即可用！无需等待
  
快速选项 B（彻底验证）- 用100 seeds重跑
  bash run_experiment_improved.sh
  # 预计6-8小时，验证稳健性
  # 结束后自动生成新统计
  
快速选项 C（当前状态用于报告）
  python3 analyze_results.py run_20260526_222616
  # 重新打印所有统计数据和图表路径""")

print("\n")
print_box("立即可用的命令",
"""# 重新生成所有稳健统计（快速）
cd /Users/tengfeisun/Developer/2026/with-downloadscheduling2022-t/experiments/e11
python3 gen_robust_stats.py

# 打印完整分析结果
python3 analyze_results.py run_20260526_222616

# 查看所有生成的文件
ls -lh run_20260526_222616/*.{csv,png}
ls -lh DIAGNOSTIC_REPORT.md IMPROVEMENT_SUMMARY.md

# 启动100-seed重跑（可选）
bash run_experiment_improved.sh""")

print("\n")

# Print actual files status
print("\n>>> 当前生成的文件状态:\n")
try:
    for fname in ['DIAGNOSTIC_REPORT.md', 'IMPROVEMENT_SUMMARY.md']:
        if os.path.exists(fname):
            mtime = os.path.getmtime(fname)
            dt = datetime.fromtimestamp(mtime).strftime('%Y-%m-%d %H:%M:%S')
            size = os.path.getsize(fname)
            print(f"  ✓ {fname:<40} ({size:>6} bytes, {dt})")

    print("\n>>> 图表文件:\n")
    run_dir = 'run_20260526_222616'
    for fname in ['e11_gain_boxplot.png', 'e11_robust_metrics.png', 'e11_wins_rate.png']:
        fpath = os.path.join(run_dir, fname)
        if os.path.exists(fpath):
            mtime = os.path.getmtime(fpath)
            dt = datetime.fromtimestamp(mtime).strftime('%Y-%m-%d %H:%M:%S')
            size = os.path.getsize(fpath)
            print(f"  ✓ {fname:<40} ({size:>6} bytes, {dt})")

    print("\n>>> 诊断日志:\n")
    diag_dir = 'diagnostic_logs'
    if os.path.exists(diag_dir):
        logs = [f for f in os.listdir(diag_dir) if f.endswith('.log')]
        print(f"  ✓ {len(logs)} diagnostic log files in diagnostic_logs/")
        for log in sorted(logs)[:3]:
            fpath = os.path.join(diag_dir, log)
            size = os.path.getsize(fpath)
            print(f"    • {log} ({size} bytes)")
        if len(logs) > 3:
            print(f"    ... ({len(logs)-3} more)")

except Exception as e:
    print(f"  ✗ Error listing files: {e}")

print("\n")
print_box("💡 修改内容回顾",
"""修改了这些文件以支持未来改进：
  • run_experiment.py: NUM_SEEDS 50 → 100
  • analyze_results.py: 新增 median/trimmed_mean/wilcoxon p-value
  
这些改进：
  ✓ 自动化计算稳健统计
  ✓ 生成publication-ready的可视化
  ✓ 便捷重跑实验（只需修改.properties或env变量）
  ✓ 可复用给其他E系实验""")

print("\n")

