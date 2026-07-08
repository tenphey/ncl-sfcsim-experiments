#!/usr/bin/env python3
"""
Analyze E14 results: generate summary statistics and figures for the
Task-Type Diversity with Controlled Repetition Density experiment.

Usage:
  python3 analyze_results.py <result_folder>
  python3 analyze_results.py run_20260527_123000
"""

import os
import sys
import json
import glob
import shutil

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from scipy import stats

THIS_DIR = os.path.dirname(os.path.abspath(__file__))


def resolve_result_dir(arg):
    """Resolve result directory path (absolute, relative, or basename)."""
    if os.path.isdir(arg):
        return arg
    candidate = os.path.join(THIS_DIR, arg)
    if os.path.isdir(candidate):
        return candidate
    try:
        matches = [d for d in os.listdir(THIS_DIR)
                   if os.path.isdir(os.path.join(THIS_DIR, d)) and d.startswith(arg)]
        if len(matches) == 1:
            return os.path.join(THIS_DIR, matches[0])
        if len(matches) > 1:
            print(f"Multiple matching folders for '{arg}':")
            for m in matches:
                print('  ', m)
            raise SystemExit(1)
    except Exception:
        pass
    return None


def add_value_labels(ax, bars):
    for bar in bars:
        height = bar.get_height()
        ax.text(
            bar.get_x() + bar.get_width() / 2.0,
            height,
            f'{height:.1f}',
            ha='center',
            va='bottom',
            fontsize=10,
            fontweight='bold',
        )


def draw_table_image(display_df, title, out_path):
    fig_height = max(3.8, 0.55 * (len(display_df) + 2))
    fig, ax = plt.subplots(figsize=(17, fig_height))
    ax.axis("off")
    ax.set_title(title, fontsize=14, fontweight="bold", pad=14)

    table = ax.table(cellText=display_df.values, colLabels=display_df.columns, cellLoc="center", loc="center")
    table.auto_set_font_size(False)
    table.set_fontsize(9)
    table.scale(1.0, 1.45)

    for (row, col), cell in table.get_celld().items():
        cell.set_edgecolor("#666666")
        cell.set_linewidth(0.6)
        if row == 0:
            cell.set_facecolor("#DCEBFA")
            cell.set_text_props(weight="bold")
        else:
            cell.set_facecolor("#F8FBFF" if row % 2 == 0 else "#FFFFFF")

    plt.tight_layout()
    plt.savefig(out_path, dpi=300, bbox_inches="tight")
    plt.close()


def normalize_log_layout(result_dir):
    """
    Ensure run logs are stored under result_dir/logs.
    For backward compatibility, move legacy root logs into logs/.
    """
    logs_dir = os.path.join(result_dir, "logs")
    os.makedirs(logs_dir, exist_ok=True)

    moved = 0
    for name in os.listdir(result_dir):
        src = os.path.join(result_dir, name)
        if not os.path.isfile(src):
            continue
        if not (name.startswith("run_") and name.endswith(".log")):
            continue
        dst = os.path.join(logs_dir, name)
        try:
            shutil.move(src, dst)
            moved += 1
        except Exception:
            # Keep analysis robust even if one log cannot be moved.
            pass
    return moved


def resolve_log_path(result_dir, seed, vnf_type_max, sfc_vnf_num):
    """Resolve per-run log path under logs/ (supports both new and legacy patterns)."""
    logs_dir = os.path.join(result_dir, "logs")
    seed_i = int(seed)
    vtm_i = int(vnf_type_max)
    sfc_i = int(sfc_vnf_num)

    new_name = os.path.join(logs_dir, f"run_seed_{seed_i}_vtm_{vtm_i}_tasks_{sfc_i}.log")
    if os.path.exists(new_name):
        return new_name

    legacy_pattern = os.path.join(logs_dir, f"run_*_seed_{seed_i}_vtm_{vtm_i}_tasks_{sfc_i}.log")
    matches = sorted(glob.glob(legacy_pattern))
    if matches:
        return matches[0]

    return new_name


def read_log_meta(log_path):
    """Read lightweight log metadata used in loss-seed JSON."""
    if not os.path.exists(log_path):
        return {
            "log_file": None,
            "log_exists": False,
            "log_size_bytes": None,
            "log_readable": False,
        }
    try:
        size = os.path.getsize(log_path)
    except Exception:
        size = None
    readable = False
    try:
        # Read a tiny chunk to ensure the log is actually readable from logs/.
        with open(log_path, "rb") as f:
            _ = f.read(1)
        readable = True
    except Exception:
        readable = False
    return {
        "log_file": log_path,
        "log_exists": True,
        "log_size_bytes": size,
        "log_readable": readable,
    }


def main():
    if len(sys.argv) < 2:
        print('Usage: analyze_results.py <result_folder>')
        raise SystemExit(1)

    result_dir = resolve_result_dir(sys.argv[1])
    if not result_dir:
        print(f"Result folder not found: {sys.argv[1]}")
        print(f"Available run_* folders in {THIS_DIR}:")
        for d in sorted(os.listdir(THIS_DIR)):
            if os.path.isdir(os.path.join(THIS_DIR, d)) and d.startswith('run_'):
                print(f"  {d}")
        raise SystemExit(1)

    moved_logs = normalize_log_layout(result_dir)
    if moved_logs > 0:
        print(f"Moved {moved_logs} legacy log files into: {os.path.join(result_dir, 'logs')}")

    csv_path = os.path.join(result_dir, 'grid_e14_results.csv')
    if not os.path.exists(csv_path):
        print(f"CSV not found: {csv_path}")
        raise SystemExit(1)

    df = pd.read_csv(csv_path)
    required_cols = {'vnf_type_max', 'sfc_vnf_num', 'HEFT', 'DHEFT', 'NHEFT'}
    missing = required_cols - set(df.columns)
    if missing:
        raise SystemExit(f"Missing required columns: {sorted(missing)}")

    df = df[(df['HEFT'] > 0) & (df['DHEFT'] > 0) & (df['NHEFT'] > 0)]
    df['gain_N_over_D'] = (df['DHEFT'] - df['NHEFT']) / df['DHEFT'] * 100
    df['gain_D_over_H'] = (df['HEFT'] - df['DHEFT']) / df['HEFT'] * 100
    df['expected_tasks_per_type'] = df['sfc_vnf_num'] / df['vnf_type_max']

    grouped = df.groupby('vnf_type_max')
    summary_rows = []

    for vtm, group in grouped:
        n_runs = len(group)
        sfc_vnf_num = group['sfc_vnf_num'].iloc[0]
        expected_tasks_per_type = group['expected_tasks_per_type'].iloc[0]
        heft_mean = group['HEFT'].mean()
        heft_std = group['HEFT'].std()
        dheft_mean = group['DHEFT'].mean()
        dheft_std = group['DHEFT'].std()
        nheft_mean = group['NHEFT'].mean()
        nheft_std = group['NHEFT'].std()
        gain_mean = group['gain_N_over_D'].mean()
        gain_median = group['gain_N_over_D'].median()
        gain_trimmed = stats.trim_mean(group['gain_N_over_D'], 0.1)
        wins = (group['NHEFT'] < group['DHEFT']).sum()

        if n_runs >= 2:
            _, p_val = stats.ttest_rel(group['DHEFT'], group['NHEFT'])
            p_val = float(p_val)
            try:
                _, w_pval = stats.wilcoxon(group['DHEFT'], group['NHEFT'])
                w_pval = float(w_pval)
            except Exception:
                w_pval = np.nan
        else:
            p_val = np.nan
            w_pval = np.nan

        summary_rows.append({
            'vnf_type_max': int(vtm),
            'sfc_vnf_num': int(sfc_vnf_num),
            'expected_tasks_per_type': expected_tasks_per_type,
            'HEFT_mean': heft_mean,
            'HEFT_std': heft_std,
            'DHEFT_mean': dheft_mean,
            'DHEFT_std': dheft_std,
            'NHEFT_mean': nheft_mean,
            'NHEFT_std': nheft_std,
            'gain_N_over_D_mean': gain_mean,
            'gain_N_over_D_median': gain_median,
            'gain_N_over_D_trimmed': gain_trimmed,
            'wins_count': int(wins),
            'p_value': p_val,
            'wilcoxon_p': w_pval,
            'n_runs': n_runs,
        })

    summary_df = pd.DataFrame(summary_rows).sort_values('vnf_type_max')
    summary_csv = os.path.join(result_dir, 'grid_e14_summary.csv')
    summary_df.to_csv(summary_csv, index=False)

    # Build a vnf_type_max -> {seed -> execution details} JSON where NHEFT loses to DHEFT.
    if 'seed' not in df.columns:
        raise SystemExit("Missing required column: seed")
    loss_details_by_vtm = {}
    for vtm in sorted(df['vnf_type_max'].unique()):
        group = df[df['vnf_type_max'] == vtm]
        loss_group = group[group['NHEFT'] > group['DHEFT']].sort_values('seed')
        seed_map = {}
        for _, row in loss_group.iterrows():
            seed_key = str(int(row['seed']))
            dheft_val = float(row['DHEFT'])
            nheft_val = float(row['NHEFT'])
            sfc_vnf_num = int(row['sfc_vnf_num'])
            log_path = resolve_log_path(result_dir, row['seed'], row['vnf_type_max'], sfc_vnf_num)
            log_meta = read_log_meta(log_path)
            seed_map[seed_key] = {
                'HEFT': round(float(row['HEFT']), 6),
                'DHEFT': round(dheft_val, 6),
                'NHEFT': round(nheft_val, 6),
                'gain_N_over_D_percent': round(float(row['gain_N_over_D']), 6),
                'nheft_minus_dheft': round(nheft_val - dheft_val, 6),
                'vnf_type_max': int(row['vnf_type_max']),
                'sfc_vnf_num': sfc_vnf_num,
                'multiple_sfc_num': int(row['multiple_sfc_num']) if 'multiple_sfc_num' in row.index else None,
                'per_sfc_vnf_num': int(row['per_sfc_vnf_num']) if 'per_sfc_vnf_num' in row.index else None,
                'expected_tasks_per_type': float(row['expected_tasks_per_type']) if 'expected_tasks_per_type' in row.index else None,
                'time_sec': round(float(row['time_sec']), 6) if 'time_sec' in row.index else None,
                'log_file': os.path.relpath(log_meta['log_file'], result_dir) if log_meta['log_file'] else None,
                'log_exists': log_meta['log_exists'],
                'log_readable': log_meta['log_readable'],
                'log_size_bytes': log_meta['log_size_bytes'],
            }
        loss_details_by_vtm[str(int(vtm))] = seed_map

    loss_json_path = os.path.join(result_dir, 'e14_nheft_loss_seeds_by_vnf_type_max.json')
    with open(loss_json_path, 'w') as f:
        json.dump(loss_details_by_vtm, f, indent=2)

    print(f'\nSummary CSV: {summary_csv}')
    print(f'Loss-seeds JSON saved: {loss_json_path}')
    print('\n=== E14 Results by VNF Type Max ===')
    console_df = summary_df[['vnf_type_max', 'sfc_vnf_num', 'expected_tasks_per_type', 'DHEFT_mean', 'NHEFT_mean', 'gain_N_over_D_median', 'gain_N_over_D_mean', 'wins_count', 'p_value', 'n_runs']].copy()
    console_df['wins_count'] = console_df.apply(lambda row: f"{int(row['wins_count'])}/{int(row['n_runs'])}", axis=1)
    display_df = console_df.drop(columns=['n_runs']).copy()
    display_df['vnf_type_max'] = display_df['vnf_type_max'].map(lambda x: f"{int(x)}")
    display_df['sfc_vnf_num'] = display_df['sfc_vnf_num'].map(lambda x: f"{int(x)}")
    display_df['expected_tasks_per_type'] = display_df['expected_tasks_per_type'].map(lambda x: f"{float(x):.1f}")
    for col in ['DHEFT_mean', 'NHEFT_mean', 'gain_N_over_D_median', 'gain_N_over_D_mean']:
        display_df[col] = display_df[col].map(lambda x: f"{float(x):.6f}")
    display_df['p_value'] = display_df['p_value'].map(lambda x: "" if pd.isna(x) else f"{float(x):.6e}")
    print(console_df.drop(columns=['n_runs']).to_string(index=False))
    table_path = os.path.join(result_dir, 'e14_summary_table.png')
    draw_table_image(display_df, 'E14 Results by VNF Type Max', table_path)
    print(f'Summary table image saved: {table_path}')

    # Plot 1: Trend line for gain %
    fig, ax = plt.subplots(figsize=(12, 7))

    x = summary_df['vnf_type_max'].values
    gains_mean = summary_df['gain_N_over_D_mean'].values
    gains_median = summary_df['gain_N_over_D_median'].values
    gains_trimmed = summary_df['gain_N_over_D_trimmed'].values

    ax.plot(x, gains_median, marker='o', markersize=10, linewidth=2.5,
            label='NHEFT gain % (median, robust)', color='#06A77D', linestyle='-')
    ax.plot(x, gains_trimmed, marker='s', markersize=8, linewidth=2,
            label='NHEFT gain % (trimmed mean 10%-90%)', color='#A23B72', linestyle='--')
    ax.plot(x, gains_mean, marker='^', markersize=8, linewidth=1.5,
            label='NHEFT gain % (arithmetic mean, outlier-sensitive)', color='#F18F01', linestyle=':')
    ax.axhline(y=0, color='red', linestyle='--', alpha=0.5, linewidth=1)

    ax.set_xlabel('VNF Type Max / SFC Task Count', fontsize=13, fontweight='bold')
    ax.set_ylabel('NHEFT Gain % over DHEFT', fontsize=13, fontweight='bold')
    ax.set_title('E14 Experiment: Task-Type Diversity with Controlled Repetition Density',
                 fontsize=14, fontweight='bold')
    ax.grid(True, alpha=0.3, linestyle='--')
    ax.set_xticks(x)
    ax.set_xticklabels([f'{int(v)}\n({int(v) * 10})' for v in x], fontsize=12)

    for xm, gain_m in zip(x, gains_median):
        ax.text(xm, gain_m - 3, f'{gain_m:.1f}%', ha='center', fontsize=9, fontweight='bold', color='#06A77D')

    ax.legend(fontsize=11, loc='best')
    plt.tight_layout()

    chart_path = os.path.join(result_dir, 'e14_gain_trend.png')
    plt.savefig(chart_path, dpi=300, bbox_inches='tight')
    plt.close()
    print(f'Chart saved: {chart_path}')

    # Plot 2: Grouped bar chart for average makespan
    fig, ax = plt.subplots(figsize=(12, 7))

    labels = summary_df['vnf_type_max'].astype(str).values
    dheft_means = summary_df['DHEFT_mean'].values
    nheft_means = summary_df['NHEFT_mean'].values

    x_pos = np.arange(len(labels))
    bar_width = 0.35

    bars1 = ax.bar(x_pos - bar_width / 2, dheft_means, bar_width,
                   label='DHEFT', color='#FF6B6B', alpha=0.85,
                   edgecolor='black', linewidth=1.0)
    bars2 = ax.bar(x_pos + bar_width / 2, nheft_means, bar_width,
                   label='NHEFT', color='#06A77D', alpha=0.85,
                   edgecolor='black', linewidth=1.0)

    ax.set_xlabel('VNF Type Max / SFC Task Count', fontsize=13, fontweight='bold')
    ax.set_ylabel('Average Makespan (seconds)', fontsize=13, fontweight='bold')
    ax.set_title('E14 Experiment: DHEFT vs NHEFT Makespan by VNF Type Max',
                 fontsize=14, fontweight='bold')
    ax.set_xticks(x_pos)
    ax.set_xticklabels([f'{label}\n({int(label) * 10})' for label in labels], fontsize=12)
    ax.legend(fontsize=12, loc='best')
    ax.grid(True, alpha=0.3, axis='y', linestyle='--')

    add_value_labels(ax, bars1)
    add_value_labels(ax, bars2)

    plt.tight_layout()
    chart_path_bar = os.path.join(result_dir, 'e14_makespan_comparison.png')
    plt.savefig(chart_path_bar, dpi=300, bbox_inches='tight')
    plt.close()
    print(f'Grouped bar chart saved: {chart_path_bar}')


if __name__ == '__main__':
    main()
