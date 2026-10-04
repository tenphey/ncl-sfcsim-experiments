#!/usr/bin/env python3
"""Aggregate the 24 experiments/six scenarios without rerunning Java.

The script reads the newest ``run_*_<seed_count>`` directory for each of
e01x--e08z and summarizes the paired DHEFT, NHEFT, and GHEFT results written
by ``common_runner.py``.  Raw rows are filtered by the measured communication
values, not by the scenario directory name alone.

The default analysis uses 500-seed runs.  Change TARGET_SEED_COUNT below when
the same experiment set is rerun with another seed count.
"""

import argparse
import json
import math
import os
import zlib
from datetime import datetime
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
# EDAS rejects Matplotlib's default Type 3 PDF fonts.  Embed TrueType fonts
# (PDF Type 42) so the vector figures remain sharp and submission-compliant.
matplotlib.rcParams["pdf.fonttype"] = 42
matplotlib.rcParams["ps.fonttype"] = 42
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from common_runner import DATA_REVISION
from scipy.stats import wilcoxon
from matplotlib.lines import Line2D


FIVE_DIR = Path(__file__).resolve().parent

# Change this value to select the newest run with another number of seeds.
TARGET_SEED_COUNT = 500

# Keep the confidence-interval method identical to four/e3x and to the paper.
# The fixed seed makes regenerated tables reproducible.
BOOTSTRAP_CONFIDENCE = 0.95
BOOTSTRAP_RESAMPLES = 10000
BOOTSTRAP_RANDOM_SEED = 20260827

# The 10% rule is used for the balanced condition only.  The two directional
# conditions retain their 20% separation so that they remain clearly dominant.
BALANCED_RELATIVE_GAP_MAX_PERCENT = 10.0
DOMINANT_RELATIVE_GAP_MIN_PERCENT = 20.0

WASEDA_RED = "#8E1728"
GREEN = "#0B7F5B"
GREY = "#BDBDBD"
DARK = "#172A33"
ALGORITHM_KEYS = ("dheft", "nheft", "gheft")
# Display names are independent of the historical CSV keys and filenames.
ALGORITHM_LABELS = {
    "dheft": "DHEFT",
    "nheft": "NHEFT",
    "gheft": "G-NHEFT",
}

BUCKET_SPECS = [
    ("(0.10, 0.18]", 0.10, 0.18),
    ("(0.18, 0.32]", 0.18, 0.32),
    ("(0.32, 0.56]", 0.32, 0.56),
    ("(0.56, 1.00]", 0.56, 1.00),
    ("(1.00, 1.78]", 1.00, 1.78),
    ("(1.78, 3.16]", 1.78, 3.16),
    ("(3.16, 5.62]", 3.16, 5.62),
    ("(5.62, 10.00]", 5.62, 10.00),
]

COMPOSITIONS = {
    "x": "Balanced (CCR ~= IDR)",
    "y": "Image-dominant (CCR < IDR)",
    "z": "Data-dominant (CCR > IDR)",
}

PLOT_COLORS = {
    "dheft": DARK,
    "nheft": WASEDA_RED,
    "gheft": GREEN,
}
PLOT_MARKERS = {"dheft": "o", "nheft": "o", "gheft": "o"}

# Keep the e3x-compatible figures readable when they are inserted into a paper.
PLOT_DPI = 300
OVERVIEW_FIGSIZE = (13.8, 4.8)
OVERVIEW_AXIS_LABEL_FONTSIZE = 24
OVERVIEW_XTICK_FONTSIZE = 24
OVERVIEW_YTICK_FONTSIZE = 24
OVERVIEW_LEGEND_FONTSIZE = 16
OVERVIEW_LINE_ANNOTATION_FONTSIZE = 24
OVERVIEW_LINE_WIDTH = 2.8
OVERVIEW_MARKER_SIZE = 8
SHOW_OVERVIEW_X_AXIS_LABEL = False
SHOW_OVERVIEW_TITLE = False

# Larger factors lower makespan lines and labels without changing their values
# or the independent vCPU axis. Other figures retain the original 1.35 factor.
OVERVIEW_MAKESPAN_Y_MAX_FACTORS = {
    "e3xyz_mean_makespan_vcpu_overview-low": 1.8,
}

# 折线数值标注的位置，按输出图片、折线和数据点分别设置。
# 每个 tuple 是相对于圆点的 (水平偏移, 垂直偏移)，单位为 points。
# 每个列表按横轴数据点顺序排列；修改某一个数值时只需调整对应位置。
# 如果某张图的数据点少于列表长度，多余的位置会被忽略。
OVERVIEW_ANNOTATION_OFFSETS = {
    "e3xyz_mean_makespan_vcpu_overview-low": {
        "dheft": [(-36, 6), (-36, 6), (-36, 10), (-36, 6)],
        "nheft": [(0, -12), (0, -12), (0, -12), (0, -12)],
        "gheft": [(2, 6), (2, 6), (4, 8), (8, 6)],
    },
    "e3xyz_mean_makespan_vcpu_overview-high": {
        "dheft": [(0, 12), (0, 10), (-6, 10), (46, -10)],
        "nheft": [(0, -12), (0, -12), (0, -12), (0, -12)],
        "gheft": [(-80, -8), (-34, 0), (-46, 0), (5, -8)],
    },
    "e3xyz_mean_makespan_vcpu_overview-low-dheft-nheft": {
        "dheft": [(0, 10), (0, 10), (0, 10), (40, -8)],
        "nheft": [(0, -12), (0, -12), (0, -12), (0, -12)],
    },
    "e3xyz_mean_makespan_vcpu_overview-high-dheft-nheft": {
        "dheft": [(0, 10), (0, 10), (0, 10), (45, -10)],
        "nheft": [(0, -12), (0, -12), (0, -12), (0, -12)],
    },
}

RATE_FIGSIZE = (18, 8.5)
RATE_AXIS_LABEL_FONTSIZE = 30
RATE_XTICK_FONTSIZE = 30
RATE_YTICK_FONTSIZE = 30
RATE_LEGEND_FONTSIZE = 25
RATE_LEGEND_TITLE_FONTSIZE = 26
RATE_WIN_LEGEND_Y = 0.96
RATE_GAIN_LEGEND_Y = 0.42
RATE_MARKER_SIZE = 9
RATE_LINE_WIDTH = 2.8


def parse_args():
    parser = argparse.ArgumentParser(
        description="Aggregate experiments/six e01x--e08z raw results."
    )
    parser.add_argument(
        "--output-dir",
        help="Optional output directory. Default: experiments/six/analysis_<timestamp>_<seed_count>",
    )
    parser.add_argument("--allow-legacy-runs", action="store_true",
                        help="Explicitly analyze older complete runs without version/validation provenance")
    return parser.parse_args()


def scenario_specs():
    specs = []
    for index, (label, lower, upper) in enumerate(BUCKET_SPECS, start=1):
        for composition in ("x", "y", "z"):
            scenario = f"e{index:02d}{composition}"
            specs.append(
                {
                    "scenario": scenario,
                    "bucket_index": index,
                    "bucket_label": label,
                    "lower": lower,
                    "upper": upper,
                    "composition": composition,
                    "composition_label": COMPOSITIONS[composition],
                }
            )
    return specs


def find_latest_run_dir(scenario_dir, raw_csv_name, allow_legacy=False):
    candidates = []
    if not scenario_dir.is_dir():
        return None

    for path in scenario_dir.iterdir():
        if not path.is_dir() or not path.name.startswith("run_"):
            continue
        try:
            seed_count = int(path.name.rsplit("_", 1)[-1])
        except ValueError:
            continue
        if seed_count != TARGET_SEED_COUNT:
            continue
        manifest_path = path / "run_manifest.json"
        if not manifest_path.is_file():
            continue
        try:
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        complete = (manifest.get("completed_runs") == TARGET_SEED_COUNT
                    and manifest.get("num_seeds") == TARGET_SEED_COUNT
                    and manifest.get("status_counts", {}).get("ok") == TARGET_SEED_COUNT
                    and not manifest.get("interrupted", False))
        if "complete" in manifest:
            complete = complete and manifest["complete"] is True
        if not allow_legacy and (manifest.get("data_revision") != DATA_REVISION
                                 or not manifest.get("validation_required") or not manifest.get("classes_sha256")):
            continue
        if complete and (path / raw_csv_name).is_file():
            candidates.append(path)

    if not candidates:
        return None
    return max(candidates, key=lambda path: path.name)


def relative_gap_percent(ccr, idr):
    denominator = (ccr + idr) / 2.0
    if not np.isfinite(denominator) or denominator == 0.0:
        return np.nan
    return abs(ccr - idr) / denominator * 100.0


def load_and_filter(csv_path, spec):
    raw = pd.read_csv(csv_path)
    raw_rows = len(raw)
    if raw_rows != TARGET_SEED_COUNT or raw["seed"].duplicated().any():
        raise ValueError(f"Expected {TARGET_SEED_COUNT} unique seed rows: {csv_path}")
    if "status" not in raw.columns:
        raise ValueError(f"Missing status column: {csv_path}")

    numeric_columns = [
        "ccr_data",
        "idr_image",
        "nccr_total",
        *[f"{algorithm}_{metric}" for algorithm in ALGORITHM_KEYS for metric in ("makespan", "vcpus")],
    ]
    for column in numeric_columns:
        if column in raw.columns:
            raw[column] = pd.to_numeric(raw[column], errors="coerce")

    required = ["ccr_data", "idr_image", "nccr_total"]
    required += [
        f"{algorithm}_{metric}"
        for algorithm in ALGORITHM_KEYS
        for metric in ("makespan", "vcpus")
    ]
    missing = [column for column in required if column not in raw.columns]
    if missing:
        raise ValueError(f"Missing required columns in {csv_path}: {missing}")

    ok = raw[raw["status"].astype(str).eq("ok")].copy()
    ok_rows = len(ok)
    ok = ok.dropna(subset=required)
    finite = np.isfinite(ok[required].to_numpy(dtype=float)).all(axis=1)
    positive = (ok[[f"{algorithm}_{metric}" for algorithm in ALGORITHM_KEYS
                    for metric in ("makespan", "vcpus")]] > 0).all(axis=1)
    communication_valid = (ok[["ccr_data", "idr_image", "nccr_total"]] >= 0).all(axis=1)
    if (len(ok) != raw_rows or not finite.all() or not positive.all()
            or not communication_valid.all() or ok_rows != raw_rows):
        raise ValueError(f"Incomplete or invalid paired metrics: {csv_path}")
    if ok.empty:
        return raw_rows, ok_rows, ok

    ok["ccr_idr_relative_gap_pct"] = [
        relative_gap_percent(ccr, idr)
        for ccr, idr in zip(ok["ccr_data"], ok["idr_image"])
    ]
    bucket_match = (ok["nccr_total"] > spec["lower"]) & (
        ok["nccr_total"] <= spec["upper"]
    )
    composition = spec["composition"]
    if composition == "x":
        composition_match = (
            ok["ccr_idr_relative_gap_pct"]
            <= BALANCED_RELATIVE_GAP_MAX_PERCENT
        )
    elif composition == "y":
        composition_match = (
            (ok["ccr_data"] < ok["idr_image"])
            & (ok["ccr_idr_relative_gap_pct"] >= DOMINANT_RELATIVE_GAP_MIN_PERCENT)
        )
    else:
        composition_match = (
            (ok["ccr_data"] > ok["idr_image"])
            & (ok["ccr_idr_relative_gap_pct"] >= DOMINANT_RELATIVE_GAP_MIN_PERCENT)
        )
    return raw_rows, ok_rows, ok[bucket_match & composition_match].copy()


def finite_array(values):
    array = np.asarray(values, dtype=float)
    return array[np.isfinite(array)]


def deterministic_seed(seed_key):
    key_bytes = str(seed_key).encode("utf-8")
    return BOOTSTRAP_RANDOM_SEED + (zlib.crc32(key_bytes) & 0xFFFFFFFF)


def bootstrap_mean_ci(values, seed_key):
    array = finite_array(values)
    if array.size == 0:
        return np.nan, np.nan
    if array.size == 1 or np.allclose(array, array[0]):
        value = float(array.mean())
        return value, value

    rng = np.random.default_rng(deterministic_seed(seed_key))
    bootstrap_means = []
    remaining = BOOTSTRAP_RESAMPLES
    batch_size = 1000
    while remaining > 0:
        current_batch = min(batch_size, remaining)
        indices = rng.integers(0, array.size, size=(current_batch, array.size))
        bootstrap_means.append(array[indices].mean(axis=1))
        remaining -= current_batch

    bootstrap_means = np.concatenate(bootstrap_means)
    tail = (1.0 - BOOTSTRAP_CONFIDENCE) / 2.0
    low, high = np.quantile(bootstrap_means, [tail, 1.0 - tail])
    return float(low), float(high)


def distribution_summary(values, seed_key):
    array = finite_array(values)
    if array.size == 0:
        return {"n": 0, "mean": np.nan, "sd": np.nan, "ci95_low": np.nan, "ci95_high": np.nan}
    mean = float(array.mean())
    if array.size == 1:
        return {"n": 1, "mean": mean, "sd": np.nan, "ci95_low": mean, "ci95_high": mean}
    sd = float(array.std(ddof=1))
    ci_low, ci_high = bootstrap_mean_ci(array, seed_key)
    return {
        "n": int(array.size),
        "mean": mean,
        "sd": sd,
        "ci95_low": ci_low,
        "ci95_high": ci_high,
    }


def add_distribution(row, prefix, values, seed_key):
    summary = distribution_summary(values, seed_key)
    for suffix, value in summary.items():
        row[f"{prefix}_{suffix}"] = value


def wilcoxon_summary(left, right):
    left = np.asarray(left, dtype=float)
    right = np.asarray(right, dtype=float)
    finite = np.isfinite(left) & np.isfinite(right)
    left = left[finite]
    right = right[finite]
    differences = left - right
    if differences.size == 0:
        return {"n": 0, "nonzero_n": 0, "statistic": np.nan, "p_raw": np.nan}
    nonzero = ~np.isclose(differences, 0.0, rtol=1e-12, atol=1e-12)
    if not nonzero.any():
        statistic, p_value = 0.0, 1.0
    else:
        result = wilcoxon(
            left,
            right,
            zero_method="wilcox",
            correction=False,
            alternative="two-sided",
            method="auto",
        )
        statistic, p_value = float(result.statistic), float(result.pvalue)
    return {
        "n": int(differences.size),
        "nonzero_n": int(nonzero.sum()),
        "statistic": statistic,
        "p_raw": p_value,
    }


def holm_adjust(values):
    values = np.asarray(values, dtype=float)
    adjusted = np.full(values.shape, np.nan, dtype=float)
    positions = np.flatnonzero(np.isfinite(values))
    if positions.size == 0:
        return adjusted
    order = positions[np.argsort(values[positions])]
    sorted_values = values[order]
    corrected = np.maximum.accumulate(sorted_values * (len(sorted_values) - np.arange(len(sorted_values))))
    corrected = np.minimum(corrected, 1.0)
    adjusted[order] = corrected
    return adjusted


def summarize_scenario(spec, result_dir, csv_path):
    raw_rows, ok_rows, valid = load_and_filter(csv_path, spec)
    row = dict(spec)
    row.update(
        {
            "data_status": "ok" if not valid.empty else "no_valid_rows",
            "result_dir": str(result_dir),
            "raw_rows": raw_rows,
            "ok_rows": ok_rows,
            "valid_rows": len(valid),
        }
    )
    if valid.empty:
        return row, None

    for algorithm in ALGORITHM_KEYS:
        add_distribution(
            row,
            f"{algorithm}_makespan",
            valid[f"{algorithm}_makespan"],
            f"{spec['scenario']}:{algorithm}:makespan",
        )
        add_distribution(
            row,
            f"{algorithm}_vcpus",
            valid[f"{algorithm}_vcpus"],
            f"{spec['scenario']}:{algorithm}:vcpus",
        )

    dheft_makespan = valid["dheft_makespan"].to_numpy()
    nheft_makespan = valid["nheft_makespan"].to_numpy()
    gheft_makespan = valid["gheft_makespan"].to_numpy()
    dheft_vcpus = valid["dheft_vcpus"].to_numpy()
    nheft_vcpus = valid["nheft_vcpus"].to_numpy()
    gheft_vcpus = valid["gheft_vcpus"].to_numpy()

    nheft_gain = (dheft_makespan - nheft_makespan) / dheft_makespan * 100.0
    gheft_gain = (dheft_makespan - gheft_makespan) / dheft_makespan * 100.0
    gheft_change = (gheft_makespan - nheft_makespan) / nheft_makespan * 100.0
    gheft_vcpu_reduction = (nheft_vcpus - gheft_vcpus) / nheft_vcpus * 100.0

    add_distribution(
        row,
        "nheft_gain_over_dheft_pct",
        nheft_gain,
        f"{spec['scenario']}:nheft_gain_over_dheft_pct",
    )
    add_distribution(
        row,
        "gheft_gain_over_dheft_pct",
        gheft_gain,
        f"{spec['scenario']}:gheft_gain_over_dheft_pct",
    )
    add_distribution(
        row,
        "gheft_change_vs_nheft_pct",
        gheft_change,
        f"{spec['scenario']}:gheft_change_vs_nheft_pct",
    )
    add_distribution(
        row,
        "gheft_vcpu_reduction_vs_nheft_pct",
        gheft_vcpu_reduction,
        f"{spec['scenario']}:gheft_vcpu_reduction_vs_nheft_pct",
    )
    nheft_wins = nheft_makespan < dheft_makespan
    gheft_wins_vs_dheft = gheft_makespan < dheft_makespan
    gheft_resource_saving = gheft_vcpus < nheft_vcpus
    gheft_joint_success = gheft_wins_vs_dheft & gheft_resource_saving
    row["nheft_win_count"] = int(nheft_wins.sum())
    row["gheft_win_vs_dheft_count"] = int(gheft_wins_vs_dheft.sum())
    row["gheft_resource_saving_count"] = int(gheft_resource_saving.sum())
    row["gheft_joint_success_count"] = int(gheft_joint_success.sum())
    row["nheft_win_rate_pct"] = float(nheft_wins.mean() * 100.0)
    row["gheft_win_rate_vs_dheft_pct"] = float(gheft_wins_vs_dheft.mean() * 100.0)
    row["gheft_resource_saving_rate_vs_nheft_pct"] = float(gheft_resource_saving.mean() * 100.0)
    row["gheft_joint_success_rate_pct"] = float(gheft_joint_success.mean() * 100.0)

    statistical_rows = []
    comparisons = [
        ("NHEFT_vs_DHEFT_makespan", dheft_makespan, nheft_makespan),
        ("GHEFT_vs_DHEFT_makespan", dheft_makespan, gheft_makespan),
        ("GHEFT_vs_NHEFT_makespan", nheft_makespan, gheft_makespan),
        ("GHEFT_vs_NHEFT_vcpus", nheft_vcpus, gheft_vcpus),
    ]
    for comparison, left, right in comparisons:
        test = wilcoxon_summary(left, right)
        statistical_rows.append(
            {
                "scenario": spec["scenario"],
                "bucket_index": spec["bucket_index"],
                "bucket_label": spec["bucket_label"],
                "composition": spec["composition"],
                "composition_label": spec["composition_label"],
                "comparison": comparison,
                **test,
            }
        )
    return row, statistical_rows


def aggregate_bucket_means(scenario_df):
    if "data_status" in scenario_df.columns:
        usable = scenario_df[scenario_df["data_status"].eq("ok")].copy()
    else:
        usable = scenario_df.iloc[0:0].copy()
    rows = []
    mean_columns = [
        f"{algorithm}_{metric}_mean"
        for algorithm in ALGORITHM_KEYS
        for metric in ("makespan", "vcpus")
    ]
    for index, (label, lower, upper) in enumerate(BUCKET_SPECS, start=1):
        bucket = usable[usable["bucket_index"].eq(index)]
        row = {
            "bucket_index": index,
            "bucket_label": label,
            "n_available_compositions": int(bucket["composition"].nunique()),
        }
        for column in mean_columns:
            row[column] = (
                float(bucket[column].mean())
                if not bucket.empty and column in bucket.columns
                else np.nan
            )
        rows.append(row)
    return pd.DataFrame(rows)


def markdown_table(frame, columns=None):
    if columns is not None:
        frame = frame[columns]
    frame = frame.copy()
    values = frame.fillna("").astype(str)
    header = "| " + " | ".join(values.columns) + " |"
    divider = "| " + " | ".join("---" for _ in values.columns) + " |"
    lines = [header, divider]
    for _, row in values.iterrows():
        lines.append("| " + " | ".join(row.tolist()) + " |")
    return "\n".join(lines) + "\n"


def write_markdown(frame, path, title, columns=None, note=None):
    with path.open("w", encoding="utf-8") as target:
        target.write(f"# {title}\n\n")
        if note:
            target.write(note + "\n\n")
        target.write(markdown_table(frame, columns))


def save_figure(fig, output_dir, stem):
    fig.tight_layout()
    fig.savefig(output_dir / f"{stem}.png", dpi=300, bbox_inches="tight")
    fig.savefig(output_dir / f"{stem}.pdf", format="pdf", bbox_inches="tight")
    plt.close(fig)


def plot_algorithm_lines(scenario_df, output_dir, metric, ylabel, stem, title):
    fig, axes = plt.subplots(1, 3, figsize=(19, 5.8), sharex=True)
    for axis, composition in zip(axes, ("x", "y", "z")):
        subset = scenario_df[
            (scenario_df["composition"] == composition)
            & scenario_df["data_status"].eq("ok")
        ].sort_values("bucket_index")
        for algorithm in ALGORITHM_KEYS:
            column = f"{algorithm}_{metric}_mean"
            axis.plot(
                subset["bucket_label"],
                subset[column],
                marker=PLOT_MARKERS[algorithm],
                color=PLOT_COLORS[algorithm],
                linewidth=2.2,
                label=ALGORITHM_LABELS[algorithm],
            )
        axis.set_title(COMPOSITIONS[composition], fontsize=13)
        axis.tick_params(axis="x", labelrotation=45, labelsize=9)
        axis.tick_params(axis="y", labelsize=10)
        axis.grid(axis="y", linestyle=":", alpha=0.45)
        axis.set_xlabel("NCCR bucket")
        axis.set_ylabel(ylabel)
    handles, labels = axes[0].get_legend_handles_labels()
    fig.legend(handles, labels, loc="upper center", ncol=4, frameon=True)
    fig.suptitle(title, fontsize=16)
    save_figure(fig, output_dir, stem)


def plot_nheft_rates(scenario_df, output_dir):
    fig, axes = plt.subplots(1, 3, figsize=(19, 5.8), sharex=True)
    for axis, composition in zip(axes, ("x", "y", "z")):
        subset = scenario_df[
            (scenario_df["composition"] == composition)
            & scenario_df["data_status"].eq("ok")
        ].sort_values("bucket_index")
        axis.plot(
            subset["bucket_label"],
            subset["nheft_gain_over_dheft_pct_mean"],
            marker="o",
            color="#1F77B4",
            linewidth=2.2,
            label="NHEFT gain vs DHEFT (%)",
        )
        axis.plot(
            subset["bucket_label"],
            subset["nheft_win_rate_pct"],
            marker="s",
            color=WASEDA_RED,
            linewidth=2.2,
            label="NHEFT win rate (%)",
        )
        axis.set_title(COMPOSITIONS[composition], fontsize=13)
        axis.tick_params(axis="x", labelrotation=45, labelsize=9)
        axis.tick_params(axis="y", labelsize=10)
        axis.grid(axis="y", linestyle=":", alpha=0.45)
        axis.set_xlabel("NCCR bucket")
        axis.set_ylabel("Percentage (%)")
        axis.set_ylim(bottom=0)
    handles, labels = axes[0].get_legend_handles_labels()
    fig.legend(handles, labels, loc="upper center", ncol=2, frameon=True)
    fig.suptitle("NHEFT gain rate and win rate by communication composition", fontsize=16)
    save_figure(fig, output_dir, "nheft_gain_win_rate")


def plot_gheft_tradeoff(scenario_df, output_dir):
    fig, axes = plt.subplots(1, 3, figsize=(19, 5.8), sharex=True)
    for axis, composition in zip(axes, ("x", "y", "z")):
        subset = scenario_df[
            (scenario_df["composition"] == composition)
            & scenario_df["data_status"].eq("ok")
        ].sort_values("bucket_index")
        axis.plot(
            subset["bucket_label"],
            subset["gheft_gain_over_dheft_pct_mean"],
            marker="o",
            color="#1F77B4",
            linewidth=2.2,
            label=f"{ALGORITHM_LABELS['gheft']} gain vs DHEFT (%)",
        )
        axis.plot(
            subset["bucket_label"],
            subset["gheft_change_vs_nheft_pct_mean"],
            marker="s",
            color=WASEDA_RED,
            linewidth=2.2,
            label=f"{ALGORITHM_LABELS['gheft']} makespan change vs NHEFT (%)",
        )
        axis.plot(
            subset["bucket_label"],
            subset["gheft_vcpu_reduction_vs_nheft_pct_mean"],
            marker="^",
            color="#0B7F5B",
            linewidth=2.2,
            label=f"{ALGORITHM_LABELS['gheft']} vCPU reduction vs NHEFT (%)",
        )
        axis.axhline(0.0, color="#777777", linewidth=0.8)
        axis.set_title(COMPOSITIONS[composition], fontsize=13)
        axis.tick_params(axis="x", labelrotation=45, labelsize=9)
        axis.tick_params(axis="y", labelsize=10)
        axis.grid(axis="y", linestyle=":", alpha=0.45)
        axis.set_xlabel("NCCR bucket")
        axis.set_ylabel("Percentage (%)")
    handles, labels = axes[0].get_legend_handles_labels()
    fig.legend(handles, labels, loc="upper center", ncol=3, frameon=True)
    fig.suptitle(f"{ALGORITHM_LABELS['gheft']} performance and resource trade-off", fontsize=16)
    save_figure(fig, output_dir, "gheft_tradeoff")


def format_number(value, digits=2):
    if pd.isna(value):
        return ""
    return f"{float(value):.{digits}f}"


def format_percent(value, digits=2):
    text = format_number(value, digits)
    return f"{text}%" if text else ""


def finite_max(values, default=1.0):
    array = np.asarray(values, dtype=float)
    array = array[np.isfinite(array)]
    if array.size == 0:
        return default
    return float(np.max(array))


def annotate_line_points(
    axis,
    x_values,
    y_values,
    color,
    fmt,
    xytext=(0, 8),
    xytexts=None,
    horizontal_alignment="center",
    horizontal_alignments=None,
    vertical_alignment="bottom",
):
    for index, (x_value, y_value) in enumerate(zip(x_values, y_values)):
        if not np.isfinite(y_value):
            continue
        if xytexts is None:
            point_xytext = xytext
        elif index < len(xytexts):
            point_xytext = xytexts[index]
        else:
            # Keep plotting robust if a future subset has more points than
            # the manually configured annotation list.
            point_xytext = xytexts[-1]
        point_alignment = (
            horizontal_alignment
            if horizontal_alignments is None
            else horizontal_alignments[index]
        )
        axis.annotate(
            fmt.format(y_value),
            (x_value, y_value),
            textcoords="offset points",
            xytext=point_xytext,
            ha=point_alignment,
            va=vertical_alignment,
            fontsize=OVERVIEW_LINE_ANNOTATION_FONTSIZE,
            color=color,
        )


def save_e3x_overview_plot(
    bucket_df,
    output_dir,
    stem,
    title,
    include_gheft=True,
    wrap_bucket_labels=True,
    split_legend=False,
    annotation_offsets=None,
):
    """Save the overview with the exact visual grammar used by four/e3x."""
    frame = bucket_df.sort_values("bucket_index").copy()
    frame = frame[frame["n_available_compositions"] > 0].copy()
    if frame.empty:
        return

    x = np.arange(len(frame))
    labels = frame["bucket_label"].tolist()
    makespan_dheft = frame["dheft_makespan_mean"].to_numpy(dtype=float)
    makespan_nheft = frame["nheft_makespan_mean"].to_numpy(dtype=float)
    makespan_gheft = frame["gheft_makespan_mean"].to_numpy(dtype=float)
    vcpu_dheft = frame["dheft_vcpus_mean"].to_numpy(dtype=float)
    vcpu_nheft = frame["nheft_vcpus_mean"].to_numpy(dtype=float)
    vcpu_gheft = frame["gheft_vcpus_mean"].to_numpy(dtype=float)

    fig, ax_makespan = plt.subplots(figsize=OVERVIEW_FIGSIZE)
    ax_vcpu = ax_makespan.twinx()
    bar_width = 0.22
    if include_gheft:
        dheft_bar_x, nheft_bar_x, gheft_bar_x = x - bar_width, x, x + bar_width
    else:
        dheft_bar_x, nheft_bar_x = x - bar_width / 2, x + bar_width / 2

    bars_dheft = ax_vcpu.bar(
        dheft_bar_x,
        vcpu_dheft,
        width=bar_width,
        color=GREY,
        edgecolor=DARK,
        linewidth=0.8,
        alpha=0.35,
        label="DHEFT mean used vCPUs",
        zorder=1,
    )
    bars_nheft = ax_vcpu.bar(
        nheft_bar_x,
        vcpu_nheft,
        width=bar_width,
        color=WASEDA_RED,
        edgecolor=WASEDA_RED,
        linewidth=0.8,
        alpha=0.25,
        label="NHEFT mean used vCPUs",
        zorder=1,
    )
    bars_gheft = None
    if include_gheft:
        bars_gheft = ax_vcpu.bar(
            gheft_bar_x,
            vcpu_gheft,
            width=bar_width,
            color=GREEN,
            edgecolor=GREEN,
            linewidth=0.8,
            alpha=0.25,
            label=f"{ALGORITHM_LABELS['gheft']} mean used vCPUs",
            zorder=1,
        )

    line_dheft = ax_makespan.plot(
        x,
        makespan_dheft,
        color=DARK,
        marker="o",
        markersize=OVERVIEW_MARKER_SIZE,
        linewidth=OVERVIEW_LINE_WIDTH,
        label="DHEFT mean makespan",
        zorder=4,
    )
    line_nheft = ax_makespan.plot(
        x,
        makespan_nheft,
        color=WASEDA_RED,
        marker="o",
        markersize=OVERVIEW_MARKER_SIZE,
        linewidth=OVERVIEW_LINE_WIDTH,
        label="NHEFT mean makespan",
        zorder=4,
    )
    line_gheft = None
    if include_gheft:
        line_gheft = ax_makespan.plot(
            x,
            makespan_gheft,
            color=GREEN,
            marker="o",
            markersize=OVERVIEW_MARKER_SIZE,
            linewidth=OVERVIEW_LINE_WIDTH,
            label=f"{ALGORITHM_LABELS['gheft']} mean makespan",
            zorder=4,
        )

    if SHOW_OVERVIEW_X_AXIS_LABEL:
        ax_makespan.set_xlabel("NCCR bucket", fontsize=OVERVIEW_AXIS_LABEL_FONTSIZE)
    if SHOW_OVERVIEW_TITLE:
        ax_makespan.set_title(title, fontsize=OVERVIEW_AXIS_LABEL_FONTSIZE)
    ax_makespan.set_ylabel("Mean makespan", color=DARK, fontsize=OVERVIEW_AXIS_LABEL_FONTSIZE)
    ax_vcpu.set_ylabel("Mean used vCPUs", color=DARK, fontsize=OVERVIEW_AXIS_LABEL_FONTSIZE)
    ax_makespan.set_xticks(x)
    display_labels = [label.replace(", ", ",\n") for label in labels] if wrap_bucket_labels else labels
    ax_makespan.set_xticklabels(display_labels, ha="center", fontsize=OVERVIEW_XTICK_FONTSIZE)
    ax_makespan.tick_params(axis="y", labelcolor=DARK, labelsize=OVERVIEW_YTICK_FONTSIZE)
    ax_vcpu.tick_params(axis="y", labelcolor=DARK, labelsize=OVERVIEW_YTICK_FONTSIZE)

    makespan_values = [makespan_dheft, makespan_nheft]
    vcpu_values = [vcpu_dheft, vcpu_nheft]
    if include_gheft:
        makespan_values.append(makespan_gheft)
        vcpu_values.append(vcpu_gheft)
    makespan_y_max_factor = OVERVIEW_MAKESPAN_Y_MAX_FACTORS.get(stem, 1.35)
    ax_makespan.set_ylim(0, finite_max(np.concatenate(makespan_values)) * makespan_y_max_factor)
    ax_vcpu.set_ylim(0, finite_max(np.concatenate(vcpu_values)) * 1.25)
    ax_makespan.grid(axis="y", linestyle="--", linewidth=0.6, alpha=0.35)

    annotation_offsets = annotation_offsets or {}
    dheft_offsets = annotation_offsets.get("dheft")
    nheft_offsets = annotation_offsets.get("nheft")
    gheft_offsets = annotation_offsets.get("gheft")
    annotate_line_points(
        ax_makespan,
        x,
        makespan_dheft,
        DARK,
        "{:.2f}",
        xytext=(0, 10),
        xytexts=dheft_offsets,
        horizontal_alignment="center",
    )
    annotate_line_points(
        ax_makespan,
        x,
        makespan_nheft,
        WASEDA_RED,
        "{:.2f}",
        xytext=(0, -12),
        xytexts=nheft_offsets,
        vertical_alignment="top",
    )
    if include_gheft:
        annotate_line_points(
            ax_makespan,
            x,
            makespan_gheft,
            GREEN,
            "{:.2f}",
            xytext=(8, 10),
            xytexts=gheft_offsets,
            horizontal_alignment="left",
        )

    if split_legend:
        resource_handles = [bars_dheft, bars_nheft]
        resource_labels = ["DHEFT", "NHEFT"]
        performance_handles = [line_dheft[0], line_nheft[0]]
        performance_labels = ["DHEFT", "NHEFT"]
        if include_gheft:
            resource_handles.append(bars_gheft)
            resource_labels.append(ALGORITHM_LABELS["gheft"])
            performance_handles.append(line_gheft[0])
            performance_labels.append(ALGORITHM_LABELS["gheft"])
        resource_legend = ax_makespan.legend(
            resource_handles,
            resource_labels,
            title="Mean used vCPUs",
            loc="upper left",
            fontsize=OVERVIEW_LEGEND_FONTSIZE,
            title_fontsize=OVERVIEW_LEGEND_FONTSIZE,
            ncol=3,
            frameon=True,
        )
        ax_makespan.add_artist(resource_legend)
        ax_makespan.legend(
            performance_handles,
            performance_labels,
            title="Mean makespan",
            loc="upper right",
            fontsize=OVERVIEW_LEGEND_FONTSIZE,
            title_fontsize=OVERVIEW_LEGEND_FONTSIZE,
            ncol=3,
            frameon=True,
        )
    else:
        if include_gheft:
            handles = [line_dheft[0], line_nheft[0], line_gheft[0], bars_dheft, bars_nheft, bars_gheft]
        else:
            handles = [line_dheft[0], line_nheft[0], bars_dheft, bars_nheft]
        ax_makespan.legend(
            handles,
            [handle.get_label() for handle in handles],
            loc="upper left",
            fontsize=OVERVIEW_LEGEND_FONTSIZE,
            ncol=3,
            frameon=True,
        )

    fig.tight_layout(pad=0.6)
    fig.savefig(output_dir / f"{stem}.png", dpi=PLOT_DPI, bbox_inches="tight")
    fig.savefig(output_dir / f"{stem}.pdf", format="pdf", bbox_inches="tight")
    plt.close(fig)


def save_e3x_overview_plots(bucket_df, output_dir):
    """Create the full, low/high, and DHEFT/NHEFT overview variants."""
    save_e3x_overview_plot(
        bucket_df,
        output_dir,
        "e3x_makespan_vcpu_overview",
        f"DHEFT, NHEFT, and {ALGORITHM_LABELS['gheft']} overview",
        include_gheft=True,
    )
    for suffix, subset in (("-1", bucket_df[bucket_df["bucket_index"] <= 4]), ("-2", bucket_df[bucket_df["bucket_index"] > 4])):
        save_e3x_overview_plot(
            subset,
            output_dir,
            f"e3x_makespan_vcpu_overview{suffix}",
            f"DHEFT, NHEFT, and {ALGORITHM_LABELS['gheft']} overview",
            include_gheft=True,
        )
    for name, subset in (
        ("e3xyz_mean_makespan_vcpu_overview-low", bucket_df[bucket_df["bucket_index"] <= 4]),
        ("e3xyz_mean_makespan_vcpu_overview-high", bucket_df[bucket_df["bucket_index"] > 4]),
        ("e3xyz_mean_makespan_vcpu_overview-low-dheft-nheft", bucket_df[bucket_df["bucket_index"] <= 4]),
        ("e3xyz_mean_makespan_vcpu_overview-high-dheft-nheft", bucket_df[bucket_df["bucket_index"] > 4]),
    ):
        save_e3x_overview_plot(
            subset,
            output_dir,
            name,
            name,
            include_gheft="dheft-nheft" not in name,
            wrap_bucket_labels=False,
            split_legend=True,
            annotation_offsets=OVERVIEW_ANNOTATION_OFFSETS[name],
        )


def save_nheft_gain_win_rate_combined(scenario_df, output_dir):
    """Save the six-curve plot with the exact e3x line and legend styling."""
    fig, ax = plt.subplots(figsize=RATE_FIGSIZE)
    styles = {
        "x": {"label": r"Balanced ($\mathrm{CCR}\approx\mathrm{IDR}$)", "color": "#4472C4", "marker": "o"},
        "y": {"label": r"Image-dominant ($\mathrm{CCR}<\mathrm{IDR}$)", "color": "#ED7D31", "marker": "s"},
        "z": {"label": r"Data-dominant ($\mathrm{CCR}>\mathrm{IDR}$)", "color": "#548235", "marker": "^"},
    }
    for composition in ("x", "y", "z"):
        subset = scenario_df[
            (scenario_df["composition"] == composition)
            & scenario_df["data_status"].eq("ok")
        ].sort_values("bucket_index")
        if subset.empty:
            continue
        x = subset["bucket_index"].to_numpy(dtype=float) - 1.0
        style = styles[composition]
        ax.plot(
            x,
            subset["nheft_gain_over_dheft_pct_mean"],
            color=style["color"],
            marker=style["marker"],
            markersize=RATE_MARKER_SIZE,
            linewidth=RATE_LINE_WIDTH,
            linestyle="-",
            zorder=3,
        )
        ax.plot(
            x,
            subset["nheft_win_rate_pct"],
            color=style["color"],
            marker=style["marker"],
            markersize=RATE_MARKER_SIZE,
            linestyle="--",
            markerfacecolor="white",
            markeredgewidth=1.5,
            linewidth=RATE_LINE_WIDTH,
            zorder=3,
        )
    ax.axhline(0, color=DARK, linewidth=0.9, alpha=0.7, zorder=1)
    ax.set_xticks(
        np.arange(len(BUCKET_SPECS)),
        [label.replace(", ", ",\n") for label, _, _ in BUCKET_SPECS],
    )
    ax.tick_params(axis="x", labelsize=RATE_XTICK_FONTSIZE)
    ax.tick_params(axis="y", labelsize=RATE_YTICK_FONTSIZE)
    ax.set_ylabel("Percentage (%)", fontsize=RATE_AXIS_LABEL_FONTSIZE)
    if SHOW_OVERVIEW_X_AXIS_LABEL:
        ax.set_xlabel("NCCR bucket", fontsize=RATE_AXIS_LABEL_FONTSIZE)
    ax.set_ylim(-5, 140)
    ax.set_yticks(np.arange(0, 101, 20))
    ax.grid(axis="y", linestyle="--", linewidth=1.0, color="#8A8A8A", alpha=0.8)
    win_handles = [
        Line2D(
            [0], [0], color=style["color"], marker=style["marker"],
            markersize=RATE_MARKER_SIZE, markerfacecolor="white",
            markeredgecolor=style["color"], markeredgewidth=1.5,
            linewidth=RATE_LINE_WIDTH, linestyle="--", label=style["label"],
        )
        for style in styles.values()
    ]
    gain_handles = [
        Line2D(
            [0], [0], color=style["color"], marker=style["marker"],
            markersize=RATE_MARKER_SIZE, markerfacecolor=style["color"],
            markeredgecolor=style["color"], linewidth=RATE_LINE_WIDTH,
            linestyle="-", label=style["label"],
        )
        for style in styles.values()
    ]
    win_legend = ax.legend(
        handles=win_handles,
        title="Win rate",
        loc="upper left",
        bbox_to_anchor=(0.01, RATE_WIN_LEGEND_Y),
        fontsize=RATE_LEGEND_FONTSIZE,
        title_fontsize=RATE_LEGEND_TITLE_FONTSIZE,
        ncol=1,
        frameon=True,
    )
    ax.add_artist(win_legend)
    ax.legend(
        handles=gain_handles,
        title="Gain rate",
        loc="center right",
        bbox_to_anchor=(0.99, RATE_GAIN_LEGEND_Y),
        fontsize=RATE_LEGEND_FONTSIZE,
        title_fontsize=RATE_LEGEND_TITLE_FONTSIZE,
        ncol=1,
        frameon=True,
    )
    save_figure(fig, output_dir, "nheft_gain_win_rate_combined")


def binomial_ci(count, total):
    if not total:
        return np.nan, np.nan
    p = float(count) / float(total)
    z = 1.96
    denominator = 1.0 + z * z / total
    center = (p + z * z / (2.0 * total)) / denominator
    half = z * math.sqrt((p * (1.0 - p) + z * z / (4.0 * total)) / total) / denominator
    return max(0.0, (center - half) * 100.0), min(100.0, (center + half) * 100.0)


def write_latex_table(frame, path, title, columns, headers, alignment=None):
    alignment = alignment or ("l" + "r" * (len(columns) - 1))
    with path.open("w", encoding="utf-8") as target:
        target.write("% Auto-generated by experiments/five/analyze_results.py\n")
        target.write(f"\\begin{{table}}[t]\n\\centering\n\\caption{{{title}}}\n")
        target.write(f"\\label{{tab:{path.stem}}}\n\\begin{{tabular}}{{{alignment}}}\n\\hline\n")
        target.write(" & ".join(headers) + " \\\\ \n\\hline\n")
        for _, row in frame[columns].iterrows():
            values = [str(row[column]) if not pd.isna(row[column]) else "" for column in columns]
            target.write(" & ".join(values) + " \\\\ \n")
        target.write("\\hline\n\\end{tabular}\n\\end{table}\n")


def write_nheft_statistical_latex(detail, path):
    """Write the compact grouped NHEFT table used by four/e3x."""
    lines = [
        "% Auto-generated by experiments/five/analyze_results.py",
        r"\begin{table}[t]",
        r"\centering",
        r"\caption{Paired per-seed NHEFT makespan gains over DHEFT.}",
        r"\label{tab:nheft_statistics}",
        r"\scriptsize",
        r"\setlength{\tabcolsep}{1.2pt}",
        r"\resizebox{\columnwidth}{!}{%",
        r"\begin{tabular}{@{}l|cc|cc|cc@{}}",
        r"\hline",
        (
            r"& \multicolumn{2}{c|}{Balanced} "
            r"& \multicolumn{2}{c|}{Image-dominant} "
            r"& \multicolumn{2}{c}{Data-dominant} \\"
        ),
        r"\cline{2-7}",
        (
            r"NCCR bucket & Gain $\pm$ SD & 95\% CI "
            r"& Gain $\pm$ SD & 95\% CI "
            r"& Gain $\pm$ SD & 95\% CI \\"
        ),
        r"\hline",
    ]
    for bucket_label, _, _ in BUCKET_SPECS:
        cells = [bucket_label]
        for composition in ("x", "y", "z"):
            matching = detail[
                detail["nccr_bucket"].eq(bucket_label)
                & detail["scenario"].str.endswith(composition)
            ]
            if len(matching) != 1:
                raise RuntimeError(
                    f"Expected one NHEFT row for {bucket_label}/{composition}, "
                    f"found {len(matching)}."
                )
            row = matching.iloc[0]
            gain = f"{float(row['gain_mean_pct']):.2f}$\\pm${float(row['gain_sd_pct']):.2f}"
            if np.isfinite(row["p_holm"]) and float(row["p_holm"]) < 0.05:
                gain += r"$^{*}$"
            cells.extend(
                [
                    gain,
                    "[{:.2f},{:.2f}]".format(
                        float(row["gain_ci95_low_pct"]),
                        float(row["gain_ci95_high_pct"]),
                    ),
                ]
            )
        lines.append(" & ".join(cells) + r" \\")
    lines.extend(
        [
            r"\hline",
            r"\end{tabular}",
            r"}",
            r"\vspace{1mm}",
            (
                r"\parbox{\columnwidth}{\raggedright\scriptsize\textit{Note:} "
                r"Values are mean per-seed gain $\pm$ SD (\%); brackets show 95\% "
                r"bootstrap CIs. $^{*}$Significant after Holm-corrected paired "
                r"Wilcoxon tests ($\alpha=0.05$).}"
            ),
            r"\end{table}",
        ]
    )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_gheft_metrics_latex(detail, path):
    """Write the grouped 10-column GHEFT table used by four/e3x."""
    lines = [
        "% Auto-generated by experiments/five/analyze_results.py",
        r"\begin{table}[t]",
        r"\centering",
        r"\caption{GHEFT performance and resource effects for each NCCR bucket and communication composition.}",
        r"\label{tab:gheft_metrics}",
        r"\scriptsize",
        r"\setlength{\tabcolsep}{1.0pt}",
        r"\resizebox{\columnwidth}{!}{%",
        r"\begin{tabular}{@{}l|rrr|rrr|rrr@{}}",
        r"\hline",
        (
            r"& \multicolumn{3}{c|}{Balanced} "
            r"& \multicolumn{3}{c|}{Image-dominant} "
            r"& \multicolumn{3}{c}{Data-dominant} \\"
        ),
        r"\cline{2-10}",
        (
            r"NCCR bucket & Gain & $\Delta M$ & $\Delta U$ "
            r"& Gain & $\Delta M$ & $\Delta U$ "
            r"& Gain & $\Delta M$ & $\Delta U$ \\"
        ),
        r"\hline",
    ]
    for bucket_label, _, _ in BUCKET_SPECS:
        cells = [bucket_label]
        for composition in ("x", "y", "z"):
            matching = detail[
                detail["nccr_bucket"].eq(bucket_label)
                & detail["scenario"].str.endswith(composition)
            ]
            if len(matching) != 1:
                raise RuntimeError(
                    f"Expected one GHEFT row for {bucket_label}/{composition}, "
                    f"found {len(matching)}."
                )
            row = matching.iloc[0]
            metric_specs = (
                ("gain_g_over_d_pct", "gain_g_over_d_significant"),
                ("delta_m_g_over_n_pct", "delta_m_g_over_n_significant"),
                ("delta_u_g_over_n_pct", "delta_u_g_over_n_significant"),
            )
            for value_column, star_column in metric_specs:
                star = r"^{*}" if bool(row[star_column]) else ""
                cells.append(f"${float(row[value_column]):.2f}{star}$")
        lines.append(" & ".join(cells) + r" \\")
    lines.extend(
        [
            r"\hline",
            r"\end{tabular}",
            r"}",
            r"\vspace{1mm}",
            (
                r"\parbox{\columnwidth}{\raggedright\scriptsize\textit{Note:} "
                r"Values are per-seed means (\%). Positive Gain favors GHEFT over "
                r"DHEFT; positive $\Delta M_{G/N}$ denotes a makespan increase, whereas "
                r"positive $\Delta U_{G/N}$ denotes fewer used vCPUs, both relative to "
                r"NHEFT. $^{*}$Significant paired Wilcoxon test after Holm correction "
                r"($\alpha=0.05$).}"
            ),
            r"\end{table}",
        ]
    )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_gheft_success_rates_latex(detail, path):
    """Write the composition-grouped GHEFT target-achievement table."""
    labels = {
        "x": r"Balanced ($\mathrm{CCR}\approx\mathrm{IDR}$)",
        "y": r"Image-dominant ($\mathrm{CCR}<\mathrm{IDR}$)",
        "z": r"Data-dominant ($\mathrm{CCR}>\mathrm{IDR}$)",
    }
    lines = [
        "% Auto-generated by experiments/five/analyze_results.py",
        r"\begin{table}[t]",
        r"\centering",
        r"\caption{Strict paired-seed target-achievement rates for GHEFT.}",
        r"\label{tab:gheft_success_rates}",
        r"\scriptsize",
        r"\setlength{\tabcolsep}{2.5pt}",
        r"\begin{tabular}{lrrrr}",
        r"\hline",
        r"NCCR bucket & $n$ & Retain & Save & Joint \\ ",
        r"\hline",
    ]
    for composition in ("x", "y", "z"):
        subset = detail[detail["scenario"].str.endswith(composition)].copy()
        if subset.empty:
            continue
        subset["bucket_index"] = subset["nccr_bucket"].map(
            {label: index for index, (label, _, _) in enumerate(BUCKET_SPECS, start=1)}
        )
        subset = subset.sort_values("bucket_index")
        lines.append(rf"\multicolumn{{5}}{{l}}{{\textit{{{labels[composition]}}}}} \\")
        for _, row in subset.iterrows():
            lines.append(
                "{} & {} & {:.1f} & {:.1f} & {:.1f} \\\\".format(
                    row["nccr_bucket"],
                    int(row["paired_n"]),
                    float(row["performance_retention_rate_pct"]),
                    float(row["resource_saving_rate_pct"]),
                    float(row["joint_success_rate_pct"]),
                )
            )
        lines.append(r"\hline")
    lines.extend(
        [
            r"\end{tabular}",
            r"\vspace{1mm}",
            (
                r"\parbox{\columnwidth}{\scriptsize All entries except $n$ are "
                r"percentages. Retain: $M_G<M_D$; Save: $U_G<U_N$; Joint: "
                r"both strict inequalities hold for the same seed. Ties are not successes.}"
            ),
            r"\end{table}",
        ]
    )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def build_nheft_statistical_outputs(scenario_df, statistical_df, output_dir):
    rows = []
    stats = statistical_df[statistical_df["comparison"].eq("NHEFT_vs_DHEFT_makespan")].copy()
    for _, scenario in scenario_df[scenario_df["data_status"].eq("ok")].sort_values(["bucket_index", "composition"]).iterrows():
        match = stats[stats["scenario"].eq(scenario["scenario"])]
        stat = match.iloc[0] if not match.empty else pd.Series(dtype=object)
        rows.append(
            {
                "scenario": scenario["scenario"],
                "nccr_bucket": scenario["bucket_label"],
                "composition": scenario["composition_label"],
                "paired_n": int(scenario["valid_rows"]),
                "gain_mean_pct": scenario.get("nheft_gain_over_dheft_pct_mean", np.nan),
                "gain_sd_pct": scenario.get("nheft_gain_over_dheft_pct_sd", np.nan),
                "gain_ci95_low_pct": scenario.get("nheft_gain_over_dheft_pct_ci95_low", np.nan),
                "gain_ci95_high_pct": scenario.get("nheft_gain_over_dheft_pct_ci95_high", np.nan),
                "win_rate_pct": scenario.get("nheft_win_rate_pct", np.nan),
                "wilcoxon_statistic": stat.get("statistic", np.nan),
                "p_raw": stat.get("p_raw", np.nan),
                "p_holm": stat.get("p_holm", np.nan),
            }
        )
    detail = pd.DataFrame(rows)
    detail.to_csv(output_dir / "nheft_vs_dheft_statistical_summary.csv", index=False)
    write_markdown(
        detail,
        output_dir / "nheft_vs_dheft_statistical_report.md",
        "NHEFT vs DHEFT Statistical Summary",
        note="Gain is the mean of paired per-seed gains. Confidence intervals use the existing scenario-level calculation; Wilcoxon p-values are Holm-adjusted within each comparison family.",
    )

    table_rows = []
    for index, (label, _, _) in enumerate(BUCKET_SPECS, start=1):
        row = {"NCCR bucket": label}
        for composition, prefix in (("x", "Balanced"), ("y", "Image-dominant"), ("z", "Data-dominant")):
            item = detail[(detail["nccr_bucket"] == label) & detail["scenario"].str.endswith(composition)]
            values = item.iloc[0] if not item.empty else pd.Series(dtype=object)
            row[f"{prefix} Gain +/- SD"] = (
                f"{format_percent(values.get('gain_mean_pct'))} +/- {format_percent(values.get('gain_sd_pct'))}"
                if not item.empty else ""
            )
            row[f"{prefix} 95% CI"] = (
                f"[{format_percent(values.get('gain_ci95_low_pct'))}, {format_percent(values.get('gain_ci95_high_pct'))}]"
                if not item.empty else ""
            )
        table_rows.append(row)
    table = pd.DataFrame(table_rows)
    table.to_csv(output_dir / "nheft_vs_dheft_statistical_table.csv", index=False)
    write_markdown(table, output_dir / "nheft_vs_dheft_statistical_table.md", "Paired NHEFT Makespan Gain Table")
    write_nheft_statistical_latex(
        detail,
        output_dir / "nheft_vs_dheft_statistical_table.tex",
    )
    return detail, table


def build_gheft_outputs(scenario_df, statistical_df, output_dir):
    significance = {}
    if not statistical_df.empty:
        for _, stat in statistical_df.iterrows():
            significance[(stat["scenario"], stat["comparison"])] = (
                np.isfinite(stat.get("p_holm", np.nan))
                and float(stat["p_holm"]) < 0.05
            )
    rows = []
    for _, scenario in scenario_df[scenario_df["data_status"].eq("ok")].sort_values(["bucket_index", "composition"]).iterrows():
        rows.append(
            {
                "scenario": scenario["scenario"],
                "nccr_bucket": scenario["bucket_label"],
                "composition": scenario["composition_label"],
                "paired_n": int(scenario["valid_rows"]),
                "gain_g_over_d_pct": scenario.get("gheft_gain_over_dheft_pct_mean", np.nan),
                "delta_m_g_over_n_pct": scenario.get("gheft_change_vs_nheft_pct_mean", np.nan),
                "delta_u_g_over_n_pct": scenario.get("gheft_vcpu_reduction_vs_nheft_pct_mean", np.nan),
                "joint_success_rate_pct": scenario.get("gheft_joint_success_rate_pct", np.nan),
                "gain_g_over_d_significant": significance.get(
                    (scenario["scenario"], "GHEFT_vs_DHEFT_makespan"), False
                ),
                "delta_m_g_over_n_significant": significance.get(
                    (scenario["scenario"], "GHEFT_vs_NHEFT_makespan"), False
                ),
                "delta_u_g_over_n_significant": significance.get(
                    (scenario["scenario"], "GHEFT_vs_NHEFT_vcpus"), False
                ),
            }
        )
    detail = pd.DataFrame(rows)
    detail.to_csv(output_dir / "e3xyz_gheft_metrics_table.csv", index=False)
    write_markdown(
        detail,
        output_dir / "e3xyz_gheft_metrics_table.md",
        "GHEFT Metrics by NCCR Bucket and Composition",
        note="Gain is relative to DHEFT. Delta M and Delta U are relative to NHEFT. All values are means over paired valid rows.",
    )
    table_rows = []
    for label, _, _ in BUCKET_SPECS:
        row = {"NCCR bucket": label}
        for composition, prefix in (("x", "Balanced"), ("y", "Image-dominant"), ("z", "Data-dominant")):
            item = detail[(detail["nccr_bucket"] == label) & detail["scenario"].str.endswith(composition)]
            values = item.iloc[0] if not item.empty else pd.Series(dtype=object)
            row[f"{prefix} Gain"] = format_percent(values.get("gain_g_over_d_pct"))
            row[f"{prefix} Delta M"] = format_percent(values.get("delta_m_g_over_n_pct"))
            row[f"{prefix} Delta U"] = format_percent(values.get("delta_u_g_over_n_pct"))
        table_rows.append(row)
    table = pd.DataFrame(table_rows)
    table.to_csv(output_dir / "e3xyz_gheft_metrics_summary.csv", index=False)
    write_markdown(table, output_dir / "e3xyz_gheft_metrics_summary.md", "GHEFT Metrics Summary")
    write_gheft_metrics_latex(
        detail,
        output_dir / "e3xyz_gheft_metrics_table.tex",
    )
    return detail, table


def build_gheft_success_outputs(scenario_df, output_dir):
    rows = []
    for _, scenario in scenario_df[scenario_df["data_status"].eq("ok")].sort_values(["bucket_index", "composition"]).iterrows():
        total = int(scenario["valid_rows"])
        metrics = [
            ("performance_retention", int(scenario.get("gheft_win_vs_dheft_count", 0)), "gheft_win_vs_dheft_count"),
            ("resource_saving", int(scenario.get("gheft_resource_saving_count", 0)), "gheft_resource_saving_count"),
            ("joint_success", int(scenario.get("gheft_joint_success_count", 0)), "gheft_joint_success_count"),
        ]
        row = {"scenario": scenario["scenario"], "nccr_bucket": scenario["bucket_label"], "composition": scenario["composition_label"], "paired_n": total}
        for name, count, _ in metrics:
            low, high = binomial_ci(count, total)
            row[f"{name}_count"] = count
            row[f"{name}_rate_pct"] = count / total * 100.0 if total else np.nan
            row[f"{name}_ci95_low_pct"] = low
            row[f"{name}_ci95_high_pct"] = high
        rows.append(row)
    detail = pd.DataFrame(rows)
    detail.to_csv(output_dir / "e3xyz_gheft_success_rates.csv", index=False)
    write_markdown(
        detail,
        output_dir / "e3xyz_gheft_success_rates.md",
        "GHEFT Success Rates",
        note="Performance retention means GHEFT has a shorter makespan than DHEFT; resource saving means fewer vCPUs than NHEFT; joint success requires both. Intervals are Wilson 95% binomial intervals.",
    )
    write_gheft_success_rates_latex(
        detail,
        output_dir / "e3xyz_gheft_success_rates.tex",
    )
    return detail


def write_e3x_statistical_report(statistical_df, output_dir):
    if statistical_df.empty:
        return
    columns = ["comparison", "scenario", "bucket_label", "composition_label", "n", "nonzero_n", "statistic", "p_raw", "p_holm"]
    columns = [column for column in columns if column in statistical_df.columns]
    write_markdown(
        statistical_df,
        output_dir / "e3xyz_statistical_report.md",
        "E3x-Compatible Statistical Report",
        columns,
        note="All comparisons are paired within the same five CSV row. Holm correction is applied within each comparison family.",
    )


def write_e3x_seed_coverage_report(scenario_df, output_dir):
    columns = ["scenario", "bucket_label", "composition_label", "raw_rows", "ok_rows", "valid_rows", "data_status"]
    columns = [column for column in columns if column in scenario_df.columns]
    write_markdown(
        scenario_df,
        output_dir / "e3x_seed_coverage_report.md",
        "E3x-Compatible Seed Coverage",
        columns,
        note="Each five CSV row contains the three paired algorithms. Valid rows are selected using the measured NCCR bucket and CCR/IDR composition filters.",
    )


def write_e3x_compatible_csv_outputs(scenario_df, bucket_df, statistical_df, output_dir):
    """Write the two main CSV names used by the e3x analysis pipeline.

    The five runner stores all three algorithms in one paired row, so its
    scenario summary is the natural equivalent of e3x's wide statistical
    summary.  The original five CSV files remain available as well.
    """
    bucket_df.to_csv(output_dir / "e3x_bucket_summary.csv", index=False)

    compatible = scenario_df.copy()
    if not statistical_df.empty:
        stat_columns = ("n", "nonzero_n", "statistic", "p_raw", "p_holm")
        for comparison in sorted(statistical_df["comparison"].dropna().unique()):
            prefix = f"wilcoxon_{comparison.lower()}"
            subset = statistical_df[statistical_df["comparison"].eq(comparison)].set_index("scenario")
            for column in stat_columns:
                if column in subset.columns:
                    compatible[f"{prefix}_{column}"] = compatible["scenario"].map(subset[column])

    compatible.to_csv(output_dir / "e3xyz_statistical_summary.csv", index=False)


def main():
    args = parse_args()
    # Resolve the complete cohort first; never mix a partial run or simulator revisions.
    selected_runs = {}
    signatures = set()
    seed_sets = set()
    for spec in scenario_specs():
        name = spec["scenario"]
        path = find_latest_run_dir(FIVE_DIR / name, f"{name}_results.csv", args.allow_legacy_runs)
        if path is None:
            raise RuntimeError(f"No complete, versioned {TARGET_SEED_COUNT}-seed run for {name}; "
                               "finish the run first (use --allow-legacy-runs only for historical data)")
        manifest = json.loads((path / "run_manifest.json").read_text(encoding="utf-8"))
        signatures.add((manifest.get("data_revision"), manifest.get("classes_sha256"),
                        manifest.get("libraries_sha256")))
        seed_sets.add(tuple(manifest["seeds_used"]))
        actual = pd.read_csv(path / f"{name}_results.csv", usecols=["seed"])["seed"].tolist()
        if actual != manifest["seeds_used"]:
            raise ValueError(f"CSV seed sequence does not match manifest: {path}")
        selected_runs[name] = path
    if len(signatures) != 1 or len(seed_sets) != 1:
        raise RuntimeError("Selected scenarios mix simulator versions/dependencies or seed cohorts; select matching runs")
    scenario_rows = []
    statistical_rows = []
    missing_scenarios = []
    for spec in scenario_specs():
        raw_csv_name = f"{spec['scenario']}_results.csv"
        result_dir = selected_runs[spec["scenario"]]
        row, stats = summarize_scenario(spec, result_dir, result_dir / raw_csv_name)
        if row["valid_rows"] == 0:
            raise ValueError(f"No scenario-valid paired samples: {result_dir}")
        scenario_rows.append(row)
        if stats:
            statistical_rows.extend(stats)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_dir = Path(args.output_dir) if args.output_dir else FIVE_DIR / f"analysis_{timestamp}_{TARGET_SEED_COUNT}"
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "analysis_provenance.json").write_text(json.dumps({
        "selected_runs": {name: str(path) for name, path in selected_runs.items()},
        "simulator_signature": list(next(iter(signatures))),
        "legacy_allowed": args.allow_legacy_runs,
    }, indent=2) + "\n", encoding="utf-8")

    scenario_df = pd.DataFrame(scenario_rows)
    bucket_df = aggregate_bucket_means(scenario_df)
    statistical_df = pd.DataFrame(statistical_rows)
    if not statistical_df.empty:
        statistical_df["p_holm"] = np.nan
        for comparison, positions in statistical_df.groupby("comparison").groups.items():
            statistical_df.loc[positions, "p_holm"] = holm_adjust(
                statistical_df.loc[positions, "p_raw"].to_numpy()
            )

    scenario_df.to_csv(output_dir / "five_scenario_summary.csv", index=False)
    bucket_df.to_csv(output_dir / "five_bucket_summary.csv", index=False)
    statistical_df.to_csv(output_dir / "five_statistical_summary.csv", index=False)

    concise_columns = [
        "scenario",
        "bucket_label",
        "composition",
        "data_status",
        "raw_rows",
        "ok_rows",
        "valid_rows",
        "dheft_makespan_mean",
        "nheft_makespan_mean",
        "gheft_makespan_mean",
        "dheft_vcpus_mean",
        "nheft_vcpus_mean",
        "gheft_vcpus_mean",
        "nheft_gain_over_dheft_pct_mean",
        "nheft_win_rate_pct",
        "gheft_gain_over_dheft_pct_mean",
        "gheft_change_vs_nheft_pct_mean",
        "gheft_vcpu_reduction_vs_nheft_pct_mean",
        "gheft_joint_success_rate_pct",
    ]
    concise_columns = [column for column in concise_columns if column in scenario_df.columns]
    write_markdown(
        scenario_df,
        output_dir / "five_scenario_summary.md",
        "Experiments/Five Scenario Summary",
        concise_columns,
        "Each row is one NCCR bucket and communication composition. `valid_rows` are paired rows that satisfy the measured NCCR and CCR/IDR filters.",
    )
    write_markdown(
        bucket_df,
        output_dir / "five_bucket_summary.md",
        "Experiments/Five Bucket Summary",
        note="Each bucket value is the mean of the available scenario-level means for balanced, image-dominant, and data-dominant conditions.",
    )
    if not statistical_df.empty:
        write_markdown(
            statistical_df,
            output_dir / "five_statistical_summary.md",
            "Experiments/Five Paired Statistical Summary",
            note="Wilcoxon tests use paired valid rows. `p_holm` is adjusted within each comparison family across the 24 scenarios.",
        )

    valid_counts = scenario_df[
        ["scenario", "bucket_label", "composition", "raw_rows", "ok_rows", "valid_rows", "data_status"]
    ]
    write_markdown(
        valid_counts,
        output_dir / "five_valid_counts.md",
        "Experiments/Five Valid Row Counts",
        note="Raw rows are retained by the runner; valid rows are selected here using the measured communication conditions.",
    )

    if scenario_df["data_status"].eq("ok").any():
        plot_algorithm_lines(
            scenario_df,
            output_dir,
            "makespan",
            "Mean makespan",
            "makespan_comparison",
            f"DHEFT, NHEFT, and {ALGORITHM_LABELS['gheft']} makespan by communication composition",
        )
        plot_algorithm_lines(
            scenario_df,
            output_dir,
            "vcpus",
            "Mean used vCPUs",
            "vcpu_usage_comparison",
            f"DHEFT, NHEFT, and {ALGORITHM_LABELS['gheft']} resource usage by communication composition",
        )
        plot_nheft_rates(scenario_df, output_dir)
        plot_gheft_tradeoff(scenario_df, output_dir)

        # Keep the original five outputs above, and additionally expose the
        # same output families as experiments/four/e3x for paper preparation.
        save_e3x_overview_plots(bucket_df, output_dir)
        save_nheft_gain_win_rate_combined(scenario_df, output_dir)

    nheft_statistical_detail = None
    gheft_metric_detail = None
    gheft_success_detail = None
    if not statistical_df.empty:
        nheft_statistical_detail, _ = build_nheft_statistical_outputs(
            scenario_df, statistical_df, output_dir
        )
        gheft_metric_detail, _ = build_gheft_outputs(
            scenario_df, statistical_df, output_dir
        )
        gheft_success_detail = build_gheft_success_outputs(scenario_df, output_dir)
        write_e3x_statistical_report(statistical_df, output_dir)
        write_e3x_seed_coverage_report(scenario_df, output_dir)

    # Match the principal CSV names used by experiments/four/e3x while
    # retaining the original five-specific summaries above.
    write_e3x_compatible_csv_outputs(
        scenario_df, bucket_df, statistical_df, output_dir
    )

    manifest = {
        "experiment": "five",
        "target_seed_count": TARGET_SEED_COUNT,
        "scenario_count": len(scenario_specs()),
        "available_scenarios": int(scenario_df["data_status"].eq("ok").sum()),
        "missing_or_invalid_scenarios": missing_scenarios,
        "balanced_filter": f"relative CCR/IDR gap <= {BALANCED_RELATIVE_GAP_MAX_PERCENT:.2f}%",
        "dominant_filter": f"directional CCR/IDR gap >= {DOMINANT_RELATIVE_GAP_MIN_PERCENT:.2f}%",
        "raw_rows_are_not_filtered_by_runner": True,
        "output_files": sorted(path.name for path in output_dir.iterdir()),
    }
    (output_dir / "analysis_manifest.json").write_text(
        json.dumps(manifest, indent=2), encoding="utf-8"
    )

    print(f"Output directory: {output_dir}")
    print(f"Scenarios with usable data: {manifest['available_scenarios']}/24")
    if missing_scenarios:
        print("Missing or invalid scenarios:")
        for scenario in missing_scenarios:
            print(f"  - {scenario}")


if __name__ == "__main__":
    main()
