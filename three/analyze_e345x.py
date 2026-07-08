#!/usr/bin/env python3
"""
Combine the latest aggregated summaries of e3x, e4x, and e5x into
one output folder and draw combined makespan / vCPU figures.

Input folders:
  experiments/e31_e38/<timestamp>/e3x_latest_summary.csv
  experiments/e41_e48/<timestamp>/e4x_latest_summary.csv
  experiments/e51_e58/<timestamp>/e5x_latest_summary.csv

Output folder:
  experiments/e3x_e4x_e5x/<timestamp>/

Usage:
  python3 experiments/analyze_e345x.py
  python3 experiments/analyze_e345x.py 4
"""

import argparse
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


OUT_BASE_DIR = os.path.join(THIS_DIR, "e3x_e4x_e5x")

FAMILIES = [
    {
        "family_key": "e3x",
        "family_title": "CCR_data ~= IDR_image",
        "family_short": "CCR ~= IDR",
        "base_dir": os.path.join(THIS_DIR, "e31_e38"),
        "summary_csv": "e3x_latest_summary.csv",
        "footnote": "e31-e33: absolute tolerance <= 0.02 | e34-e38: relative tolerance <= 10%",
    },
    {
        "family_key": "e4x",
        "family_title": "CCR_data < IDR_image",
        "family_short": "CCR < IDR",
        "base_dir": os.path.join(THIS_DIR, "e41_e48"),
        "summary_csv": "e4x_latest_summary.csv",
        "footnote": "all bins: relative CCR/IDR gap >= 20%",
    },
    {
        "family_key": "e5x",
        "family_title": "CCR_data > IDR_image",
        "family_short": "CCR > IDR",
        "base_dir": os.path.join(THIS_DIR, "e51_e58"),
        "summary_csv": "e5x_latest_summary.csv",
        "footnote": "all bins: relative CCR/IDR gap >= 20%",
    },
]

ALGO_COLORS = {
    "HEFT": "#4E79A7",
    "DHEFT": "#FF6B6B",
    "NHEFT": "#06A77D",
}

# 是否在柱状图中显示 HEFT 柱子。
# 论文图里如果只想突出 DHEFT vs NHEFT，通常保持 False。
SHOW_HEFT_BAR = False
# 是否显示“图级别”的额外标题和底部说明文字。
# 论文出图通常保持 False，把说明放到 caption 和正文里。
SHOW_EXTRA_FIGURE_TITLES = False
# 是否在 makespan 图上叠加 win rate 折线。
# 为了避免论文图过于拥挤，默认关闭。
SHOW_WIN_RATE_LINE = False
# 是否在 makespan 图上叠加 gain rate 折线。
# 为了避免论文图过于拥挤，默认关闭。
SHOW_GAIN_RATE_LINE = False
# 下面这组比例用于控制左侧柱状图纵轴的上限。
# 计算方式：纵轴上限 = 当前图中最大柱形高度 * 比例
# 比例越大，柱子上方留白越多；比例越小，柱子会显得更高、更紧凑。
FAMILY_MAKESPAN_YMAX_RATIO = 1.45
FAMILY_VCPU_YMAX_RATIO = 1.20
CASE_BALANCED_MAKESPAN_YMAX_RATIO = 1.1
CASE_BALANCED_VCPU_YMAX_RATIO = 1.1
GAIN_ZERO_LIFT_RATIO = 0.35
WIN_RATE_AXIS_MAX = 105.0

AXIS_LABEL_FONTSIZE = 30
TITLE_FONTSIZE = 28
SUBTITLE_FONTSIZE = 18
XTICK_FONTSIZE = 30
YTICK_FONTSIZE = 30
BAR_LABEL_FONTSIZE = 20
LINE_ANNOTATION_FONTSIZE = 11
FOOTNOTE_FONTSIZE = 13
LEGEND_FONTSIZE = 14
TABLE_TITLE_FONTSIZE = 18
TABLE_BODY_FONTSIZE = 12

BAR_LABEL_BASE_Y_OFFSET = 4
BAR_LABEL_X_OFFSET_POINTS = 10
BAR_LABEL_CLOSE_HEIGHT_THRESHOLD_RATIO = 0.035
BAR_LABEL_CLOSE_EXTRA_Y_OFFSET = 11

BUCKET_ORDER = [
    "(0.10, 0.18]",
    "(0.18, 0.32]",
    "(0.32, 0.56]",
    "(0.56, 1.00]",
    "(1.00, 1.78]",
    "(1.78, 3.16]",
    "(3.16, 5.62]",
    "(5.62, 10.00]",
]
BUCKET_ORDER_MAP = {label: idx for idx, label in enumerate(BUCKET_ORDER)}


def parse_args():
    parser = argparse.ArgumentParser(
        description="Aggregate e3x/e4x/e5x summaries and draw combined figures."
    )
    parser.add_argument(
        "case_balanced_bucket_count",
        nargs="?",
        type=int,
        default=4,
        choices=[4, 8],
        help="Number of buckets shown per case-balanced figure: 8 keeps the original single figure, 4 splits it into two figures.",
    )
    return parser.parse_args()


def rel_to_experiments(path):
    try:
        return os.path.relpath(str(path), THIS_DIR)
    except Exception:
        return str(path)


def find_latest_aggregate_dir(base_dir, expected_csv):
    candidates = []
    if not os.path.isdir(base_dir):
        return None

    for name in os.listdir(base_dir):
        path = os.path.join(base_dir, name)
        if os.path.isdir(path) and os.path.exists(os.path.join(path, expected_csv)):
            candidates.append(path)

    if not candidates:
        return None

    candidates.sort(key=lambda p: os.path.getmtime(p), reverse=True)
    return candidates[0]


def finite_max(values, default=1.0):
    arr = np.asarray(values, dtype=float)
    arr = arr[np.isfinite(arr)]
    if arr.size == 0:
        return default
    return float(np.max(arr))


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


def load_family_summary(spec):
    latest_dir = find_latest_aggregate_dir(spec["base_dir"], spec["summary_csv"])
    if latest_dir is None:
        raise RuntimeError(f"No aggregate folder with {spec['summary_csv']} found under {spec['base_dir']}")

    summary_path = os.path.join(latest_dir, spec["summary_csv"])
    df = pd.read_csv(summary_path)
    df["family_key"] = spec["family_key"]
    df["family_title"] = spec["family_title"]
    df["family_short"] = spec["family_short"]
    df["family_footnote"] = spec["footnote"]
    df["aggregate_dir_rel"] = rel_to_experiments(latest_dir)
    df["aggregate_summary_rel"] = rel_to_experiments(summary_path)
    return df


def load_all_summaries():
    frames = [load_family_summary(spec) for spec in FAMILIES]
    df = pd.concat(frames, ignore_index=True)
    df["bucket_sort_key"] = df["bucket_label"].map(BUCKET_ORDER_MAP)
    return df


def draw_family_makespan_panel(ax, panel_df, family_key, family_title):
    panel_df = panel_df.copy()
    x = np.arange(len(panel_df))
    width = 0.23 if SHOW_HEFT_BAR else 0.30

    heft_vals = panel_df["HEFT_mean"].to_numpy(dtype=float)
    dheft_vals = panel_df["DHEFT_mean"].to_numpy(dtype=float)
    nheft_vals = panel_df["NHEFT_mean"].to_numpy(dtype=float)
    win_rate_vals = panel_df["win_rate_N_over_D"].to_numpy(dtype=float) * 100.0
    gain_vals = panel_df["gain_N_over_D_mean"].to_numpy(dtype=float)

    bar_heft = None
    if SHOW_HEFT_BAR:
        bar_heft = ax.bar(
            x - width,
            heft_vals,
            width,
            label="HEFT",
            color=ALGO_COLORS["HEFT"],
            edgecolor="black",
            linewidth=0.8,
        )
        bar_dheft = ax.bar(
            x,
            dheft_vals,
            width,
            label="DHEFT",
            color=ALGO_COLORS["DHEFT"],
            edgecolor="black",
            linewidth=0.8,
        )
        bar_nheft = ax.bar(
            x + width,
            nheft_vals,
            width,
            label="NHEFT",
            color=ALGO_COLORS["NHEFT"],
            edgecolor="black",
            linewidth=0.8,
        )
    else:
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

    ymax_candidates = [finite_max(dheft_vals), finite_max(nheft_vals)]
    if SHOW_HEFT_BAR:
        ymax_candidates.append(finite_max(heft_vals))
    ymax = max(ymax_candidates)
    ax.set_ylim(0, ymax * FAMILY_MAKESPAN_YMAX_RATIO if ymax > 0 else 1.0)
    ax.set_title(family_title, fontsize=SUBTITLE_FONTSIZE, fontweight="bold", pad=10)
    ax.set_xticks(x)
    ax.set_xticklabels(panel_df["bucket_label"].tolist(), rotation=0, fontsize=XTICK_FONTSIZE)
    ax.tick_params(axis="y", labelsize=YTICK_FONTSIZE)
    ax.grid(axis="y", linestyle="--", alpha=0.35)
    ax.set_axisbelow(True)

    label_containers = [bar_dheft, bar_nheft]
    label_values = [dheft_vals, nheft_vals]
    if SHOW_HEFT_BAR and bar_heft is not None:
        label_containers.insert(0, bar_heft)
        label_values.insert(0, heft_vals)
    annotate_grouped_bar_values(ax, label_containers, label_values, ymax)

    ax2 = None
    ax3 = None
    win_line = None
    gain_line = None

    if SHOW_WIN_RATE_LINE:
        ax2 = ax.twinx()
        win_line, = ax2.plot(
            x,
            win_rate_vals,
            color="#F39C12",
            marker="o",
            markersize=5,
            linewidth=2.0,
            label="NHEFT Win Rate",
        )
        ax2.set_ylim(0, WIN_RATE_AXIS_MAX)
        ax2.tick_params(axis="y", colors="#F39C12", labelsize=YTICK_FONTSIZE)
        for xi, yi in zip(x, win_rate_vals):
            ax2.annotate(
                f"{yi:.1f}%",
                (xi, yi),
                textcoords="offset points",
                xytext=(0, -14),
                ha="center",
                color="#F39C12",
                fontsize=LINE_ANNOTATION_FONTSIZE,
            )

    if SHOW_GAIN_RATE_LINE:
        ax3 = ax.twinx()
        if SHOW_WIN_RATE_LINE:
            ax3.spines["right"].set_position(("outward", 52))
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
            markersize=5,
            linewidth=2.0,
            label="NHEFT Gain over DHEFT",
        )
        ax3.tick_params(axis="y", colors="#8E44AD", labelsize=YTICK_FONTSIZE)
        for xi, yi in zip(x, gain_vals):
            ax3.annotate(
                f"{yi:.1f}%",
                (xi, yi),
                textcoords="offset points",
                xytext=(0, 8),
                ha="center",
                color="#8E44AD",
                fontsize=LINE_ANNOTATION_FONTSIZE,
            )

    return bar_heft, bar_dheft, bar_nheft, win_line, gain_line, ax2, ax3


def draw_combined_makespan_chart(df, out_path):
    fig, axes = plt.subplots(1, 3, figsize=(32, 10), sharey=False)
    if SHOW_EXTRA_FIGURE_TITLES:
        fig.suptitle(
            "E3x / E4x / E5x Combined Makespan Comparison",
            fontsize=TITLE_FONTSIZE,
            fontweight="bold",
            y=0.98,
        )

    legend_handles = None
    legend_labels = None

    for idx, spec in enumerate(FAMILIES):
        panel_df = df[df["family_key"] == spec["family_key"]].copy()
        panel_df = panel_df.sort_values("bucket_sort_key").reset_index(drop=True)
        bar_heft, bar_dheft, bar_nheft, win_line, gain_line, ax2, ax3 = draw_family_makespan_panel(
            axes[idx], panel_df, spec["family_key"], spec["family_title"]
        )
        axes[idx].set_xlabel("NCCR Bucket", fontsize=AXIS_LABEL_FONTSIZE)
        if idx == 0:
            axes[idx].set_ylabel("Mean Makespan", fontsize=AXIS_LABEL_FONTSIZE)
            if SHOW_WIN_RATE_LINE and ax2 is not None:
                ax2.set_ylabel("Win Rate (%)", color="#F39C12", fontsize=AXIS_LABEL_FONTSIZE)
            if SHOW_GAIN_RATE_LINE and ax3 is not None:
                ax3.set_ylabel("Gain (%)", color="#8E44AD", fontsize=AXIS_LABEL_FONTSIZE)

        if legend_handles is None:
            legend_handles = []
            legend_labels = []
            if SHOW_HEFT_BAR and bar_heft is not None:
                legend_handles.append(bar_heft)
                legend_labels.append("HEFT")
            legend_handles.extend([bar_dheft, bar_nheft])
            legend_labels.extend(["DHEFT", "NHEFT"])
            if SHOW_WIN_RATE_LINE and win_line is not None:
                legend_handles.append(win_line)
                legend_labels.append("NHEFT Win Rate")
            if SHOW_GAIN_RATE_LINE and gain_line is not None:
                legend_handles.append(gain_line)
                legend_labels.append("NHEFT Gain over DHEFT")

    fig.legend(
        legend_handles,
        legend_labels,
        loc="upper center",
        bbox_to_anchor=(0.5, 0.935),
        ncol=len(legend_labels),
        frameon=True,
        fontsize=LEGEND_FONTSIZE,
    )

    if SHOW_EXTRA_FIGURE_TITLES:
        fig.text(
            0.5,
            0.03,
            "Left-to-right panels: CCR_data ~= IDR_image | CCR_data < IDR_image | CCR_data > IDR_image",
            ha="center",
            fontsize=FOOTNOTE_FONTSIZE,
        )
        layout_rect = [0.02, 0.07, 0.98, 0.90]
    else:
        layout_rect = [0.02, 0.04, 0.98, 0.94]

    plt.tight_layout(rect=layout_rect)
    plt.savefig(out_path, dpi=300, bbox_inches="tight")
    plt.close(fig)


def draw_family_vcpu_panel(ax, panel_df, family_key, family_title):
    panel_df = panel_df.copy()
    x = np.arange(len(panel_df))
    width = 0.34

    dheft_vals = panel_df["DHEFT_used_vcpu_mean"].to_numpy(dtype=float)
    nheft_vals = panel_df["NHEFT_used_vcpu_mean"].to_numpy(dtype=float)

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

    ymax = max(finite_max(dheft_vals), finite_max(nheft_vals))
    ax.set_ylim(0, ymax * FAMILY_VCPU_YMAX_RATIO if ymax > 0 else 1.0)
    ax.set_title(family_title, fontsize=SUBTITLE_FONTSIZE, fontweight="bold", pad=10)
    ax.set_xticks(x)
    ax.set_xticklabels(panel_df["bucket_label"].tolist(), rotation=0, fontsize=XTICK_FONTSIZE)
    ax.tick_params(axis="y", labelsize=YTICK_FONTSIZE)
    ax.grid(axis="y", linestyle="--", alpha=0.35)
    ax.set_axisbelow(True)

    annotate_grouped_bar_values(ax, [bar_dheft, bar_nheft], [dheft_vals, nheft_vals], ymax)
    return bar_dheft, bar_nheft


def draw_combined_vcpu_chart(df, out_path):
    fig, axes = plt.subplots(1, 3, figsize=(30, 8), sharey=False)
    if SHOW_EXTRA_FIGURE_TITLES:
        fig.suptitle(
            "E3x / E4x / E5x Combined vCPU Usage Comparison",
            fontsize=TITLE_FONTSIZE,
            fontweight="bold",
            y=0.98,
        )

    legend_handles = None
    legend_labels = None

    for idx, spec in enumerate(FAMILIES):
        panel_df = df[df["family_key"] == spec["family_key"]].copy()
        panel_df = panel_df.sort_values("bucket_sort_key").reset_index(drop=True)
        bar_dheft, bar_nheft = draw_family_vcpu_panel(axes[idx], panel_df, spec["family_key"], spec["family_title"])
        axes[idx].set_xlabel("NCCR Bucket", fontsize=AXIS_LABEL_FONTSIZE)
        if idx == 0:
            axes[idx].set_ylabel("Mean Used vCPUs", fontsize=AXIS_LABEL_FONTSIZE)
            legend_handles = [bar_dheft, bar_nheft]
            legend_labels = ["DHEFT", "NHEFT"]

    fig.legend(
        legend_handles,
        legend_labels,
        loc="upper center",
        bbox_to_anchor=(0.5, 0.94),
        ncol=2,
        frameon=True,
        fontsize=LEGEND_FONTSIZE,
    )
    if SHOW_EXTRA_FIGURE_TITLES:
        fig.text(
            0.5,
            0.03,
            "Values are mean used vCPU counts over qualified runs in each NCCR bucket",
            ha="center",
            fontsize=FOOTNOTE_FONTSIZE,
        )
        layout_rect = [0.02, 0.07, 0.98, 0.90]
    else:
        layout_rect = [0.02, 0.04, 0.98, 0.94]

    plt.tight_layout(rect=layout_rect)
    plt.savefig(out_path, dpi=300, bbox_inches="tight")
    plt.close(fig)


def build_case_balanced_mean_df(df):
    rows = []
    for bucket_label in BUCKET_ORDER:
        bucket_df = df[df["bucket_label"] == bucket_label].copy()
        bucket_df = bucket_df.sort_values("family_key")
        if bucket_df.empty:
            continue

        rows.append(
            {
                "bucket_label": bucket_label,
                "bucket_sort_key": BUCKET_ORDER_MAP[bucket_label],
                "family_count": int(len(bucket_df)),
                "HEFT_mean": float(bucket_df["HEFT_mean"].mean()),
                "DHEFT_mean": float(bucket_df["DHEFT_mean"].mean()),
                "NHEFT_mean": float(bucket_df["NHEFT_mean"].mean()),
                "DHEFT_used_vcpu_mean": float(bucket_df["DHEFT_used_vcpu_mean"].mean()),
                "NHEFT_used_vcpu_mean": float(bucket_df["NHEFT_used_vcpu_mean"].mean()),
                "gain_N_over_D_mean": float(bucket_df["gain_N_over_D_mean"].mean()),
                "gain_N_over_D_median": float(bucket_df["gain_N_over_D_median"].mean()),
                "win_rate_N_over_D": float(bucket_df["win_rate_N_over_D"].mean()),
                "qualified_runs_mean": float(bucket_df["qualified_runs"].mean()),
                "qualified_runs_sum": int(bucket_df["qualified_runs"].sum()),
            }
        )

    mean_df = pd.DataFrame(rows)
    return mean_df.sort_values("bucket_sort_key").reset_index(drop=True)


def build_case_balanced_output_specs(df, bucket_count):
    ordered_df = df.sort_values("bucket_sort_key").reset_index(drop=True)
    if bucket_count == 8:
        return [
            {
                "suffix": "",
                "title_suffix": "",
                "df": ordered_df,
            }
        ]

    specs = []
    chunk_size = 4
    for idx, start in enumerate(range(0, len(ordered_df), chunk_size), start=1):
        chunk_df = ordered_df.iloc[start : start + chunk_size].reset_index(drop=True)
        if chunk_df.empty:
            continue
        specs.append(
            {
                "suffix": f"-{idx}",
                "title_suffix": f" (Part {idx})",
                "df": chunk_df,
            }
        )
    return specs


def append_suffix_before_ext(path, suffix):
    if not suffix:
        return path
    root, ext = os.path.splitext(path)
    return f"{root}{suffix}{ext}"


def draw_case_balanced_mean_makespan_chart(df, out_path, title_suffix=""):
    fig, ax = plt.subplots(figsize=(20, 10))

    x = np.arange(len(df))
    width = 0.23 if SHOW_HEFT_BAR else 0.30

    heft_vals = df["HEFT_mean"].to_numpy(dtype=float)
    dheft_vals = df["DHEFT_mean"].to_numpy(dtype=float)
    nheft_vals = df["NHEFT_mean"].to_numpy(dtype=float)
    win_rate_vals = df["win_rate_N_over_D"].to_numpy(dtype=float) * 100.0
    gain_vals = df["gain_N_over_D_mean"].to_numpy(dtype=float)

    bar_heft = None
    if SHOW_HEFT_BAR:
        bar_heft = ax.bar(
            x - width,
            heft_vals,
            width,
            label="HEFT",
            color=ALGO_COLORS["HEFT"],
            edgecolor="black",
            linewidth=0.8,
        )
        bar_dheft = ax.bar(
            x,
            dheft_vals,
            width,
            label="DHEFT",
            color=ALGO_COLORS["DHEFT"],
            edgecolor="black",
            linewidth=0.8,
        )
        bar_nheft = ax.bar(
            x + width,
            nheft_vals,
            width,
            label="NHEFT",
            color=ALGO_COLORS["NHEFT"],
            edgecolor="black",
            linewidth=0.8,
        )
    else:
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

    ymax_candidates = [finite_max(dheft_vals), finite_max(nheft_vals)]
    if SHOW_HEFT_BAR:
        ymax_candidates.append(finite_max(heft_vals))
    ymax = max(ymax_candidates)
    ax.set_ylim(0, ymax * CASE_BALANCED_MAKESPAN_YMAX_RATIO if ymax > 0 else 1.0)
    ax.set_ylabel("Mean Makespan", fontsize=AXIS_LABEL_FONTSIZE)
    ax.set_xlabel("NCCR Bucket", fontsize=AXIS_LABEL_FONTSIZE)
    if SHOW_EXTRA_FIGURE_TITLES:
        ax.set_title(
            f"Case-Balanced Mean Makespan Comparison across CCR/IDR Cases{title_suffix}",
            fontsize=TITLE_FONTSIZE,
            fontweight="bold",
            pad=16,
        )
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

    ax2 = None
    ax3 = None
    win_line = None
    gain_line = None

    if SHOW_WIN_RATE_LINE:
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
            ax2.annotate(
                f"{yi:.1f}%",
                (xi, yi),
                textcoords="offset points",
                xytext=(0, -18),
                ha="center",
                color="#F39C12",
                fontsize=LINE_ANNOTATION_FONTSIZE,
            )

    if SHOW_GAIN_RATE_LINE:
        ax3 = ax.twinx()
        if SHOW_WIN_RATE_LINE:
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
            ax3.annotate(
                f"{yi:.1f}%",
                (xi, yi),
                textcoords="offset points",
                xytext=(0, 10),
                ha="center",
                color="#8E44AD",
                fontsize=LINE_ANNOTATION_FONTSIZE,
            )

    legend_handles = []
    legend_labels = []
    if SHOW_HEFT_BAR and bar_heft is not None:
        legend_handles.append(bar_heft)
        legend_labels.append("HEFT")
    legend_handles.extend([bar_dheft, bar_nheft])
    legend_labels.extend(["DHEFT", "NHEFT"])
    if SHOW_WIN_RATE_LINE and win_line is not None:
        legend_handles.append(win_line)
        legend_labels.append("NHEFT Win Rate")
    if SHOW_GAIN_RATE_LINE and gain_line is not None:
        legend_handles.append(gain_line)
        legend_labels.append("NHEFT Gain over DHEFT")
    legend = ax.legend(
        legend_handles,
        legend_labels,
        loc="upper left",
        ncol=3,
        frameon=True,
        fontsize=LEGEND_FONTSIZE,
    )
    legend.get_frame().set_alpha(0.95)

    if SHOW_EXTRA_FIGURE_TITLES:
        fig.text(
            0.5,
            0.02,
            "Case-balanced mean across CCR_data ~= IDR_image, CCR_data < IDR_image, and CCR_data > IDR_image",
            ha="center",
            fontsize=FOOTNOTE_FONTSIZE,
        )
        layout_rect = [0.02, 0.06, 0.93, 0.95]
    else:
        layout_rect = [0.02, 0.04, 0.93, 0.98]

    plt.tight_layout(rect=layout_rect)
    plt.savefig(out_path, dpi=300, bbox_inches="tight")
    plt.close(fig)


def draw_case_balanced_mean_vcpu_chart(df, out_path, title_suffix=""):
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

    ymax = max(finite_max(dheft_vals), finite_max(nheft_vals))
    ax.set_ylim(0, ymax * CASE_BALANCED_VCPU_YMAX_RATIO if ymax > 0 else 1.0)
    ax.set_ylabel("Mean Used vCPUs", fontsize=AXIS_LABEL_FONTSIZE)
    ax.set_xlabel("NCCR Bucket", fontsize=AXIS_LABEL_FONTSIZE)
    if SHOW_EXTRA_FIGURE_TITLES:
        ax.set_title(
            f"Case-Balanced Mean vCPU Usage across CCR/IDR Cases{title_suffix}",
            fontsize=TITLE_FONTSIZE,
            fontweight="bold",
            pad=16,
        )
    ax.set_xticks(x)
    ax.set_xticklabels(df["bucket_label"].tolist(), rotation=0, fontsize=XTICK_FONTSIZE)
    ax.tick_params(axis="y", labelsize=YTICK_FONTSIZE)
    ax.grid(axis="y", linestyle="--", alpha=0.35)
    ax.set_axisbelow(True)

    annotate_grouped_bar_values(ax, [bar_dheft, bar_nheft], [dheft_vals, nheft_vals], ymax)

    legend = ax.legend(loc="upper left", ncol=2, frameon=True, fontsize=LEGEND_FONTSIZE)
    legend.get_frame().set_alpha(0.95)

    if SHOW_EXTRA_FIGURE_TITLES:
        fig.text(
            0.5,
            0.02,
            "Case-balanced mean across CCR_data ~= IDR_image, CCR_data < IDR_image, and CCR_data > IDR_image",
            ha="center",
            fontsize=FOOTNOTE_FONTSIZE,
        )
        layout_rect = [0.02, 0.06, 0.98, 0.95]
    else:
        layout_rect = [0.02, 0.04, 0.98, 0.98]

    plt.tight_layout(rect=layout_rect)
    plt.savefig(out_path, dpi=300, bbox_inches="tight")
    plt.close(fig)


def build_summary_text(df):
    lines = []
    lines.append("E3x / E4x / E5x Combined Summary")
    lines.append("")
    lines.append("This aggregation reads the latest existing aggregate CSV under each family folder.")
    lines.append("")
    lines.append("Source aggregate folders:")
    for spec in FAMILIES:
        panel_df = df[df["family_key"] == spec["family_key"]]
        if panel_df.empty:
            continue
        row0 = panel_df.iloc[0]
        lines.append(f"- {spec['family_key']}: {row0['aggregate_dir_rel']} ({row0['aggregate_summary_rel']})")
    lines.append("")
    lines.append("Bucket overview:")
    for spec in FAMILIES:
        lines.append(f"- {spec['family_title']}")
        panel_df = df[df["family_key"] == spec["family_key"]].copy()
        panel_df = panel_df.sort_values("bucket_sort_key")
        for _, row in panel_df.iterrows():
            lines.append(
                "  "
                + f"{row['bucket_label']}: "
                + f"qualified={int(row['qualified_runs'])}/{int(row['algo_valid_runs'])} "
                + f"({float(row['qualified_rate']) * 100:.2f}%), "
                + f"HEFT_mean={float(row['HEFT_mean']):.4f}, "
                + f"DHEFT_mean={float(row['DHEFT_mean']):.4f}, "
                + f"NHEFT_mean={float(row['NHEFT_mean']):.4f}, "
                + f"DHEFT_used_vCPU_mean={float(row['DHEFT_used_vcpu_mean']):.2f}, "
                + f"NHEFT_used_vCPU_mean={float(row['NHEFT_used_vcpu_mean']):.2f}, "
                + f"win_rate_N_over_D={float(row['win_rate_N_over_D']) * 100:.2f}%, "
                + f"gain_mean={float(row['gain_N_over_D_mean']):.4f}%"
            )
        lines.append(f"  note: {spec['footnote']}")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def build_metric_table_df(df, metric_kind):
    rows = []
    for bucket_label in BUCKET_ORDER:
        row = {"NCCR Bucket": bucket_label}
        for spec in FAMILIES:
            match = df[
                (df["family_key"] == spec["family_key"])
                & (df["bucket_label"] == bucket_label)
            ]
            if match.empty:
                cell = "N/A"
            else:
                rec = match.iloc[0]
                if metric_kind == "makespan":
                    cell = f"{float(rec['DHEFT_mean']):.2f} / {float(rec['NHEFT_mean']):.2f}"
                elif metric_kind == "gain":
                    cell = f"{float(rec['gain_N_over_D_mean']):.2f}%"
                elif metric_kind == "win":
                    cell = f"{float(rec['win_rate_N_over_D']) * 100:.1f}%"
                elif metric_kind == "usage":
                    cell = f"{float(rec['DHEFT_used_vcpu_mean']):.1f} / {float(rec['NHEFT_used_vcpu_mean']):.1f}"
                else:
                    raise ValueError(f"Unknown metric_kind: {metric_kind}")
            row[spec["family_short"]] = cell
        rows.append(row)
    return pd.DataFrame(rows)


def draw_table_image(display_df, title, out_path, note=None):
    fig_height = max(4.2, 0.62 * (len(display_df) + 2.5))
    fig, ax = plt.subplots(figsize=(13.5, fig_height))
    ax.axis("off")
    if SHOW_EXTRA_FIGURE_TITLES:
        ax.set_title(title, fontsize=TABLE_TITLE_FONTSIZE, fontweight="bold", pad=14)

    table = ax.table(
        cellText=display_df.values,
        colLabels=display_df.columns,
        cellLoc="center",
        loc="center",
    )
    table.auto_set_font_size(False)
    table.set_fontsize(TABLE_BODY_FONTSIZE)
    table.scale(1.08, 1.55)
    try:
        table.auto_set_column_width(col=list(range(len(display_df.columns))))
    except Exception:
        pass

    for (row, col), cell in table.get_celld().items():
        cell.set_edgecolor("#000000")
        cell.set_linewidth(0.6)
        cell.set_facecolor("#FFFFFF")
        if row == 0:
            cell.set_text_props(weight="bold")
        else:
            if col == 0:
                cell.set_text_props(weight="bold")

    if SHOW_EXTRA_FIGURE_TITLES and note:
        fig.text(0.5, 0.03, note, ha="center", fontsize=FOOTNOTE_FONTSIZE)
        layout_rect = [0.02, 0.07, 0.98, 0.93]
    else:
        layout_rect = None
    if layout_rect is None:
        plt.tight_layout()
    else:
        plt.tight_layout(rect=layout_rect)
    plt.savefig(out_path, dpi=300, bbox_inches="tight")
    plt.close(fig)


def draw_metric_tables(df, out_dir):
    makespan_df = build_metric_table_df(df, "makespan")
    gain_df = build_metric_table_df(df, "gain")
    win_df = build_metric_table_df(df, "win")
    usage_df = build_metric_table_df(df, "usage")

    draw_table_image(
        makespan_df,
        "E3x / E4x / E5x Makespan Table",
        os.path.join(out_dir, "makespan_table.png"),
        note="Cell format: DHEFT mean / NHEFT mean",
    )
    draw_table_image(
        gain_df,
        "E3x / E4x / E5x Gain Rate Table",
        os.path.join(out_dir, "gain_rate_table.png"),
        note="Cell format: mean NHEFT gain over DHEFT",
    )
    draw_table_image(
        win_df,
        "E3x / E4x / E5x Win Rate Table",
        os.path.join(out_dir, "win_rate_table.png"),
        note="Cell format: NHEFT win rate over DHEFT",
    )
    draw_table_image(
        usage_df,
        "E3x / E4x / E5x vCPU Usage Table",
        os.path.join(out_dir, "vcpu_usage_table.png"),
        note="Cell format: DHEFT mean used vCPUs / NHEFT mean used vCPUs",
    )


def main():
    args = parse_args()

    os.makedirs(OUT_BASE_DIR, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_dir = os.path.join(OUT_BASE_DIR, timestamp)
    os.makedirs(out_dir, exist_ok=True)

    df = load_all_summaries().copy()
    case_balanced_mean_df = build_case_balanced_mean_df(df)

    ordered_cols = [
        "family_key",
        "family_title",
        "family_short",
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
        "aggregate_dir_rel",
        "aggregate_summary_rel",
        "latest_run_rel",
        "summary_csv_rel",
        "bucket_sort_key",
    ]
    df = df[ordered_cols]
    df = df.sort_values(["family_key", "bucket_sort_key"]).reset_index(drop=True)

    out_csv = os.path.join(out_dir, "e345x_latest_summary.csv")
    df.to_csv(out_csv, index=False)

    summary_txt = os.path.join(out_dir, "summary.txt")
    with open(summary_txt, "w") as f:
        f.write(build_summary_text(df))

    makespan_png = os.path.join(out_dir, "makespan_mean_comparison.png")
    draw_combined_makespan_chart(df, makespan_png)

    vcpu_png = os.path.join(out_dir, "vcpu_usage_comparison.png")
    draw_combined_vcpu_chart(df, vcpu_png)

    case_balanced_mean_csv = os.path.join(out_dir, "e345x_case_balanced_mean_summary.csv")
    case_balanced_mean_df.to_csv(case_balanced_mean_csv, index=False)

    case_balanced_makespan_png = os.path.join(out_dir, "makespan_mean_comparison_ccr_idr_mean.png")
    case_balanced_vcpu_png = os.path.join(out_dir, "vcpu_usage_comparison_ccr_idr_mean.png")
    case_balanced_specs = build_case_balanced_output_specs(
        case_balanced_mean_df, args.case_balanced_bucket_count
    )

    case_balanced_makespan_outputs = []
    case_balanced_vcpu_outputs = []
    for spec in case_balanced_specs:
        makespan_out = append_suffix_before_ext(case_balanced_makespan_png, spec["suffix"])
        vcpu_out = append_suffix_before_ext(case_balanced_vcpu_png, spec["suffix"])
        draw_case_balanced_mean_makespan_chart(
            spec["df"], makespan_out, title_suffix=spec["title_suffix"]
        )
        draw_case_balanced_mean_vcpu_chart(
            spec["df"], vcpu_out, title_suffix=spec["title_suffix"]
        )
        case_balanced_makespan_outputs.append(makespan_out)
        case_balanced_vcpu_outputs.append(vcpu_out)

    draw_metric_tables(df, out_dir)

    print(f"[OK] Output directory: {out_dir}")
    print(f"[OK] Summary CSV: {out_csv}")
    print(f"[OK] Makespan figure: {makespan_png}")
    print(f"[OK] vCPU figure: {vcpu_png}")
    print(f"[OK] Case-balanced mean CSV: {case_balanced_mean_csv}")
    for path in case_balanced_makespan_outputs:
        print(f"[OK] Case-balanced mean makespan figure: {path}")
    for path in case_balanced_vcpu_outputs:
        print(f"[OK] Case-balanced mean vCPU figure: {path}")


if __name__ == "__main__":
    main()
