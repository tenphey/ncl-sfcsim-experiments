#!/usr/bin/env python3
"""Analyze E0 NHEFT vCPU EFT-tolerance sweep results.

This script reads an existing run_* folder produced by run_experiment.py.
It never launches Java and never modifies the raw CSV.  The main comparison is
paired by seed: each tolerance variant is compared with the same seed under
tolerance=0.0, which is the original NHEFT behavior.

If a run was stopped in the middle of a seed, that incomplete seed is excluded
from all summaries and plots.  A seed must have all observed tolerance values
to be used in the analysis.

Usage from the simulator repository root:

  experiments/.venv/bin/python \
      experiments/four/e0_nheft_vcpu_tolerance/analyze_results.py

  experiments/.venv/bin/python \
      experiments/four/e0_nheft_vcpu_tolerance/analyze_results.py \
      run_20260810_151839_151_1
"""

import argparse
import json
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


RAW_CSV_NAME = "e0_tolerance_results.csv"
BASE_TOLERANCE = 0.0
MAKESPAN_WITHIN_1PCT = 0.01
MAKESPAN_WITHIN_5PCT = 0.05

WASEDA_RED = "#8E1728"
GREY = "#CFCFCF"
DARK = "#172A33"
GREEN = "#0B7F5B"
ORANGE = "#D97904"

PLOT_DPI = 300
FIGSIZE_LINE = (12, 6.2)
FIGSIZE_TRADEOFF = (8.2, 6.4)
FIGSIZE_COMBINED = (13.5, 6.4)


def parse_args():
    parser = argparse.ArgumentParser(
        description="Analyze an existing E0 tolerance-sweep result folder."
    )
    parser.add_argument(
        "result_folder",
        nargs="?",
        help=(
            "run_* folder path or basename. If omitted, the latest run_* folder "
            "with e0_tolerance_results.csv is used."
        ),
    )
    parser.add_argument(
        "--output-dir",
        help="Optional output directory. Default: <result_folder>/analysis_<timestamp>",
    )
    return parser.parse_args()


def relpath(path, base=THIS_DIR):
    try:
        return os.path.relpath(path, base)
    except Exception:
        return path


def find_latest_result_dir():
    candidates = []
    for name in os.listdir(THIS_DIR):
        path = os.path.join(THIS_DIR, name)
        if (
            os.path.isdir(path)
            and name.startswith("run_")
            and os.path.exists(os.path.join(path, RAW_CSV_NAME))
        ):
            candidates.append(path)

    if not candidates:
        return None

    candidates.sort(key=lambda p: os.path.getmtime(p), reverse=True)
    return candidates[0]


def resolve_result_dir(arg):
    if not arg:
        return find_latest_result_dir()

    if os.path.isdir(arg):
        return os.path.abspath(arg)

    candidate = os.path.join(THIS_DIR, arg)
    if os.path.isdir(candidate):
        return os.path.abspath(candidate)

    matches = []
    for name in os.listdir(THIS_DIR):
        path = os.path.join(THIS_DIR, name)
        if os.path.isdir(path) and name.startswith(arg):
            matches.append(path)

    if len(matches) == 1:
        return os.path.abspath(matches[0])
    if len(matches) > 1:
        print(f"Multiple result folders match '{arg}':")
        for match in sorted(matches):
            print(f"  {os.path.basename(match)}")
        raise SystemExit(1)

    return None


def canonical_tolerance(value):
    if pd.isna(value):
        return ""
    value = float(value)
    rounded = round(value, 10)
    if abs(rounded - round(rounded, 1)) <= 1.0e-10:
        return f"{rounded:.1f}"
    return f"{rounded:g}"


def safe_percent(numerator, denominator):
    denominator = np.asarray(denominator, dtype=float)
    numerator = np.asarray(numerator, dtype=float)
    with np.errstate(divide="ignore", invalid="ignore"):
        result = numerator / denominator * 100.0
    result[~np.isfinite(result)] = np.nan
    return result


def load_raw_csv(result_dir):
    csv_path = os.path.join(result_dir, RAW_CSV_NAME)
    if not os.path.exists(csv_path):
        raise FileNotFoundError(f"CSV not found: {csv_path}")

    df = pd.read_csv(csv_path)
    if df.empty:
        raise RuntimeError(f"CSV is empty: {csv_path}")

    numeric_cols = [
        "seed",
        "configured_tolerance",
        "ccr_data",
        "idr_image",
        "nccr_total",
        "heft_makespan",
        "heft_slr",
        "heft_vcpus",
        "heft_hosts",
        "heft_instances",
        "dheft_makespan",
        "dheft_slr",
        "dheft_vcpus",
        "dheft_hosts",
        "dheft_instances",
        "nheft_makespan",
        "nheft_slr",
        "nheft_vcpus",
        "nheft_hosts",
        "nheft_instances",
        "time_sec",
        "return_code",
    ]
    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    df["tolerance_value"] = pd.to_numeric(df["tolerance"], errors="coerce")
    df["tolerance_label"] = df["tolerance_value"].map(canonical_tolerance)
    return df


def filter_ok_rows(df):
    if "status" not in df.columns:
        raise RuntimeError("CSV does not contain a status column")

    ok = df[df["status"] == "ok"].copy()
    if ok.empty:
        status_counts = df["status"].value_counts(dropna=False).to_dict()
        raise RuntimeError(f"No ok rows found. Status counts: {status_counts}")

    required = [
        "seed",
        "tolerance_value",
        "heft_makespan",
        "heft_vcpus",
        "dheft_makespan",
        "dheft_vcpus",
        "nheft_makespan",
        "nheft_vcpus",
    ]
    missing = [col for col in required if col not in ok.columns]
    if missing:
        raise RuntimeError(f"Missing required columns: {missing}")

    ok = ok.dropna(subset=required).copy()
    if ok.empty:
        raise RuntimeError("No ok rows have complete core metrics")
    return ok


def tolerance_grid_from_rows(ok):
    values = sorted(ok["tolerance_value"].dropna().unique())
    labels = [canonical_tolerance(value) for value in values]
    return values, labels


def filter_complete_seeds(ok):
    """Keep only seeds that have every observed tolerance value.

    This is important for interrupted runs.  If the last seed was stopped after
    only part of the tolerance grid, including it would make the averages use
    different DAG/platform inputs for different tolerance values.
    """
    expected_values, expected_labels = tolerance_grid_from_rows(ok)
    expected_label_set = set(expected_labels)

    report_rows = []
    complete_seeds = []
    for seed, group in ok.groupby("seed", sort=True):
        observed_labels = set(group["tolerance_label"].dropna().astype(str))
        missing_labels = sorted(
            expected_label_set - observed_labels,
            key=lambda label: float(label),
        )
        is_complete = len(missing_labels) == 0
        if is_complete:
            complete_seeds.append(seed)
        report_rows.append(
            {
                "seed": int(seed),
                "is_complete": is_complete,
                "completed_tolerance_count": len(observed_labels),
                "expected_tolerance_count": len(expected_labels),
                "completed_tolerances": ",".join(
                    sorted(observed_labels, key=lambda label: float(label))
                ),
                "missing_tolerances": ",".join(missing_labels),
            }
        )

    if not complete_seeds:
        raise RuntimeError(
            "No complete seeds found. At least one seed must have all observed "
            f"tolerances: {', '.join(expected_labels)}"
        )

    complete_ok = ok[ok["seed"].isin(complete_seeds)].copy()
    report = pd.DataFrame(report_rows)
    return complete_ok, report, expected_labels


def build_paired_metrics(ok):
    baseline = ok[np.isclose(ok["tolerance_value"], BASE_TOLERANCE)].copy()
    if baseline.empty:
        raise RuntimeError("No tolerance=0.0 baseline rows were found")

    baseline = baseline.sort_values(["seed", "time_sec"]).drop_duplicates("seed")
    baseline_cols = [
        "seed",
        "heft_makespan",
        "heft_vcpus",
        "dheft_makespan",
        "dheft_vcpus",
        "nheft_makespan",
        "nheft_vcpus",
        "nheft_hosts",
        "nheft_instances",
    ]
    baseline_cols = [col for col in baseline_cols if col in baseline.columns]
    base = baseline[baseline_cols].rename(
        columns={
            "heft_makespan": "base_heft_makespan",
            "heft_vcpus": "base_heft_vcpus",
            "dheft_makespan": "base_dheft_makespan",
            "dheft_vcpus": "base_dheft_vcpus",
            "nheft_makespan": "base_nheft_makespan",
            "nheft_vcpus": "base_nheft_vcpus",
            "nheft_hosts": "base_nheft_hosts",
            "nheft_instances": "base_nheft_instances",
        }
    )

    paired = ok.merge(base, on="seed", how="inner")
    if paired.empty:
        raise RuntimeError("No rows can be paired with tolerance=0.0 baseline")

    paired["makespan_delta_vs_base"] = (
        paired["nheft_makespan"] - paired["base_nheft_makespan"]
    )
    paired["makespan_change_vs_base_pct"] = safe_percent(
        paired["makespan_delta_vs_base"], paired["base_nheft_makespan"]
    )
    paired["vcpu_delta_vs_base"] = paired["nheft_vcpus"] - paired["base_nheft_vcpus"]
    paired["vcpu_reduction_vs_base_pct"] = safe_percent(
        paired["base_nheft_vcpus"] - paired["nheft_vcpus"],
        paired["base_nheft_vcpus"],
    )
    paired["gain_nheft_over_dheft_pct"] = safe_percent(
        paired["dheft_makespan"] - paired["nheft_makespan"],
        paired["dheft_makespan"],
    )
    paired["nheft_win_over_dheft"] = paired["nheft_makespan"] < paired["dheft_makespan"]
    paired["makespan_not_worse_than_base"] = (
        paired["nheft_makespan"] <= paired["base_nheft_makespan"]
    )
    paired["makespan_within_1pct_base"] = (
        paired["nheft_makespan"]
        <= paired["base_nheft_makespan"] * (1.0 + MAKESPAN_WITHIN_1PCT)
    )
    paired["makespan_within_5pct_base"] = (
        paired["nheft_makespan"]
        <= paired["base_nheft_makespan"] * (1.0 + MAKESPAN_WITHIN_5PCT)
    )
    paired["vcpu_not_more_than_base"] = paired["nheft_vcpus"] <= paired["base_nheft_vcpus"]
    paired["vcpu_strictly_reduced"] = paired["nheft_vcpus"] < paired["base_nheft_vcpus"]
    paired["within_1pct_and_vcpu_reduced"] = (
        paired["makespan_within_1pct_base"] & paired["vcpu_strictly_reduced"]
    )
    paired["within_5pct_and_vcpu_reduced"] = (
        paired["makespan_within_5pct_base"] & paired["vcpu_strictly_reduced"]
    )
    return paired


def bool_mean_percent(series):
    return float(series.mean() * 100.0) if len(series) else np.nan


def build_tolerance_summary(paired):
    rows = []
    for tolerance, group in paired.groupby("tolerance_value", sort=True):
        row = {
            "tolerance": canonical_tolerance(tolerance),
            "tolerance_value": tolerance,
            "paired_rows": len(group),
            "paired_seeds": group["seed"].nunique(),
            "nheft_makespan_mean": group["nheft_makespan"].mean(),
            "nheft_makespan_std": group["nheft_makespan"].std(ddof=1),
            "nheft_makespan_median": group["nheft_makespan"].median(),
            "nheft_vcpus_mean": group["nheft_vcpus"].mean(),
            "nheft_vcpus_std": group["nheft_vcpus"].std(ddof=1),
            "nheft_hosts_mean": group["nheft_hosts"].mean()
            if "nheft_hosts" in group.columns
            else np.nan,
            "makespan_change_vs_base_pct_mean": group[
                "makespan_change_vs_base_pct"
            ].mean(),
            "makespan_change_vs_base_pct_median": group[
                "makespan_change_vs_base_pct"
            ].median(),
            "vcpu_delta_vs_base_mean": group["vcpu_delta_vs_base"].mean(),
            "vcpu_reduction_vs_base_pct_mean": group[
                "vcpu_reduction_vs_base_pct"
            ].mean(),
            "gain_nheft_over_dheft_pct_mean": group[
                "gain_nheft_over_dheft_pct"
            ].mean(),
            "win_rate_over_dheft_pct": bool_mean_percent(
                group["nheft_win_over_dheft"]
            ),
            "makespan_not_worse_than_base_rate_pct": bool_mean_percent(
                group["makespan_not_worse_than_base"]
            ),
            "makespan_within_1pct_base_rate_pct": bool_mean_percent(
                group["makespan_within_1pct_base"]
            ),
            "makespan_within_5pct_base_rate_pct": bool_mean_percent(
                group["makespan_within_5pct_base"]
            ),
            "vcpu_not_more_than_base_rate_pct": bool_mean_percent(
                group["vcpu_not_more_than_base"]
            ),
            "vcpu_strictly_reduced_rate_pct": bool_mean_percent(
                group["vcpu_strictly_reduced"]
            ),
            "within_1pct_and_vcpu_reduced_rate_pct": bool_mean_percent(
                group["within_1pct_and_vcpu_reduced"]
            ),
            "within_5pct_and_vcpu_reduced_rate_pct": bool_mean_percent(
                group["within_5pct_and_vcpu_reduced"]
            ),
        }
        rows.append(row)

    summary = pd.DataFrame(rows).sort_values("tolerance_value").reset_index(drop=True)
    return summary


def build_reference_summary(paired):
    baseline = paired[np.isclose(paired["tolerance_value"], BASE_TOLERANCE)].copy()
    rows = []
    for label, prefix in [
        ("HEFT", "heft"),
        ("DHEFT", "dheft"),
        ("Original NHEFT", "nheft"),
    ]:
        rows.append(
            {
                "algorithm": label,
                "rows": len(baseline),
                "seeds": baseline["seed"].nunique(),
                "makespan_mean": baseline[f"{prefix}_makespan"].mean(),
                "makespan_std": baseline[f"{prefix}_makespan"].std(ddof=1),
                "makespan_median": baseline[f"{prefix}_makespan"].median(),
                "vcpus_mean": baseline[f"{prefix}_vcpus"].mean(),
                "vcpus_std": baseline[f"{prefix}_vcpus"].std(ddof=1),
            }
        )
    return pd.DataFrame(rows)


def finite_max(values, default=1.0):
    arr = np.asarray(values, dtype=float)
    arr = arr[np.isfinite(arr)]
    if arr.size == 0:
        return default
    return float(np.max(arr))


def add_grid(ax):
    ax.grid(axis="y", linestyle="--", linewidth=0.7, alpha=0.35)
    ax.set_axisbelow(True)


def save_line_plots(summary, reference, output_dir):
    x = summary["tolerance_value"].to_numpy(dtype=float)
    tol_labels = summary["tolerance"].tolist()

    original_makespan = float(
        reference.loc[reference["algorithm"] == "Original NHEFT", "makespan_mean"].iloc[0]
    )
    dheft_makespan = float(
        reference.loc[reference["algorithm"] == "DHEFT", "makespan_mean"].iloc[0]
    )
    original_vcpus = float(
        reference.loc[reference["algorithm"] == "Original NHEFT", "vcpus_mean"].iloc[0]
    )
    dheft_vcpus = float(reference.loc[reference["algorithm"] == "DHEFT", "vcpus_mean"].iloc[0])

    fig, ax = plt.subplots(figsize=FIGSIZE_LINE)
    ax.plot(
        x,
        summary["nheft_makespan_mean"],
        color=WASEDA_RED,
        marker="o",
        linewidth=2.5,
        label="NHEFT tolerance variant",
    )
    ax.axhline(original_makespan, color=DARK, linestyle="--", linewidth=1.5, label="Original NHEFT")
    ax.axhline(dheft_makespan, color=GREY, linestyle="-.", linewidth=1.8, label="DHEFT")
    ax.set_xlabel("nheft_vcpu_eft_tolerance")
    ax.set_ylabel("Mean makespan")
    ax.set_xticks(x)
    ax.set_xticklabels(tol_labels)
    ax.set_ylim(0, finite_max(summary["nheft_makespan_mean"]) * 1.25)
    add_grid(ax)
    ax.legend()
    ax.set_title("Mean Makespan by NHEFT vCPU EFT Tolerance")
    fig.tight_layout()
    fig.savefig(os.path.join(output_dir, "makespan_by_tolerance.png"), dpi=PLOT_DPI)
    plt.close(fig)

    fig, ax = plt.subplots(figsize=FIGSIZE_LINE)
    ax.plot(
        x,
        summary["nheft_vcpus_mean"],
        color=WASEDA_RED,
        marker="o",
        linewidth=2.5,
        label="NHEFT tolerance variant",
    )
    ax.axhline(original_vcpus, color=DARK, linestyle="--", linewidth=1.5, label="Original NHEFT")
    ax.axhline(dheft_vcpus, color=GREY, linestyle="-.", linewidth=1.8, label="DHEFT")
    ax.set_xlabel("nheft_vcpu_eft_tolerance")
    ax.set_ylabel("Mean used vCPUs")
    ax.set_xticks(x)
    ax.set_xticklabels(tol_labels)
    ax.set_ylim(0, finite_max(summary["nheft_vcpus_mean"]) * 1.25)
    add_grid(ax)
    ax.legend()
    ax.set_title("Mean Used vCPUs by NHEFT vCPU EFT Tolerance")
    fig.tight_layout()
    fig.savefig(os.path.join(output_dir, "vcpu_by_tolerance.png"), dpi=PLOT_DPI)
    plt.close(fig)


def save_relative_tradeoff_plot(summary, output_dir):
    x = summary["tolerance_value"].to_numpy(dtype=float)
    tol_labels = summary["tolerance"].tolist()

    fig, ax1 = plt.subplots(figsize=FIGSIZE_LINE)
    line1 = ax1.plot(
        x,
        summary["makespan_change_vs_base_pct_mean"],
        color=WASEDA_RED,
        marker="o",
        linewidth=2.5,
        label="Makespan change vs original NHEFT",
    )
    ax1.axhline(0, color=DARK, linewidth=1.0)
    ax1.set_xlabel("nheft_vcpu_eft_tolerance")
    ax1.set_ylabel("Makespan change (%)", color=WASEDA_RED)
    ax1.tick_params(axis="y", labelcolor=WASEDA_RED)
    ax1.set_xticks(x)
    ax1.set_xticklabels(tol_labels)
    add_grid(ax1)

    ax2 = ax1.twinx()
    line2 = ax2.plot(
        x,
        summary["vcpu_reduction_vs_base_pct_mean"],
        color=GREEN,
        marker="s",
        linewidth=2.5,
        label="vCPU reduction vs original NHEFT",
    )
    ax2.axhline(0, color=GREEN, linewidth=1.0, alpha=0.4)
    ax2.set_ylabel("vCPU reduction (%)", color=GREEN)
    ax2.tick_params(axis="y", labelcolor=GREEN)

    lines = line1 + line2
    labels = [line.get_label() for line in lines]
    ax1.legend(lines, labels, loc="best")
    ax1.set_title("Makespan Cost and vCPU Reduction vs Original NHEFT")
    fig.tight_layout()
    fig.savefig(os.path.join(output_dir, "relative_tradeoff_vs_original.png"), dpi=PLOT_DPI)
    plt.close(fig)


def save_tradeoff_scatter(summary, reference, output_dir):
    fig, ax = plt.subplots(figsize=FIGSIZE_TRADEOFF)
    ax.scatter(
        summary["nheft_vcpus_mean"],
        summary["nheft_makespan_mean"],
        s=90,
        color=WASEDA_RED,
        edgecolor="black",
        linewidth=0.8,
        label="NHEFT tolerance variants",
        zorder=3,
    )
    for _, row in summary.iterrows():
        ax.annotate(
            row["tolerance"],
            (row["nheft_vcpus_mean"], row["nheft_makespan_mean"]),
            textcoords="offset points",
            xytext=(7, 5),
            fontsize=9,
        )

    for label, color, marker in [
        ("DHEFT", GREY, "s"),
        ("Original NHEFT", DARK, "D"),
    ]:
        row = reference[reference["algorithm"] == label].iloc[0]
        ax.scatter(
            row["vcpus_mean"],
            row["makespan_mean"],
            s=120,
            color=color,
            marker=marker,
            edgecolor="black",
            linewidth=0.8,
            label=label,
            zorder=4,
        )

    ax.set_xlabel("Mean used vCPUs")
    ax.set_ylabel("Mean makespan")
    ax.set_title("Makespan and vCPU Trade-off")
    add_grid(ax)
    ax.legend()
    fig.tight_layout()
    fig.savefig(os.path.join(output_dir, "makespan_vcpu_tradeoff.png"), dpi=PLOT_DPI)
    plt.close(fig)


def save_combined_makespan_vcpu_plot(summary, reference, output_dir):
    """Draw the user's requested mixed line/bar view.

    Left axis: mean makespan as a line.
    Right axis: mean used vCPUs as bars.
    """
    dheft = reference[reference["algorithm"] == "DHEFT"].iloc[0]
    nheft0 = reference[reference["algorithm"] == "Original NHEFT"].iloc[0]
    variants = summary[~np.isclose(summary["tolerance_value"], BASE_TOLERANCE)].copy()

    labels = ["DHEFT", "NHEFT"]
    makespan_values = [dheft["makespan_mean"], nheft0["makespan_mean"]]
    vcpu_values = [dheft["vcpus_mean"], nheft0["vcpus_mean"]]

    for _, row in variants.iterrows():
        labels.append(f"NHEFT-{row['tolerance']}")
        makespan_values.append(row["nheft_makespan_mean"])
        vcpu_values.append(row["nheft_vcpus_mean"])

    x = np.arange(len(labels))
    fig, ax_makespan = plt.subplots(figsize=FIGSIZE_COMBINED)
    ax_vcpu = ax_makespan.twinx()

    bars = ax_vcpu.bar(
        x,
        vcpu_values,
        width=0.55,
        color=GREY,
        edgecolor=DARK,
        linewidth=0.8,
        alpha=0.78,
        label="Mean used vCPUs",
        zorder=1,
    )
    line = ax_makespan.plot(
        x,
        makespan_values,
        color=WASEDA_RED,
        marker="o",
        markersize=7,
        linewidth=2.8,
        label="Mean makespan",
        zorder=4,
    )

    ax_makespan.set_xlabel("Method")
    ax_makespan.set_ylabel("Mean makespan", color=WASEDA_RED)
    ax_makespan.tick_params(axis="y", labelcolor=WASEDA_RED)
    ax_makespan.set_xticks(x)
    ax_makespan.set_xticklabels(labels, rotation=25, ha="right")
    ax_makespan.set_ylim(0, finite_max(makespan_values) * 1.25)
    ax_makespan.grid(axis="y", linestyle="--", linewidth=0.7, alpha=0.35)
    ax_makespan.set_axisbelow(True)

    ax_vcpu.set_ylabel("Mean used vCPUs", color=DARK)
    ax_vcpu.tick_params(axis="y", labelcolor=DARK)
    ax_vcpu.set_ylim(0, finite_max(vcpu_values) * 1.35)

    for patch, value in zip(bars.patches, vcpu_values):
        ax_vcpu.annotate(
            f"{value:.1f}",
            (patch.get_x() + patch.get_width() / 2.0, patch.get_height()),
            textcoords="offset points",
            xytext=(0, 4),
            ha="center",
            va="bottom",
            fontsize=9,
            color=DARK,
        )

    for xi, value in zip(x, makespan_values):
        ax_makespan.annotate(
            f"{value:.2f}",
            (xi, value),
            textcoords="offset points",
            xytext=(0, 9),
            ha="center",
            va="bottom",
            fontsize=9,
            color=WASEDA_RED,
        )

    handles = [line[0], bars]
    labels_for_legend = [handle.get_label() for handle in handles]
    ax_makespan.legend(handles, labels_for_legend, loc="upper left")
    ax_makespan.set_title("Mean Makespan and vCPU Use")
    fig.tight_layout()
    fig.savefig(
        os.path.join(output_dir, "makespan_vcpu_combined_line_bar.png"),
        dpi=PLOT_DPI,
    )
    plt.close(fig)


def save_summary_table(summary, output_dir):
    display_cols = [
        "tolerance",
        "paired_seeds",
        "nheft_makespan_mean",
        "makespan_change_vs_base_pct_mean",
        "nheft_vcpus_mean",
        "vcpu_reduction_vs_base_pct_mean",
        "gain_nheft_over_dheft_pct_mean",
        "win_rate_over_dheft_pct",
        "within_5pct_and_vcpu_reduced_rate_pct",
    ]
    display = summary[display_cols].copy()
    rename = {
        "tolerance": "tol",
        "paired_seeds": "seeds",
        "nheft_makespan_mean": "NHEFT mean makespan",
        "makespan_change_vs_base_pct_mean": "makespan change vs 0.0 (%)",
        "nheft_vcpus_mean": "NHEFT mean vCPUs",
        "vcpu_reduction_vs_base_pct_mean": "vCPU reduction vs 0.0 (%)",
        "gain_nheft_over_dheft_pct_mean": "gain over DHEFT (%)",
        "win_rate_over_dheft_pct": "win rate over DHEFT (%)",
        "within_5pct_and_vcpu_reduced_rate_pct": "within 5% and fewer vCPUs (%)",
    }
    display = display.rename(columns=rename)
    for col in display.columns:
        if col not in ("tol", "seeds"):
            display[col] = display[col].map(lambda v: "" if pd.isna(v) else f"{v:.2f}")

    fig_height = max(4.0, 0.55 * (len(display) + 2))
    fig, ax = plt.subplots(figsize=(16, fig_height))
    ax.axis("off")
    table = ax.table(
        cellText=display.values,
        colLabels=display.columns,
        cellLoc="center",
        loc="center",
    )
    table.auto_set_font_size(False)
    table.set_fontsize(9)
    table.scale(1.0, 1.35)
    for (row, _col), cell in table.get_celld().items():
        cell.set_edgecolor("#555555")
        cell.set_linewidth(0.55)
        if row == 0:
            cell.set_text_props(weight="bold")
            cell.set_facecolor("#F0F0F0")
        else:
            cell.set_facecolor("#FFFFFF")

    fig.tight_layout()
    fig.savefig(os.path.join(output_dir, "tolerance_summary_table.png"), dpi=PLOT_DPI)
    plt.close(fig)


def write_analysis_manifest(
    output_dir,
    result_dir,
    raw_df,
    ok_df,
    complete_ok_df,
    paired_df,
    summary_df,
    complete_seed_report,
    expected_tolerance_labels,
):
    manifest = {
        "analysis": "E0 NHEFT vCPU EFT-tolerance analysis",
        "timestamp": datetime.now().strftime("%Y%m%d_%H%M%S"),
        "result_dir": result_dir,
        "raw_csv": os.path.join(result_dir, RAW_CSV_NAME),
        "raw_rows": int(len(raw_df)),
        "ok_rows": int(len(ok_df)),
        "complete_ok_rows": int(len(complete_ok_df)),
        "complete_seeds": int(complete_seed_report["is_complete"].sum()),
        "incomplete_seeds": int((~complete_seed_report["is_complete"]).sum()),
        "paired_rows": int(len(paired_df)),
        "paired_seeds": int(paired_df["seed"].nunique()),
        "complete_seed_rule": (
            "Only seeds with all observed tolerance values are included in "
            "summaries and plots."
        ),
        "expected_tolerances_for_complete_seed": expected_tolerance_labels,
        "tolerances": summary_df["tolerance"].tolist(),
        "baseline": "tolerance=0.0 is treated as original NHEFT",
        "notes": [
            "Makespan change vs original NHEFT is positive when the tolerance variant is slower.",
            "vCPU reduction vs original NHEFT is positive when the tolerance variant uses fewer vCPUs.",
            "Gain over DHEFT is the mean of per-run gains, not the gain from bucket-level means.",
        ],
    }
    with open(os.path.join(output_dir, "analysis_manifest.json"), "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)
        f.write("\n")


def main():
    args = parse_args()
    result_dir = resolve_result_dir(args.result_folder)
    if not result_dir:
        print("No E0 result folder found.")
        print(f"Expected a run_* folder under: {THIS_DIR}")
        raise SystemExit(1)

    output_dir = args.output_dir
    if output_dir:
        output_dir = os.path.abspath(output_dir)
    else:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_dir = os.path.join(result_dir, f"analysis_{timestamp}")
    os.makedirs(output_dir, exist_ok=True)

    raw_df = load_raw_csv(result_dir)
    ok_df = filter_ok_rows(raw_df)
    complete_ok_df, complete_seed_report, expected_tolerance_labels = filter_complete_seeds(ok_df)
    paired_df = build_paired_metrics(complete_ok_df)
    summary_df = build_tolerance_summary(paired_df)
    reference_df = build_reference_summary(paired_df)

    paired_csv = os.path.join(output_dir, "e0_seed_tolerance_paired_metrics.csv")
    summary_csv = os.path.join(output_dir, "e0_tolerance_summary.csv")
    reference_csv = os.path.join(output_dir, "e0_reference_summary.csv")
    complete_seed_report_csv = os.path.join(output_dir, "e0_complete_seed_report.csv")
    paired_df.to_csv(paired_csv, index=False)
    summary_df.to_csv(summary_csv, index=False)
    reference_df.to_csv(reference_csv, index=False)
    complete_seed_report.to_csv(complete_seed_report_csv, index=False)

    save_line_plots(summary_df, reference_df, output_dir)
    save_relative_tradeoff_plot(summary_df, output_dir)
    save_tradeoff_scatter(summary_df, reference_df, output_dir)
    save_combined_makespan_vcpu_plot(summary_df, reference_df, output_dir)
    save_summary_table(summary_df, output_dir)
    write_analysis_manifest(
        output_dir,
        result_dir,
        raw_df,
        ok_df,
        complete_ok_df,
        paired_df,
        summary_df,
        complete_seed_report,
        expected_tolerance_labels,
    )

    best_resource_row = summary_df.sort_values(
        ["vcpu_reduction_vs_base_pct_mean", "makespan_change_vs_base_pct_mean"],
        ascending=[False, True],
    ).iloc[0]
    best_balanced_candidates = summary_df[
        summary_df["within_5pct_and_vcpu_reduced_rate_pct"] > 0
    ].copy()

    print("=== E0 Analysis Complete ===")
    print(f"Input result dir: {result_dir}")
    print(f"Output dir: {output_dir}")
    print(f"Raw rows: {len(raw_df)}")
    print(f"OK rows: {len(ok_df)}")
    print(f"Complete seeds: {int(complete_seed_report['is_complete'].sum())}")
    print(f"Incomplete seeds dropped: {int((~complete_seed_report['is_complete']).sum())}")
    print(f"Complete-seed tolerance grid: {', '.join(expected_tolerance_labels)}")
    print(f"Paired rows: {len(paired_df)}")
    print(f"Paired seeds: {paired_df['seed'].nunique()}")
    print()
    print("Main CSV outputs:")
    print(f"  {relpath(summary_csv)}")
    print(f"  {relpath(paired_csv)}")
    print(f"  {relpath(reference_csv)}")
    print(f"  {relpath(complete_seed_report_csv)}")
    print()
    print("Main figures:")
    for name in [
        "makespan_by_tolerance.png",
        "vcpu_by_tolerance.png",
        "relative_tradeoff_vs_original.png",
        "makespan_vcpu_tradeoff.png",
        "makespan_vcpu_combined_line_bar.png",
        "tolerance_summary_table.png",
    ]:
        print(f"  {relpath(os.path.join(output_dir, name))}")
    print()
    print(
        "Largest mean vCPU reduction: "
        f"tolerance={best_resource_row['tolerance']}, "
        f"vCPU reduction={best_resource_row['vcpu_reduction_vs_base_pct_mean']:.2f}%, "
        f"makespan change={best_resource_row['makespan_change_vs_base_pct_mean']:.2f}%"
    )
    if not best_balanced_candidates.empty:
        best_balanced = best_balanced_candidates.sort_values(
            [
                "within_5pct_and_vcpu_reduced_rate_pct",
                "vcpu_reduction_vs_base_pct_mean",
            ],
            ascending=[False, False],
        ).iloc[0]
        print(
            "Best within-5%-and-fewer-vCPUs rate: "
            f"tolerance={best_balanced['tolerance']}, "
            f"rate={best_balanced['within_5pct_and_vcpu_reduced_rate_pct']:.2f}%"
        )


if __name__ == "__main__":
    main()
