#!/usr/bin/env python3
"""
Aggregate latest runs of e41-e48 and draw one grouped makespan bar chart.

Output folder:
  experiments/e41_e48/<timestamp>/

Usage:
  python3 experiments/analyze_e4x.py
"""

import os
from datetime import datetime

THIS_DIR = os.path.dirname(os.path.abspath(__file__))
CACHE_DIR = os.path.join(THIS_DIR, ".plot_cache")
os.makedirs(CACHE_DIR, exist_ok=True)
os.environ.setdefault("MPLCONFIGDIR", CACHE_DIR)
os.environ.setdefault("XDG_CACHE_HOME", CACHE_DIR)

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import re


OUT_BASE_DIR = os.path.join(THIS_DIR, "e41_e48")
PROJECT_ROOT = os.path.dirname(THIS_DIR)

SCENARIOS = [
    {"exp_dir": "e41", "label": "(0.10, 0.18]", "summary_csv": "grid_e41_summary.csv", "scenario": "b41", "constraint": "CCR < IDR, rel gap >= 20%"},
    {"exp_dir": "e42", "label": "(0.18, 0.32]", "summary_csv": "grid_e42_summary.csv", "scenario": "b42", "constraint": "CCR < IDR, rel gap >= 20%"},
    {"exp_dir": "e43", "label": "(0.32, 0.56]", "summary_csv": "grid_e43_summary.csv", "scenario": "b43", "constraint": "CCR < IDR, rel gap >= 20%"},
    {"exp_dir": "e44", "label": "(0.56, 1.00]", "summary_csv": "grid_e44_summary.csv", "scenario": "b44", "constraint": "CCR < IDR, rel gap >= 20%"},
    {"exp_dir": "e45", "label": "(1.00, 1.78]", "summary_csv": "grid_e45_summary.csv", "scenario": "b45", "constraint": "CCR < IDR, rel gap >= 20%"},
    {"exp_dir": "e46", "label": "(1.78, 3.16]", "summary_csv": "grid_e46_summary.csv", "scenario": "b46", "constraint": "CCR < IDR, rel gap >= 20%"},
    {"exp_dir": "e47", "label": "(3.16, 5.62]", "summary_csv": "grid_e47_summary.csv", "scenario": "b47", "constraint": "CCR < IDR, rel gap >= 20%"},
    {"exp_dir": "e48", "label": "(5.62, 10.00]", "summary_csv": "grid_e48_summary.csv", "scenario": "b48", "constraint": "CCR < IDR, rel gap >= 20%"},
]

ALGO_COLORS = {
    "HEFT": "#4E79A7",
    "DHEFT": "#FF6B6B",
    "NHEFT": "#06A77D",
}

# Hidden switch: control whether the HEFT bar is shown in
# makespan_mean_comparison.png. Default is True.
SHOW_HEFT_BAR = False

# Hidden switch: add extra negative margin to the gain axis so the 0% baseline
# sits higher and the gain line is less likely to overlap the bar area.
GAIN_ZERO_LIFT_RATIO = 0.35

# Hidden switch: add headroom above the win-rate axis so 100% points do not
# stick to the top frame of the chart.
WIN_RATE_AXIS_MAX = 105.0

# Font sizes for aggregated charts.
AXIS_LABEL_FONTSIZE = 22
TITLE_FONTSIZE = 32
XTICK_FONTSIZE = 18
YTICK_FONTSIZE = 18
BAR_LABEL_FONTSIZE = 18
LINE_ANNOTATION_FONTSIZE = 18
FOOTNOTE_FONTSIZE = 18
LEGEND_FONTSIZE = 17

# Bar-label layout controls for horizontal labels.
BAR_LABEL_BASE_Y_OFFSET = 6
BAR_LABEL_X_OFFSET_POINTS = 12
BAR_LABEL_CLOSE_HEIGHT_THRESHOLD_RATIO = 0.035
BAR_LABEL_CLOSE_EXTRA_Y_OFFSET = 14

DHEFT_VCPU_RE = re.compile(r"\[DHEFT\]SLR:.*?# of vCPUs:\s*(\d+)")
NHEFT_VCPU_RE = re.compile(r"\[NHEFT\]SLR:.*?# of vCPUs:\s*(\d+)")


def find_latest_run_dir(exp_abs_dir):
    run_dirs = []
    for name in os.listdir(exp_abs_dir):
        path = os.path.join(exp_abs_dir, name)
        if os.path.isdir(path) and name.startswith("run_"):
            run_dirs.append(path)
    if not run_dirs:
        return None
    run_dirs.sort(key=lambda p: os.path.getmtime(p), reverse=True)
    return run_dirs[0]


def ensure_float(v, default=np.nan):
    try:
        return float(v)
    except Exception:
        return default


def rel_to_project(path):
    try:
        return os.path.relpath(str(path), PROJECT_ROOT)
    except Exception:
        return str(path)


def find_qualified_col(columns, scenario):
    exact = f"{scenario}_qualified_runs"
    if exact in columns:
        return exact
    for c in columns:
        if c.endswith("_qualified_runs"):
            return c
    return None


def find_qualified_rate_col(columns, scenario):
    exact = f"{scenario}_qualified_rate_in_algo_valid"
    if exact in columns:
        return exact
    for c in columns:
        if c.endswith("_qualified_rate_in_algo_valid"):
            return c
    return None


def find_match_col(columns, scenario):
    exact = f"{scenario}_match"
    if exact in columns:
        return exact
    for c in columns:
        if c.endswith("_match"):
            return c
    return None


def parse_used_vcpus_from_log(log_path):
    if not os.path.exists(log_path):
        return np.nan, np.nan

    dheft_vcpu = np.nan
    nheft_vcpu = np.nan
    try:
        with open(log_path, "r", errors="ignore") as f:
            for line in f:
                if np.isnan(dheft_vcpu):
                    m = DHEFT_VCPU_RE.search(line)
                    if m:
                        dheft_vcpu = float(m.group(1))
                if np.isnan(nheft_vcpu):
                    m = NHEFT_VCPU_RE.search(line)
                    if m:
                        nheft_vcpu = float(m.group(1))
                if not np.isnan(dheft_vcpu) and not np.isnan(nheft_vcpu):
                    break
    except Exception:
        return np.nan, np.nan
    return dheft_vcpu, nheft_vcpu


def annotate_grouped_bar_values(ax, containers, value_arrays, ymax):
    if not containers:
        return

    n_series = len(containers)
    if n_series == 1:
        x_offsets = [0]
    elif n_series == 2:
        x_offsets = [-BAR_LABEL_X_OFFSET_POINTS, BAR_LABEL_X_OFFSET_POINTS]
    else:
        x_offsets = [-BAR_LABEL_X_OFFSET_POINTS, 0, BAR_LABEL_X_OFFSET_POINTS]

    close_threshold = ymax * BAR_LABEL_CLOSE_HEIGHT_THRESHOLD_RATIO
    n_groups = len(value_arrays[0]) if value_arrays else 0

    for i in range(n_groups):
        heights = [float(values[i]) for values in value_arrays]
        y_offsets = [BAR_LABEL_BASE_Y_OFFSET] * n_series

        if max(heights) - min(heights) <= close_threshold:
            order = sorted(range(n_series), key=lambda idx: heights[idx])
            for rank, idx in enumerate(order):
                y_offsets[idx] += rank * BAR_LABEL_CLOSE_EXTRA_Y_OFFSET

        for series_idx, container in enumerate(containers):
            patch = container.patches[i]
            x = patch.get_x() + patch.get_width() / 2.0
            y = patch.get_height()
            ax.annotate(
                f"{heights[series_idx]:.2f}",
                (x, y),
                textcoords="offset points",
                xytext=(x_offsets[min(series_idx, len(x_offsets) - 1)], y_offsets[series_idx]),
                ha="center",
                va="bottom",
                fontsize=BAR_LABEL_FONTSIZE,
                rotation=0,
                clip_on=False,
            )


def load_latest_summaries():
    rows = []
    for spec in SCENARIOS:
        exp_abs_dir = os.path.join(THIS_DIR, spec["exp_dir"])
        latest_run = find_latest_run_dir(exp_abs_dir)
        if latest_run is None:
            raise RuntimeError(f"No run_* folder found under {exp_abs_dir}")

        summary_path = os.path.join(latest_run, spec["summary_csv"])
        if not os.path.exists(summary_path):
            raise RuntimeError(f"Summary CSV not found: {summary_path}")

        df = pd.read_csv(summary_path)
        if len(df) != 1:
            raise RuntimeError(f"Expected exactly one summary row in {summary_path}")
        row = df.iloc[0]

        qualified_col = find_qualified_col(df.columns, spec["scenario"])
        qualified_rate_col = find_qualified_rate_col(df.columns, spec["scenario"])
        if qualified_col is None or qualified_rate_col is None:
            raise RuntimeError(f"Could not find qualified-run columns in {summary_path}")

        seed_metrics_path = os.path.join(latest_run, f"{spec['exp_dir']}_seed_metrics_with_{spec['scenario']}_flag.csv")
        if not os.path.exists(seed_metrics_path):
            raise RuntimeError(f"Seed metrics CSV not found: {seed_metrics_path}")

        seed_df = pd.read_csv(seed_metrics_path)
        match_col = find_match_col(seed_df.columns, spec["scenario"])
        if match_col is None:
            raise RuntimeError(f"Could not find match column in {seed_metrics_path}")

        qualified_seed_df = seed_df[
            (seed_df["HEFT"] > 0)
            & (seed_df["DHEFT"] > 0)
            & (seed_df["NHEFT"] > 0)
            & (seed_df[match_col] == True)
        ].copy()

        dheft_vcpu_vals = []
        nheft_vcpu_vals = []
        logs_dir = os.path.join(latest_run, "logs")
        for _, seed_row in qualified_seed_df.iterrows():
            seed = int(seed_row["seed"])
            log_path = os.path.join(logs_dir, f"run_seed_{seed}.log")
            dheft_vcpu, nheft_vcpu = parse_used_vcpus_from_log(log_path)
            if not np.isnan(dheft_vcpu):
                dheft_vcpu_vals.append(dheft_vcpu)
            if not np.isnan(nheft_vcpu):
                nheft_vcpu_vals.append(nheft_vcpu)

        rows.append(
            {
                "exp_dir": spec["exp_dir"],
                "scenario": spec["scenario"],
                "bucket_label": spec["label"],
                "constraint": spec["constraint"],
                "latest_run_dir": latest_run,
                "latest_run_rel": rel_to_project(latest_run),
                "summary_csv_rel": rel_to_project(summary_path),
                "total_runs": int(row["total_runs"]),
                "algo_valid_runs": int(row["algo_valid_runs"]),
                "qualified_runs": int(row[qualified_col]),
                "qualified_rate": ensure_float(row[qualified_rate_col]),
                "HEFT_mean": ensure_float(row["HEFT_mean"]),
                "DHEFT_mean": ensure_float(row["DHEFT_mean"]),
                "NHEFT_mean": ensure_float(row["NHEFT_mean"]),
                "gain_N_over_D_mean": ensure_float(row["gain_N_over_D_mean"]),
                "gain_N_over_D_median": ensure_float(row["gain_N_over_D_median"]),
                "win_rate_N_over_D": ensure_float(row["win_rate_N_over_D"]),
                "DHEFT_used_vcpu_mean": float(np.mean(dheft_vcpu_vals)) if dheft_vcpu_vals else np.nan,
                "NHEFT_used_vcpu_mean": float(np.mean(nheft_vcpu_vals)) if nheft_vcpu_vals else np.nan,
                "ttest_p": ensure_float(row["ttest_p_DHEFT_vs_NHEFT"]),
                "wilcoxon_p": ensure_float(row["wilcoxon_p_DHEFT_vs_NHEFT"]),
            }
        )
    return pd.DataFrame(rows)


def draw_grouped_bar_chart(df, out_path):
    fig, ax = plt.subplots(figsize=(20, 10))

    x = np.arange(len(df))
    width = 0.23 if SHOW_HEFT_BAR else 0.30

    heft_vals = df["HEFT_mean"].to_numpy()
    dheft_vals = df["DHEFT_mean"].to_numpy()
    nheft_vals = df["NHEFT_mean"].to_numpy()
    win_rate_vals = (df["win_rate_N_over_D"].to_numpy(dtype=float)) * 100.0
    gain_vals = df["gain_N_over_D_mean"].to_numpy(dtype=float)

    bar_heft = None
    if SHOW_HEFT_BAR:
        bar_heft = ax.bar(x - width, heft_vals, width, label="HEFT", color=ALGO_COLORS["HEFT"], edgecolor="black", linewidth=0.8)
        bar_dheft = ax.bar(x, dheft_vals, width, label="DHEFT", color=ALGO_COLORS["DHEFT"], edgecolor="black", linewidth=0.8)
        bar_nheft = ax.bar(x + width, nheft_vals, width, label="NHEFT", color=ALGO_COLORS["NHEFT"], edgecolor="black", linewidth=0.8)
    else:
        bar_dheft = ax.bar(x - width / 2, dheft_vals, width, label="DHEFT", color=ALGO_COLORS["DHEFT"], edgecolor="black", linewidth=0.8)
        bar_nheft = ax.bar(x + width / 2, nheft_vals, width, label="NHEFT", color=ALGO_COLORS["NHEFT"], edgecolor="black", linewidth=0.8)

    ymax_candidates = [np.max(dheft_vals), np.max(nheft_vals)]
    if SHOW_HEFT_BAR:
        ymax_candidates.append(np.max(heft_vals))
    ymax = max(ymax_candidates)
    ax.set_ylim(0, ymax * 1.50 if ymax > 0 else 1.0)
    ax.set_ylabel("Mean Makespan", fontsize=AXIS_LABEL_FONTSIZE)
    ax.set_xlabel("NCCR Bucket", fontsize=AXIS_LABEL_FONTSIZE)
    ax.set_title("E41-E48 Makespan Mean Comparison", fontsize=TITLE_FONTSIZE, fontweight="bold", pad=16)
    ax.set_xticks(x)
    ax.set_xticklabels(df["bucket_label"].tolist(), rotation=0, fontsize=XTICK_FONTSIZE)
    ax.tick_params(axis="y", labelsize=YTICK_FONTSIZE)
    ax.grid(axis="y", linestyle="--", alpha=0.35)
    ax.set_axisbelow(True)

    label_containers = [bar_dheft, bar_nheft]
    label_values = [dheft_vals, nheft_vals]
    if SHOW_HEFT_BAR and bar_heft is not None:
        label_containers.insert(0, bar_heft)
        label_values.insert(0, heft_vals)
    annotate_grouped_bar_values(ax, label_containers, label_values, ymax)

    ax2 = ax.twinx()
    win_line, = ax2.plot(
        x,
        win_rate_vals,
        color="#F39C12",
        marker="o",
        markersize=7,
        linewidth=2.5,
        label="NHEFT Win Rate",
    )
    ax2.set_ylim(0, WIN_RATE_AXIS_MAX)
    ax2.set_ylabel("Win Rate (%)", color="#F39C12", fontsize=AXIS_LABEL_FONTSIZE)
    ax2.tick_params(axis="y", colors="#F39C12", labelsize=YTICK_FONTSIZE)
    for xi, yi in zip(x, win_rate_vals):
        ax2.annotate(f"{yi:.1f}%", (xi, yi), textcoords="offset points", xytext=(0, -18), ha="center", color="#F39C12", fontsize=LINE_ANNOTATION_FONTSIZE)

    ax3 = ax.twinx()
    ax3.spines["right"].set_position(("outward", 70))
    gain_min = min(0.0, float(np.nanmin(gain_vals)))
    gain_max = float(np.nanmax(gain_vals))
    gain_span = max(1.0, gain_max - gain_min)
    lower_gain_bound = min(gain_min - gain_span * 0.10, -gain_span * GAIN_ZERO_LIFT_RATIO)
    ax3.set_ylim(lower_gain_bound, gain_max + gain_span * 0.20)
    gain_line, = ax3.plot(
        x,
        gain_vals,
        color="#8E44AD",
        marker="o",
        markersize=7,
        linewidth=2.5,
        label="NHEFT Gain over DHEFT",
    )
    ax3.set_ylabel("Gain (%)", color="#8E44AD", fontsize=AXIS_LABEL_FONTSIZE)
    ax3.tick_params(axis="y", colors="#8E44AD", labelsize=YTICK_FONTSIZE)
    for xi, yi in zip(x, gain_vals):
        ax3.annotate(f"{yi:.1f}%", (xi, yi), textcoords="offset points", xytext=(0, 10), ha="center", color="#8E44AD", fontsize=LINE_ANNOTATION_FONTSIZE)

    if SHOW_HEFT_BAR and bar_heft is not None:
        legend_handles = [bar_heft, bar_dheft, bar_nheft, win_line, gain_line]
        legend_labels = ["HEFT", "DHEFT", "NHEFT", "NHEFT Win Rate", "NHEFT Gain over DHEFT"]
    else:
        legend_handles = [bar_dheft, bar_nheft, win_line, gain_line]
        legend_labels = ["DHEFT", "NHEFT", "NHEFT Win Rate", "NHEFT Gain over DHEFT"]
    legend = ax.legend(
        legend_handles,
        legend_labels,
        loc="upper left",
        ncol=3,
        frameon=True,
        fontsize=LEGEND_FONTSIZE,
    )
    legend.get_frame().set_alpha(0.95)

    fig.text(
        0.5,
        0.02,
        "Target family: CCR_data < IDR_image   |   all e41-e48 bins use relative CCR/IDR gap >= 20%",
        ha="center",
        fontsize=FOOTNOTE_FONTSIZE,
    )

    plt.tight_layout(rect=[0.02, 0.06, 0.93, 0.95])
    plt.savefig(out_path, dpi=300, bbox_inches="tight")
    plt.close(fig)


def draw_vcpu_usage_chart(df, out_path):
    fig, ax = plt.subplots(figsize=(18, 9))

    x = np.arange(len(df))
    width = 0.34

    dheft_vals = df["DHEFT_used_vcpu_mean"].to_numpy(dtype=float)
    nheft_vals = df["NHEFT_used_vcpu_mean"].to_numpy(dtype=float)

    bar_dheft = ax.bar(
        x - width / 2,
        dheft_vals,
        width,
        label="DHEFT",
        color=ALGO_COLORS["DHEFT"],
        edgecolor="black",
        linewidth=0.8,
    )
    bar_nheft = ax.bar(
        x + width / 2,
        nheft_vals,
        width,
        label="NHEFT",
        color=ALGO_COLORS["NHEFT"],
        edgecolor="black",
        linewidth=0.8,
    )

    ymax = max(np.nanmax(dheft_vals), np.nanmax(nheft_vals))
    ax.set_ylim(0, ymax * 1.20 if ymax > 0 else 1.0)
    ax.set_ylabel("Mean Used vCPUs", fontsize=AXIS_LABEL_FONTSIZE)
    ax.set_xlabel("NCCR Bucket", fontsize=AXIS_LABEL_FONTSIZE)
    ax.set_title("E41-E48 vCPU Usage Comparison", fontsize=TITLE_FONTSIZE, fontweight="bold", pad=16)
    ax.set_xticks(x)
    ax.set_xticklabels(df["bucket_label"].tolist(), rotation=0, fontsize=XTICK_FONTSIZE)
    ax.tick_params(axis="y", labelsize=YTICK_FONTSIZE)
    ax.grid(axis="y", linestyle="--", alpha=0.35)
    ax.set_axisbelow(True)

    annotate_grouped_bar_values(ax, [bar_dheft, bar_nheft], [dheft_vals, nheft_vals], ymax)

    legend = ax.legend(loc="upper left", ncol=2, frameon=True, fontsize=LEGEND_FONTSIZE)
    legend.get_frame().set_alpha(0.95)

    fig.text(
        0.5,
        0.02,
        "Values are mean used vCPU counts over qualified runs in each NCCR bucket",
        ha="center",
        fontsize=FOOTNOTE_FONTSIZE,
    )

    plt.tight_layout(rect=[0.02, 0.06, 0.98, 0.95])
    plt.savefig(out_path, dpi=300, bbox_inches="tight")
    plt.close(fig)


def build_summary_text(df):
    lines = []
    lines.append("E41-E48 Aggregated Summary")
    lines.append("")
    lines.append("This aggregation uses the latest run_* folder under each experiment directory.")
    lines.append("")
    lines.append("Runs used:")
    for _, row in df.iterrows():
        lines.append(f"- {row['exp_dir']}: {row['latest_run_rel']}")
    lines.append("")
    lines.append("Bucket overview:")
    for _, row in df.iterrows():
        lines.append(
            "- "
            f"{row['exp_dir']} {row['bucket_label']}: "
            f"qualified={row['qualified_runs']}/{row['algo_valid_runs']} "
            f"({row['qualified_rate'] * 100:.2f}%), "
            f"HEFT_mean={row['HEFT_mean']:.4f}, "
            f"DHEFT_mean={row['DHEFT_mean']:.4f}, "
            f"NHEFT_mean={row['NHEFT_mean']:.4f}, "
            f"DHEFT_used_vCPU_mean={row['DHEFT_used_vcpu_mean']:.2f}, "
            f"NHEFT_used_vCPU_mean={row['NHEFT_used_vcpu_mean']:.2f}, "
            f"win_rate_N_over_D={row['win_rate_N_over_D'] * 100:.2f}%, "
            f"gain_mean={row['gain_N_over_D_mean']:.4f}%"
        )
    lines.append("")
    lines.append("Constraint notes:")
    lines.append("- e41-e48 all require CCR_data < IDR_image")
    lines.append("- e41-e48 all require relative CCR/IDR gap >= 20%")
    return "\n".join(lines) + "\n"


def main():
    os.makedirs(OUT_BASE_DIR, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_dir = os.path.join(OUT_BASE_DIR, timestamp)
    os.makedirs(out_dir, exist_ok=True)

    df = load_latest_summaries()
    ordered_cols = [
        "exp_dir",
        "scenario",
        "bucket_label",
        "constraint",
        "total_runs",
        "algo_valid_runs",
        "qualified_runs",
        "qualified_rate",
        "HEFT_mean",
        "DHEFT_mean",
        "NHEFT_mean",
        "DHEFT_used_vcpu_mean",
        "NHEFT_used_vcpu_mean",
        "gain_N_over_D_mean",
        "gain_N_over_D_median",
        "win_rate_N_over_D",
        "ttest_p",
        "wilcoxon_p",
        "latest_run_rel",
        "summary_csv_rel",
    ]
    df = df[ordered_cols]

    summary_csv_path = os.path.join(out_dir, "e4x_latest_summary.csv")
    df.to_csv(summary_csv_path, index=False)

    summary_txt_path = os.path.join(out_dir, "summary.txt")
    with open(summary_txt_path, "w") as f:
        f.write(build_summary_text(df))

    chart_path = os.path.join(out_dir, "makespan_mean_comparison.png")
    draw_grouped_bar_chart(df, chart_path)

    vcpu_chart_path = os.path.join(out_dir, "vcpu_usage_comparison.png")
    draw_vcpu_usage_chart(df, vcpu_chart_path)

    print(f"Output directory: {out_dir}")
    print(f"Summary CSV: {summary_csv_path}")
    print(f"Summary TXT: {summary_txt_path}")
    print(f"Chart PNG: {chart_path}")
    print(f"vCPU Chart PNG: {vcpu_chart_path}")


if __name__ == "__main__":
    main()
