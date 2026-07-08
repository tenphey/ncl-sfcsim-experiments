#!/usr/bin/env python3
"""
Generate robust statistics and visualizations from E11 raw CSV.
Outputs: boxplot, median/trimmed-mean line plot, robust summary CSV.
"""
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from scipy import stats
import os

# Read data
csv_path = 'run_20260526_222616/grid_e11_results.csv'
df = pd.read_csv(csv_path)

# Clean: remove zeros
df_clean = df[(df['DHEFT'] > 0) & (df['NHEFT'] > 0)]

# Compute per-run gain
df_clean['gain_pct'] = (df_clean['DHEFT'] - df_clean['NHEFT']) / df_clean['DHEFT'] * 100

# Group by repo_bw and compute robust stats
robust_rows = []
gains_by_bw = {}

for rb, group in df_clean.groupby('repo_bw'):
    gains = group['gain_pct'].values
    gains_by_bw[rb] = gains

    mean_val = np.mean(gains)
    median_val = np.median(gains)
    trimmed_val = stats.trim_mean(gains, 0.1)  # trim 10% from each tail
    std_val = np.std(gains)

    wins = (group['NHEFT'] < group['DHEFT']).sum()
    n_runs = len(group)

    # Tests
    t_stat, t_pval = stats.ttest_rel(group['DHEFT'], group['NHEFT'], nan_policy='omit')
    try:
        w_stat, w_pval = stats.wilcoxon(group['DHEFT'], group['NHEFT'])
    except:
        w_pval = np.nan

    dheft_mean = group['DHEFT'].mean()
    nheft_mean = group['NHEFT'].mean()

    robust_rows.append({
        'repo_bw': int(rb),
        'DHEFT_mean': round(dheft_mean, 4),
        'NHEFT_mean': round(nheft_mean, 4),
        'gain_mean': round(mean_val, 4),
        'gain_median': round(median_val, 4),
        'gain_trimmed_mean': round(trimmed_val, 4),
        'gain_std': round(std_val, 4),
        'wins_count': int(wins),
        'n_runs': int(n_runs),
        'paired_t_pval': round(t_pval, 6),
        'wilcoxon_pval': round(w_pval, 6) if not np.isnan(w_pval) else np.nan,
    })

robust_df = pd.DataFrame(robust_rows)
robust_df.to_csv('run_20260526_222616/e11_robust_summary.csv', index=False)

print("\n=== E11 ROBUST SUMMARY ===")
print(robust_df.to_string(index=False))
print(f"\nRobust summary saved to: run_20260526_222616/e11_robust_summary.csv")

# Plot 1: Boxplot
fig, ax = plt.subplots(figsize=(12, 6))
bw_values = sorted(robust_rows, key=lambda x: x['repo_bw'])
bw_labels = [str(x['repo_bw']) for x in bw_values]
gains_list = [gains_by_bw[x['repo_bw']] for x in bw_values]

bp = ax.boxplot(gains_list, labels=bw_labels, patch_artist=True)
for patch in bp['boxes']:
    patch.set_facecolor('#B0E0E6')
    patch.set_alpha(0.7)

ax.set_xlabel('Repository Bandwidth (MBps)', fontsize=12, fontweight='bold')
ax.set_ylabel('NHEFT Gain % over DHEFT', fontsize=12, fontweight='bold')
ax.set_title('E11: Distribution of NHEFT Gain by Repository Bandwidth (Boxplot)', fontsize=13, fontweight='bold')
ax.grid(True, alpha=0.3, axis='y')
ax.axhline(y=0, color='red', linestyle='--', alpha=0.5, label='Break-even (0%)')

# Add wins_count as text
for i, x in enumerate(bw_values):
    ax.text(i + 1, ax.get_ylim()[1] * 0.9, f"wins: {x['wins_count']}/50",
            ha='center', fontsize=10, bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))

ax.legend()
plt.tight_layout()
plt.savefig('run_20260526_222616/e11_gain_boxplot.png', dpi=300, bbox_inches='tight')
plt.close()
print(f"Boxplot saved to: run_20260526_222616/e11_gain_boxplot.png")

# Plot 2: Line plot (median + trimmed mean)
fig, ax = plt.subplots(figsize=(12, 7))
bw_vals = robust_df['repo_bw'].values
medians = robust_df['gain_median'].values
trimmed = robust_df['gain_trimmed_mean'].values
means = robust_df['gain_mean'].values

ax.plot(bw_vals, medians, marker='o', linewidth=2.5, markersize=10,
        label='Median Gain %', color='#2E86AB')
ax.plot(bw_vals, trimmed, marker='s', linewidth=2.5, markersize=8,
        label='Trimmed Mean (10%-90%)', color='#A23B72', linestyle='--')
ax.plot(bw_vals, means, marker='^', linewidth=2, markersize=8,
        label='Arithmetic Mean (affected by outliers)', color='#F18F01', linestyle=':')

ax.axhline(y=0, color='red', linestyle='--', alpha=0.5, linewidth=1)
ax.set_xlabel('Repository Bandwidth (MBps)', fontsize=12, fontweight='bold')
ax.set_ylabel('NHEFT Gain % over DHEFT', fontsize=12, fontweight='bold')
ax.set_title('E11: Robust Metrics—Median vs Trimmed Mean vs Arithmetic Mean', fontsize=13, fontweight='bold')
ax.grid(True, alpha=0.3)
ax.set_xticks(bw_vals)
ax.legend(fontsize=11, loc='best')
plt.tight_layout()
plt.savefig('run_20260526_222616/e11_robust_metrics.png', dpi=300, bbox_inches='tight')
plt.close()
print(f"Robust metrics plot saved to: run_20260526_222616/e11_robust_metrics.png")

# Plot 3: Wins count trend
fig, ax = plt.subplots(figsize=(10, 6))
wins = robust_df['wins_count'].values
n_runs = robust_df['n_runs'].values
win_rate = wins / n_runs * 100

ax.bar(bw_vals, win_rate, width=50, color='#06A77D', alpha=0.7, edgecolor='black', linewidth=1.5)
ax.axhline(y=50, color='red', linestyle='--', alpha=0.7, linewidth=2, label='50% threshold (random)')
ax.set_xlabel('Repository Bandwidth (MBps)', fontsize=12, fontweight='bold')
ax.set_ylabel('NHEFT Win Rate (%)', fontsize=12, fontweight='bold')
ax.set_title('E11: NHEFT Win Rate—How Often NHEFT < DHEFT', fontsize=13, fontweight='bold')
ax.set_ylim([0, 100])
ax.set_xticks(bw_vals)
ax.grid(True, alpha=0.3, axis='y')
ax.legend(fontsize=11)

# Annotate bars
for i, (bw, wr) in enumerate(zip(bw_vals, win_rate)):
    ax.text(bw, wr + 2, f'{int(wins[i])}/{int(n_runs[i])}\n{wr:.1f}%',
            ha='center', fontsize=10, fontweight='bold')

plt.tight_layout()
plt.savefig('run_20260526_222616/e11_wins_rate.png', dpi=300, bbox_inches='tight')
plt.close()
print(f"Wins rate plot saved to: run_20260526_222616/e11_wins_rate.png")

print("\n✓ All robust visualizations generated.")

