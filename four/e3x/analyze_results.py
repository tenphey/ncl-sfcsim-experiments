#!/usr/bin/env python3
"""Aggregate all E3X bucket results into cross-bucket overview figures.

This script combines the latest raw results of:

  baseline side: e01x, e02x, e03x, e04x, e05x, e06x, e07x, e08x
  GHEFT side:    e31x, e32x, e33x, e34x, e35x, e36x, e37x, e38x

Each bucket keeps the original x-condition filtering:

  NCCR bucket AND |CCR_data - IDR_image| <= abs_tol

Only paired seeds are used in the final aggregation.
A seed is counted only when:

  - the baseline side has a valid `baseline` row
  - the GHEFT side has a valid `irt_only` row
  - both rows satisfy the same bucket + x-condition

The output includes one full overview and two four-bucket split figures. Each
plot is written both as PNG (for preview) and PDF (for vector-quality paper
figures):

  - x axis: 8 NCCR buckets
  - left y axis: DHEFT / NHEFT / GHEFT mean makespan lines
  - right y axis: DHEFT / NHEFT / GHEFT mean used-vCPU bars

The split figures use the same filtered summary data as the full overview:

  - e3x_makespan_vcpu_overview-1.png: lower four NCCR buckets
  - e3x_makespan_vcpu_overview-2.png: upper four NCCR buckets

The same three-composition mean data also produce DHEFT/NHEFT-only variants:

  - e3xyz_mean_makespan_vcpu_overview-low-dheft-nheft.png
  - e3xyz_mean_makespan_vcpu_overview-high-dheft-nheft.png

The script also reads the matching y- and z-condition raw results, applies each
condition's original scenario filter, and averages the three condition-level
means for every bucket and algorithm. Two additional figures are written
directly under `experiments/four/e3x/`:

  - e3xyz_mean_makespan_vcpu_overview-low.png
  - e3xyz_mean_makespan_vcpu_overview-high.png

Statistical evidence is calculated from the paired per-seed observations before
any bucket or three-composition averaging. The analysis directory also contains:

  - e3xyz_statistical_summary.csv
  - e3xyz_statistical_report.md
  - nheft_vs_dheft_statistical_summary.csv
  - nheft_vs_dheft_statistical_report.md
  - nheft_vs_dheft_statistical_table.tex
  - nheft_gain_win_rate_combined.png
  - e3xyz_gheft_metrics_table.csv
  - e3xyz_gheft_metrics_table.md
  - e3xyz_gheft_metrics_table.tex
  - e3xyz_gheft_success_rates.csv
  - e3xyz_gheft_success_rates.md
  - e3xyz_gheft_success_rates.tex

The NHEFT statistical outputs use the same original 500-seed E3X/E4X/E5X
per-seed files that produced the paper's NHEFT gain/win table. The script checks
that the recomputed gain and win rate match that source table before reporting
standard deviations, bootstrap 95% confidence intervals, and paired Wilcoxon
tests. GHEFT statistics use the strict three-algorithm paired subset. Holm
correction is applied across the 24 scenarios within each comparison family.
The GHEFT table reports Gain_G/D, DeltaM_G/N, and DeltaU_G/N for every NCCR
bucket and communication composition.

The GHEFT success-rate table additionally reports three strict paired-seed
frequencies. Ties are not counted as successes:

  - performance retention: GHEFT makespan < DHEFT makespan
  - resource saving: GHEFT used vCPUs < NHEFT used vCPUs
  - joint success: both conditions hold for the same seed

Set `TARGET_SEED_COUNT` below to select the newest run whose directory name
ends with that seed count, for example `run_..._2000`.

Usage from the simulator repository root:

  experiments/.venv/bin/python experiments/four/e3x/analyze_results.py
"""

import argparse
import json
import os
import zlib
from datetime import datetime


THIS_DIR = os.path.dirname(os.path.abspath(__file__))
FOUR_DIR = os.path.dirname(THIS_DIR)
EXPERIMENTS_DIR = os.path.dirname(FOUR_DIR)
THREE_DIR = os.path.join(EXPERIMENTS_DIR, "three")
CACHE_DIR = os.path.join(THIS_DIR, ".plot_cache")
os.makedirs(CACHE_DIR, exist_ok=True)
os.environ.setdefault("MPLCONFIGDIR", CACHE_DIR)
os.environ.setdefault("XDG_CACHE_HOME", CACHE_DIR)

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.lines import Line2D
from scipy.stats import wilcoxon


WASEDA_RED = "#8E1728"
GREEN = "#0B7F5B"
GREY = "#BDBDBD"
DARK = "#172A33"
PLOT_DPI = 300

# DHEFT/NHEFT/GHEFT makespan-vCPU overview plots for paper figures.
# Keep the bucket tick labels, but hide redundant in-figure titles by default.
FIGSIZE_OVERVIEW = (13.8, 4.8)
SHOW_OVERVIEW_X_AXIS_LABEL = False
SHOW_OVERVIEW_TITLE = False
OVERVIEW_AXIS_LABEL_FONTSIZE = 22
OVERVIEW_XTICK_FONTSIZE = 20
OVERVIEW_YTICK_FONTSIZE = 20
OVERVIEW_LEGEND_FONTSIZE = 16
# Keep legend text as large as the axis-description text for paper figures.
# OVERVIEW_LEGEND_FONTSIZE = OVERVIEW_AXIS_LABEL_FONTSIZE
OVERVIEW_TITLE_FONTSIZE = 22
OVERVIEW_LINE_ANNOTATION_FONTSIZE = 14
OVERVIEW_MARKER_SIZE = 8
OVERVIEW_LINE_WIDTH = 2.8
BALANCED_ABS_TOL = float(os.getenv("E3X_ABS_TOL", "0.02"))
Y_MIN_REL_GAP_PCT = float(os.getenv("E3Y_MIN_REL_GAP_PCT", "20.0"))
Z_MIN_REL_GAP_PCT = float(os.getenv("E3Z_MIN_REL_GAP_PCT", "20.0"))

# Select the newest run_*_<seed_count> result for every baseline/GHEFT bucket.
# Change only this value when switching between 500, 2000, or a future count.
TARGET_SEED_COUNT = 500

# 是否显示 NHEFT gain/win 合并图底部的横轴名称 "NCCR bucket"。
# bucket 区间刻度仍然保留；论文图已有 caption，因此默认关闭以节省高度。
SHOW_NHEFT_GAIN_WIN_X_AXIS_LABEL = False

# NHEFT gain/win 合并图的论文出图尺寸和字号。
# 第二个值控制 PNG 的物理高度；减小它会让整张图变矮，
# 不会改变纵轴的数值范围。取值参考 experiments/three/analyze_e345x.py。
NHEFT_GAIN_WIN_FIGSIZE = (18, 8.5)
NHEFT_GAIN_WIN_AXIS_LABEL_FONTSIZE = 30
NHEFT_GAIN_WIN_XTICK_FONTSIZE = 30
NHEFT_GAIN_WIN_YTICK_FONTSIZE = 30
NHEFT_GAIN_WIN_LEGEND_FONTSIZE = 25
NHEFT_GAIN_WIN_LEGEND_TITLE_FONTSIZE = 26
# 合并图中两个图例框的纵向位置。数值越小，图例越向下移动。
# 这里分别控制 Win rate 和 Gain rate 的图例，便于单独微调。
NHEFT_GAIN_WIN_WIN_LEGEND_Y = 0.98
NHEFT_GAIN_WIN_GAIN_LEGEND_Y = 0.46
NHEFT_GAIN_WIN_MARKER_SIZE = 9
NHEFT_GAIN_WIN_LINE_WIDTH = 2.8

# Statistical settings. Tests always use paired per-seed rows after the same
# NCCR and CCR/IDR filters as the plots; they are never run on bucket means.
STAT_ALPHA = 0.05
BOOTSTRAP_CONFIDENCE = 0.95
BOOTSTRAP_RESAMPLES = 10000
BOOTSTRAP_RANDOM_SEED = 20260827

# Authoritative 500-seed NHEFT summary used by the paper's gain/win table.
# Its `latest_run_rel` column points to the exact per-seed source run for each
# of the 24 NCCR/composition scenarios.
NHEFT_SOURCE_SUMMARY = os.path.join(
    THREE_DIR,
    "e3x_e4x_e5x",
    "20260710_014610",
    "e345x_latest_summary.csv",
)

BASE_VARIANT = "baseline"
GATE_VARIANT = "irt_only"

BUCKET_SPECS = [
    ("(0.10, 0.18]", 0.10, 0.18, "e01x", "e31x"),
    ("(0.18, 0.32]", 0.18, 0.32, "e02x", "e32x"),
    ("(0.32, 0.56]", 0.32, 0.56, "e03x", "e33x"),
    ("(0.56, 1.00]", 0.56, 1.00, "e04x", "e34x"),
    ("(1.00, 1.78]", 1.00, 1.78, "e05x", "e35x"),
    ("(1.78, 3.16]", 1.78, 3.16, "e06x", "e36x"),
    ("(3.16, 5.62]", 3.16, 5.62, "e07x", "e37x"),
    ("(5.62, 10.00]", 5.62, 10.00, "e08x", "e38x"),
]

COMPOSITION_LABELS = {
    "x": "Balanced (CCR ~= IDR)",
    "y": "Image-dominant (CCR < IDR)",
    "z": "Data-dominant (CCR > IDR)",
}

MEAN_METRIC_COLUMNS = [
    "dheft_makespan_mean",
    "dheft_vcpus_mean",
    "nheft_makespan_mean",
    "nheft_vcpus_mean",
    "gheft_makespan_mean",
    "gheft_vcpus_mean",
]

GHEFT_WILCOXON_SPECS = [
    {
        "key": "gheft_vs_dheft_makespan",
        "title": "GHEFT vs DHEFT makespan",
        "effect_prefix": "gheft_gain_over_dheft_pct",
        "effect_label": "GHEFT gain over DHEFT (%)",
        "effect_interpretation": "Positive values mean that GHEFT is faster.",
    },
    {
        "key": "gheft_vs_nheft_makespan",
        "title": "GHEFT vs NHEFT makespan",
        "effect_prefix": "gate_makespan_change_vs_nheft_pct",
        "effect_label": "GHEFT makespan change from NHEFT (%)",
        "effect_interpretation": "Positive values mean that GHEFT is slower.",
    },
    {
        "key": "gheft_vs_nheft_vcpus",
        "title": "GHEFT vs NHEFT used vCPUs",
        "effect_prefix": "gate_vcpu_reduction_vs_nheft_pct",
        "effect_label": "GHEFT vCPU reduction from NHEFT (%)",
        "effect_interpretation": "Positive values mean that GHEFT uses fewer vCPUs.",
    },
]

NHEFT_FAMILY_TO_COMPOSITION = {
    "e3x": "x",
    "e4x": "y",
    "e5x": "z",
}


def parse_args():
    parser = argparse.ArgumentParser(
        description="Aggregate baseline e01x-e08x and GHEFT e31x-e38x into full and split x-condition overview figures."
    )
    parser.add_argument(
        "--output-dir",
        help="Optional output directory. Default: experiments/four/e3x/analysis_<timestamp>",
    )
    return parser.parse_args()


def relpath(path, base=FOUR_DIR):
    try:
        return os.path.relpath(path, base)
    except Exception:
        return path


def finite_max(values, default=1.0):
    arr = np.asarray(values, dtype=float)
    arr = arr[np.isfinite(arr)]
    if arr.size == 0:
        return default
    return float(np.max(arr))


def safe_percent(numerator, denominator):
    denominator = np.asarray(denominator, dtype=float)
    numerator = np.asarray(numerator, dtype=float)
    with np.errstate(divide="ignore", invalid="ignore"):
        result = numerator / denominator * 100.0
    return np.where(np.isfinite(result), result, np.nan)


def safe_ratio_pct(part, whole):
    try:
        part_val = float(part)
        whole_val = float(whole)
    except (TypeError, ValueError):
        return np.nan
    if not np.isfinite(part_val) or not np.isfinite(whole_val) or whole_val == 0.0:
        return np.nan
    return part_val / whole_val * 100.0


def finite_values(values):
    arr = np.asarray(values, dtype=float)
    return arr[np.isfinite(arr)]


def deterministic_seed(seed_key):
    key_bytes = str(seed_key).encode("utf-8")
    return BOOTSTRAP_RANDOM_SEED + (zlib.crc32(key_bytes) & 0xFFFFFFFF)


def bootstrap_mean_ci(values, seed_key):
    arr = finite_values(values)
    if arr.size == 0:
        return np.nan, np.nan
    if arr.size == 1 or np.allclose(arr, arr[0]):
        value = float(arr.mean())
        return value, value

    rng = np.random.default_rng(deterministic_seed(seed_key))
    bootstrap_means = []
    remaining = BOOTSTRAP_RESAMPLES
    batch_size = 1000
    while remaining > 0:
        current_batch = min(batch_size, remaining)
        indices = rng.integers(0, arr.size, size=(current_batch, arr.size))
        bootstrap_means.append(arr[indices].mean(axis=1))
        remaining -= current_batch

    bootstrap_means = np.concatenate(bootstrap_means)
    tail = (1.0 - BOOTSTRAP_CONFIDENCE) / 2.0
    low, high = np.quantile(bootstrap_means, [tail, 1.0 - tail])
    return float(low), float(high)


def summarize_distribution(prefix, values, seed_key):
    arr = finite_values(values)
    if arr.size == 0:
        return {
            f"{prefix}_n": 0,
            f"{prefix}_mean": np.nan,
            f"{prefix}_sd": np.nan,
            f"{prefix}_median": np.nan,
            f"{prefix}_q1": np.nan,
            f"{prefix}_q3": np.nan,
            f"{prefix}_ci95_low": np.nan,
            f"{prefix}_ci95_high": np.nan,
        }

    ci_low, ci_high = bootstrap_mean_ci(arr, seed_key)
    return {
        f"{prefix}_n": int(arr.size),
        f"{prefix}_mean": float(arr.mean()),
        f"{prefix}_sd": float(arr.std(ddof=1)) if arr.size > 1 else np.nan,
        f"{prefix}_median": float(np.median(arr)),
        f"{prefix}_q1": float(np.quantile(arr, 0.25)),
        f"{prefix}_q3": float(np.quantile(arr, 0.75)),
        f"{prefix}_ci95_low": ci_low,
        f"{prefix}_ci95_high": ci_high,
    }


def summarize_binary_rate(prefix, success_mask, seed_key):
    """Summarize a strict same-seed success condition as a percentage."""
    mask = np.asarray(success_mask, dtype=bool)
    total = int(mask.size)
    success_count = int(mask.sum())
    if total == 0:
        return {
            f"{prefix}_n": 0,
            f"{prefix}_count": 0,
            f"{prefix}_rate_pct": np.nan,
            f"{prefix}_ci95_low": np.nan,
            f"{prefix}_ci95_high": np.nan,
        }

    rate_values = mask.astype(float) * 100.0
    ci_low, ci_high = bootstrap_mean_ci(rate_values, seed_key)
    return {
        f"{prefix}_n": total,
        f"{prefix}_count": success_count,
        f"{prefix}_rate_pct": float(rate_values.mean()),
        f"{prefix}_ci95_low": ci_low,
        f"{prefix}_ci95_high": ci_high,
    }


def summarize_paired_wilcoxon(prefix, left_values, right_values):
    left = np.asarray(left_values, dtype=float)
    right = np.asarray(right_values, dtype=float)
    finite_mask = np.isfinite(left) & np.isfinite(right)
    left = left[finite_mask]
    right = right[finite_mask]
    differences = left - right

    if differences.size == 0:
        return {
            f"wilcoxon_{prefix}_n": 0,
            f"wilcoxon_{prefix}_nonzero_n": 0,
            f"wilcoxon_{prefix}_positive_n": 0,
            f"wilcoxon_{prefix}_negative_n": 0,
            f"wilcoxon_{prefix}_zero_n": 0,
            f"wilcoxon_{prefix}_mean_difference": np.nan,
            f"wilcoxon_{prefix}_median_difference": np.nan,
            f"wilcoxon_{prefix}_statistic": np.nan,
            f"wilcoxon_{prefix}_p_raw": np.nan,
        }

    zero_mask = np.isclose(differences, 0.0, rtol=1e-12, atol=1e-12)
    nonzero_n = int((~zero_mask).sum())
    if nonzero_n == 0:
        statistic = 0.0
        p_value = 1.0
    else:
        result = wilcoxon(
            left,
            right,
            zero_method="wilcox",
            correction=False,
            alternative="two-sided",
            method="auto",
        )
        statistic = float(result.statistic)
        p_value = float(result.pvalue)

    return {
        f"wilcoxon_{prefix}_n": int(differences.size),
        f"wilcoxon_{prefix}_nonzero_n": nonzero_n,
        f"wilcoxon_{prefix}_positive_n": int((differences > 0.0).sum()),
        f"wilcoxon_{prefix}_negative_n": int((differences < 0.0).sum()),
        f"wilcoxon_{prefix}_zero_n": int(zero_mask.sum()),
        f"wilcoxon_{prefix}_mean_difference": float(differences.mean()),
        f"wilcoxon_{prefix}_median_difference": float(np.median(differences)),
        f"wilcoxon_{prefix}_statistic": statistic,
        f"wilcoxon_{prefix}_p_raw": p_value,
    }


def holm_adjust(p_values):
    p_values = np.asarray(p_values, dtype=float)
    adjusted = np.full(p_values.shape, np.nan, dtype=float)
    valid_positions = np.flatnonzero(np.isfinite(p_values))
    if valid_positions.size == 0:
        return adjusted

    valid_p = p_values[valid_positions]
    order = np.argsort(valid_p)
    sorted_p = valid_p[order]
    multiplier = valid_p.size - np.arange(valid_p.size)
    sorted_adjusted = np.maximum.accumulate(sorted_p * multiplier)
    sorted_adjusted = np.minimum(sorted_adjusted, 1.0)

    restored = np.empty_like(sorted_adjusted)
    restored[order] = sorted_adjusted
    adjusted[valid_positions] = restored
    return adjusted


def calc_relative_gap_pct(a, b):
    if pd.isna(a) or pd.isna(b):
        return np.nan
    avg = (a + b) / 2.0
    if avg == 0:
        return np.nan
    return abs(a - b) / avg * 100.0


def find_latest_run_dir(bucket_dir, raw_csv_name, target_seed_count):
    candidates = []
    if not os.path.isdir(bucket_dir):
        return None

    for name in os.listdir(bucket_dir):
        try:
            run_seed_count = int(name.rsplit("_", 1)[-1])
        except (TypeError, ValueError):
            continue

        path = os.path.join(bucket_dir, name)
        if (
            os.path.isdir(path)
            and name.startswith("run_")
            and run_seed_count == target_seed_count
            and os.path.exists(os.path.join(path, raw_csv_name))
        ):
            candidates.append(path)

    if not candidates:
        return None

    candidates.sort(key=lambda p: os.path.getmtime(p), reverse=True)
    return candidates[0]


def unique_seed_count(df):
    if "seed" not in df.columns or df.empty:
        return 0
    seeds = pd.to_numeric(df["seed"], errors="coerce").dropna()
    if seeds.empty:
        return 0
    return int(seeds.astype(int).nunique())


def read_manifest(result_dir):
    path = os.path.join(result_dir, "run_manifest.json")
    if not os.path.exists(path):
        return {}
    with open(path, encoding="utf-8") as source:
        return json.load(source)


def load_raw_csv(result_dir, raw_csv_name):
    csv_path = os.path.join(result_dir, raw_csv_name)
    if not os.path.exists(csv_path):
        raise FileNotFoundError(f"CSV not found: {csv_path}")

    df = pd.read_csv(csv_path)
    if df.empty:
        raise RuntimeError(f"CSV is empty: {csv_path}")

    numeric_cols = [
        "seed",
        "ccr_data",
        "idr_image",
        "nccr_total",
        "heft_makespan",
        "heft_vcpus",
        "dheft_makespan",
        "dheft_vcpus",
        "nheft_makespan",
        "nheft_vcpus",
        "time_sec",
        "configured_tolerance",
        "configured_comp_advantage",
        "configured_drt_advantage",
        "configured_irt_advantage",
    ]
    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    if "variant" in df.columns:
        df["variant"] = df["variant"].astype(str)
    if "variant_display_label" in df.columns:
        df["variant_display_label"] = df["variant_display_label"].astype(str)
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
        "variant",
        "ccr_data",
        "idr_image",
        "nccr_total",
        "nheft_makespan",
        "nheft_vcpus",
    ]
    missing = [col for col in required if col not in ok.columns]
    if missing:
        raise RuntimeError(f"Missing required columns: {missing}")

    ok = ok.dropna(subset=[col for col in required if col != "variant"]).copy()
    if ok.empty:
        raise RuntimeError("No ok rows have complete core metrics")
    return ok


def filter_bucket_rows(ok, lower, upper, composition_key="x"):
    scenario_ok = ok.dropna(subset=["ccr_data", "idr_image", "nccr_total"]).copy()
    if scenario_ok.empty:
        raise RuntimeError("No ok rows have complete CCR/IDR/NCCR metrics")

    scenario_ok["ccr_idr_abs_diff"] = (
        scenario_ok["ccr_data"] - scenario_ok["idr_image"]
    ).abs()
    scenario_ok["ccr_idr_rel_gap_pct"] = [
        calc_relative_gap_pct(a, b)
        for a, b in zip(scenario_ok["ccr_data"], scenario_ok["idr_image"])
    ]

    bucket_match = (scenario_ok["nccr_total"] > lower) & (
        scenario_ok["nccr_total"] <= upper
    )
    if composition_key == "x":
        composition_match = scenario_ok["ccr_idr_abs_diff"] <= BALANCED_ABS_TOL
        rule_text = f"|CCR_data - IDR_image| <= {BALANCED_ABS_TOL:.4f}"
    elif composition_key == "y":
        composition_match = (
            (scenario_ok["ccr_data"] < scenario_ok["idr_image"])
            & (scenario_ok["ccr_idr_rel_gap_pct"] >= Y_MIN_REL_GAP_PCT)
        )
        rule_text = (
            "CCR_data < IDR_image AND relative CCR/IDR gap "
            f">= {Y_MIN_REL_GAP_PCT:.2f}%"
        )
    elif composition_key == "z":
        composition_match = (
            (scenario_ok["ccr_data"] > scenario_ok["idr_image"])
            & (scenario_ok["ccr_idr_rel_gap_pct"] >= Z_MIN_REL_GAP_PCT)
        )
        rule_text = (
            "CCR_data > IDR_image AND relative CCR/IDR gap "
            f">= {Z_MIN_REL_GAP_PCT:.2f}%"
        )
    else:
        raise ValueError(f"Unknown communication composition: {composition_key}")

    scenario_ok["scenario_match"] = bucket_match & composition_match
    filtered = scenario_ok[scenario_ok["scenario_match"]].copy()
    if filtered.empty:
        raise RuntimeError(
            "No ok rows satisfy the scenario rule: "
            f"{lower:.2f} < NCCR_total <= {upper:.2f} "
            f"AND {rule_text}"
        )
    validate_filtered_rows(filtered, lower, upper, composition_key)
    return filtered


def validate_filtered_rows(filtered, lower, upper, composition_key="x"):
    bad_nccr = filtered[
        ~((filtered["nccr_total"] > lower) & (filtered["nccr_total"] <= upper))
    ]
    if not bad_nccr.empty:
        raise RuntimeError(
            "Filtered rows contain out-of-bucket NCCR values, "
            "which should never happen in e3x aggregation"
        )

    if composition_key == "x":
        bad_rows = filtered[filtered["ccr_idr_abs_diff"] > BALANCED_ABS_TOL]
        message = (
            "Filtered rows violate the x-condition "
            f"|CCR_data - IDR_image| <= {BALANCED_ABS_TOL:.4f}"
        )
    elif composition_key == "y":
        bad_rows = filtered[
            (filtered["ccr_data"] >= filtered["idr_image"])
            | (filtered["ccr_idr_rel_gap_pct"] < Y_MIN_REL_GAP_PCT)
        ]
        message = (
            "Filtered rows violate the y-condition CCR_data < IDR_image "
            f"with relative gap >= {Y_MIN_REL_GAP_PCT:.2f}%"
        )
    elif composition_key == "z":
        bad_rows = filtered[
            (filtered["ccr_data"] <= filtered["idr_image"])
            | (filtered["ccr_idr_rel_gap_pct"] < Z_MIN_REL_GAP_PCT)
        ]
        message = (
            "Filtered rows violate the z-condition CCR_data > IDR_image "
            f"with relative gap >= {Z_MIN_REL_GAP_PCT:.2f}%"
        )
    else:
        raise ValueError(f"Unknown communication composition: {composition_key}")

    if not bad_rows.empty:
        raise RuntimeError(message)


def require_variant(df, expected_variant, label):
    observed = sorted(str(value) for value in df["variant"].dropna().unique())
    if expected_variant not in observed:
        raise RuntimeError(
            f"{label} does not contain required variant '{expected_variant}'. "
            f"Observed variants: {observed}"
        )


def filter_variant_rows(df, variant_label):
    variant_df = (
        df[df["variant"] == variant_label]
        .sort_values(["seed", "time_sec"])
        .drop_duplicates("seed")
        .copy()
    )
    if variant_df.empty:
        raise RuntimeError(f"No rows remain for variant '{variant_label}'")
    return variant_df


def build_bucket_summary(
    baseline_df,
    gate_df,
    bucket_label,
    baseline_key,
    gate_key,
    baseline_run_dir,
    gate_run_dir,
    baseline_manifest,
    gate_manifest,
    baseline_raw_df,
    gate_raw_df,
    baseline_ok_df,
    gate_ok_df,
    baseline_bucket_df,
    gate_bucket_df,
):
    baseline_variant_df = filter_variant_rows(baseline_bucket_df, BASE_VARIANT)
    gate_variant_df = filter_variant_rows(gate_bucket_df, GATE_VARIANT)

    paired_seeds = sorted(
        set(baseline_variant_df["seed"]) & set(gate_variant_df["seed"])
    )
    if not paired_seeds:
        raise RuntimeError(
            f"No paired seeds remain for {baseline_key} + {gate_key} after scenario filtering"
        )

    baseline = baseline_variant_df[
        baseline_variant_df["seed"].isin(paired_seeds)
    ].copy()
    gate = gate_variant_df[gate_variant_df["seed"].isin(paired_seeds)].copy()

    merged = baseline[
        ["seed", "dheft_makespan", "dheft_vcpus", "nheft_makespan", "nheft_vcpus"]
    ].merge(
        gate[["seed", "nheft_makespan", "nheft_vcpus"]],
        on="seed",
        suffixes=("_baseline", "_gate"),
        how="inner",
    )
    if merged.empty:
        raise RuntimeError("No paired rows remain after baseline/GHEFT merge")

    makespan_change_gate_vs_nheft = safe_percent(
        merged["nheft_makespan_gate"] - merged["nheft_makespan_baseline"],
        merged["nheft_makespan_baseline"],
    )
    vcpu_reduction_gate_vs_nheft = safe_percent(
        merged["nheft_vcpus_baseline"] - merged["nheft_vcpus_gate"],
        merged["nheft_vcpus_baseline"],
    )
    gain_gheft_over_dheft = safe_percent(
        merged["dheft_makespan"] - merged["nheft_makespan_gate"],
        merged["dheft_makespan"],
    )

    # These strict paired-seed conditions answer three different questions.
    # Equality is deliberately not counted as success.
    performance_retention = (
        merged["nheft_makespan_gate"] < merged["dheft_makespan"]
    )
    resource_saving = (
        merged["nheft_vcpus_gate"] < merged["nheft_vcpus_baseline"]
    )
    joint_success = performance_retention & resource_saving

    baseline_planned = baseline_manifest.get("num_seeds")
    gate_planned = gate_manifest.get("num_seeds")
    baseline_recorded = unique_seed_count(baseline_raw_df)
    gate_recorded = unique_seed_count(gate_raw_df)
    baseline_ok = unique_seed_count(baseline_ok_df)
    gate_ok = unique_seed_count(gate_ok_df)
    baseline_valid = unique_seed_count(baseline_bucket_df)
    gate_valid = unique_seed_count(gate_bucket_df)

    summary = {
        "bucket_label": bucket_label,
        "baseline_key": baseline_key,
        "gate_key": gate_key,
        "baseline_run_dir": baseline_run_dir,
        "gate_run_dir": gate_run_dir,
        "baseline_planned_seed_count": baseline_planned,
        "gate_planned_seed_count": gate_planned,
        "baseline_recorded_seed_count": baseline_recorded,
        "gate_recorded_seed_count": gate_recorded,
        "baseline_ok_seed_count": baseline_ok,
        "gate_ok_seed_count": gate_ok,
        "baseline_valid_seed_count": baseline_valid,
        "gate_valid_seed_count": gate_valid,
        "paired_seed_count": len(paired_seeds),
        "pair_rate_vs_baseline_valid_pct": safe_ratio_pct(len(paired_seeds), baseline_valid),
        "pair_rate_vs_gate_valid_pct": safe_ratio_pct(len(paired_seeds), gate_valid),
        "matched_nccr_min": float(
            min(baseline["nccr_total"].min(), gate["nccr_total"].min())
        ),
        "matched_nccr_max": float(
            max(baseline["nccr_total"].max(), gate["nccr_total"].max())
        ),
        "matched_abs_diff_max": float(
            max(baseline["ccr_idr_abs_diff"].max(), gate["ccr_idr_abs_diff"].max())
        ),
    }

    distributions = {
        "dheft_makespan": merged["dheft_makespan"],
        "dheft_vcpus": merged["dheft_vcpus"],
        "nheft_makespan": merged["nheft_makespan_baseline"],
        "nheft_vcpus": merged["nheft_vcpus_baseline"],
        "gheft_makespan": merged["nheft_makespan_gate"],
        "gheft_vcpus": merged["nheft_vcpus_gate"],
        "gate_makespan_change_vs_nheft_pct": makespan_change_gate_vs_nheft,
        "gate_vcpu_reduction_vs_nheft_pct": vcpu_reduction_gate_vs_nheft,
        "gheft_gain_over_dheft_pct": gain_gheft_over_dheft,
    }
    for prefix, values in distributions.items():
        summary.update(
            summarize_distribution(
                prefix=prefix,
                values=values,
                seed_key=f"{baseline_key}:{gate_key}:{prefix}",
            )
        )

    success_conditions = {
        "gheft_performance_retention": performance_retention,
        "gheft_resource_saving": resource_saving,
        "gheft_joint_success": joint_success,
    }
    for prefix, success_mask in success_conditions.items():
        summary.update(
            summarize_binary_rate(
                prefix=prefix,
                success_mask=success_mask,
                seed_key=f"{baseline_key}:{gate_key}:{prefix}",
            )
        )

    # Positive paired differences have the practical meaning documented below.
    # DHEFT - GHEFT > 0: GHEFT is faster.
    summary.update(
        summarize_paired_wilcoxon(
            "gheft_vs_dheft_makespan",
            merged["dheft_makespan"],
            merged["nheft_makespan_gate"],
        )
    )
    # GHEFT - NHEFT > 0: GHEFT is slower.
    summary.update(
        summarize_paired_wilcoxon(
            "gheft_vs_nheft_makespan",
            merged["nheft_makespan_gate"],
            merged["nheft_makespan_baseline"],
        )
    )
    # NHEFT - GHEFT > 0: GHEFT uses fewer vCPUs.
    summary.update(
        summarize_paired_wilcoxon(
            "gheft_vs_nheft_vcpus",
            merged["nheft_vcpus_baseline"],
            merged["nheft_vcpus_gate"],
        )
    )
    return summary


def bucket_specs_for_composition(composition_key):
    if composition_key not in COMPOSITION_LABELS:
        raise ValueError(f"Unknown communication composition: {composition_key}")

    specs = []
    for index, (bucket_label, lower, upper, _, _) in enumerate(BUCKET_SPECS, start=1):
        specs.append(
            (
                bucket_label,
                lower,
                upper,
                f"e0{index}{composition_key}",
                f"e3{index}{composition_key}",
            )
        )
    return specs


def collect_composition_summary(composition_key):
    summary_rows = []

    for bucket_label, lower, upper, baseline_key, gate_key in (
        bucket_specs_for_composition(composition_key)
    ):
        baseline_dir = os.path.join(FOUR_DIR, baseline_key)
        gate_dir = os.path.join(FOUR_DIR, gate_key)
        baseline_csv_name = f"{baseline_key}_results.csv"
        gate_csv_name = f"{gate_key}_results.csv"

        baseline_run_dir = find_latest_run_dir(
            baseline_dir, baseline_csv_name, TARGET_SEED_COUNT
        )
        gate_run_dir = find_latest_run_dir(
            gate_dir, gate_csv_name, TARGET_SEED_COUNT
        )
        if baseline_run_dir is None:
            raise RuntimeError(
                f"No run_*_{TARGET_SEED_COUNT} directory with {baseline_csv_name} "
                f"found under {baseline_dir}"
            )
        if gate_run_dir is None:
            raise RuntimeError(
                f"No run_*_{TARGET_SEED_COUNT} directory with {gate_csv_name} "
                f"found under {gate_dir}"
            )

        baseline_manifest = read_manifest(baseline_run_dir)
        gate_manifest = read_manifest(gate_run_dir)
        baseline_raw_df = load_raw_csv(baseline_run_dir, baseline_csv_name)
        gate_raw_df = load_raw_csv(gate_run_dir, gate_csv_name)
        baseline_ok_df = filter_ok_rows(baseline_raw_df)
        gate_ok_df = filter_ok_rows(gate_raw_df)
        baseline_bucket_df = filter_bucket_rows(
            baseline_ok_df, lower, upper, composition_key
        )
        gate_bucket_df = filter_bucket_rows(
            gate_ok_df, lower, upper, composition_key
        )

        require_variant(baseline_bucket_df, BASE_VARIANT, baseline_key)
        require_variant(gate_bucket_df, GATE_VARIANT, gate_key)

        row = build_bucket_summary(
            baseline_df=baseline_bucket_df,
            gate_df=gate_bucket_df,
            bucket_label=bucket_label,
            baseline_key=baseline_key,
            gate_key=gate_key,
            baseline_run_dir=baseline_run_dir,
            gate_run_dir=gate_run_dir,
            baseline_manifest=baseline_manifest,
            gate_manifest=gate_manifest,
            baseline_raw_df=baseline_raw_df,
            gate_raw_df=gate_raw_df,
            baseline_ok_df=baseline_ok_df,
            gate_ok_df=gate_ok_df,
            baseline_bucket_df=baseline_bucket_df,
            gate_bucket_df=gate_bucket_df,
        )
        row["composition_key"] = composition_key
        row["composition_label"] = COMPOSITION_LABELS[composition_key]
        summary_rows.append(row)

    return pd.DataFrame(summary_rows)


def build_three_composition_mean(composition_summaries):
    expected_keys = set(COMPOSITION_LABELS)
    if set(composition_summaries) != expected_keys:
        raise RuntimeError(
            "Three-composition mean requires x, y, and z summaries; observed "
            f"{sorted(composition_summaries)}"
        )

    bucket_order = {
        bucket_label: index
        for index, (bucket_label, _, _, _, _) in enumerate(BUCKET_SPECS)
    }
    combined = pd.concat(
        [composition_summaries[key] for key in ("x", "y", "z")],
        ignore_index=True,
    )
    combined["bucket_order"] = combined["bucket_label"].map(bucket_order)

    counts = combined.groupby("bucket_label")["composition_key"].nunique()
    incomplete = counts[counts != 3]
    if not incomplete.empty:
        raise RuntimeError(
            "Every NCCR bucket must contain all three communication compositions: "
            f"{incomplete.to_dict()}"
        )

    mean_df = (
        combined.groupby(["bucket_order", "bucket_label"], as_index=False)[
            MEAN_METRIC_COLUMNS
        ]
        .mean()
        .sort_values("bucket_order")
        .reset_index(drop=True)
    )
    mean_df["composition_count"] = 3

    for key in ("x", "y", "z"):
        paired = composition_summaries[key][
            ["bucket_label", "paired_seed_count"]
        ].rename(columns={"paired_seed_count": f"paired_seed_count_{key}"})
        mean_df = mean_df.merge(paired, on="bucket_label", how="left")

    return mean_df


def annotate_line_points(
    ax,
    x_values,
    y_values,
    color,
    fmt,
    xytext=(0, 8),
    xytexts=None,
    ha="center",
    has=None,
    va="bottom",
):
    for index, (x, y) in enumerate(zip(x_values, y_values)):
        point_xytext = xytext if xytexts is None else xytexts[index]
        point_ha = ha if has is None else has[index]
        ax.annotate(
            fmt.format(y),
            (x, y),
            textcoords="offset points",
            xytext=point_xytext,
            ha=point_ha,
            va=va,
            fontsize=OVERVIEW_LINE_ANNOTATION_FONTSIZE,
            color=color,
        )


def save_overview_plot(
    summary_df,
    output_dir,
    filename,
    title,
    wrap_bucket_labels=True,
    split_legend=False,
    include_gheft=True,
    dheft_annotation_xytext=(-8, 10),
    dheft_annotation_ha="right",
    gheft_annotation_xytext=(8, 10),
    gheft_annotation_xytexts=None,
    dheft_annotation_xytexts=None,
    gheft_annotation_ha="left",
    dheft_annotation_has=None,
    gheft_annotation_has=None,
):
    x = np.arange(len(summary_df))
    bucket_labels = summary_df["bucket_label"].tolist()

    makespan_dheft = summary_df["dheft_makespan_mean"].to_numpy(dtype=float)
    makespan_nheft = summary_df["nheft_makespan_mean"].to_numpy(dtype=float)
    makespan_gheft = summary_df["gheft_makespan_mean"].to_numpy(dtype=float)

    vcpu_dheft = summary_df["dheft_vcpus_mean"].to_numpy(dtype=float)
    vcpu_nheft = summary_df["nheft_vcpus_mean"].to_numpy(dtype=float)
    vcpu_gheft = summary_df["gheft_vcpus_mean"].to_numpy(dtype=float)

    fig, ax_m = plt.subplots(figsize=FIGSIZE_OVERVIEW)
    ax_v = ax_m.twinx()

    bar_width = 0.22
    if include_gheft:
        dheft_bar_x = x - bar_width
        nheft_bar_x = x
        gheft_bar_x = x + bar_width
    else:
        # Keep the two remaining bars centered around each bucket.
        dheft_bar_x = x - bar_width / 2
        nheft_bar_x = x + bar_width / 2

    bars_d = ax_v.bar(
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
    bars_n = ax_v.bar(
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
    bars_g = None
    if include_gheft:
        bars_g = ax_v.bar(
            gheft_bar_x,
            vcpu_gheft,
            width=bar_width,
            color=GREEN,
            edgecolor=GREEN,
            linewidth=0.8,
            alpha=0.25,
            label="GHEFT mean used vCPUs",
            zorder=1,
        )

    line_d = ax_m.plot(
        x,
        makespan_dheft,
        color=DARK,
        marker="o",
        markersize=OVERVIEW_MARKER_SIZE,
        linewidth=OVERVIEW_LINE_WIDTH,
        label="DHEFT mean makespan",
        zorder=4,
    )
    line_n = ax_m.plot(
        x,
        makespan_nheft,
        color=WASEDA_RED,
        marker="o",
        markersize=OVERVIEW_MARKER_SIZE,
        linewidth=OVERVIEW_LINE_WIDTH,
        label="NHEFT mean makespan",
        zorder=4,
    )
    line_g = None
    if include_gheft:
        line_g = ax_m.plot(
            x,
            makespan_gheft,
            color=GREEN,
            marker="o",
            markersize=OVERVIEW_MARKER_SIZE,
            linewidth=OVERVIEW_LINE_WIDTH,
            label="GHEFT mean makespan",
            zorder=4,
        )

    if SHOW_OVERVIEW_X_AXIS_LABEL:
        ax_m.set_xlabel(
            "NCCR bucket", fontsize=OVERVIEW_AXIS_LABEL_FONTSIZE
        )
    ax_m.set_ylabel(
        "Mean makespan",
        color=DARK,
        fontsize=OVERVIEW_AXIS_LABEL_FONTSIZE,
    )
    ax_v.set_ylabel(
        "Mean used vCPUs",
        color=DARK,
        fontsize=OVERVIEW_AXIS_LABEL_FONTSIZE,
    )
    ax_m.set_xticks(x)
    # 8 桶图的标签较密，默认拆成两行；4 桶的 low/high mean 图关闭拆行，
    # 让每个区间标签保持为完整的 (X, Y] 形式。
    display_bucket_labels = bucket_labels
    if wrap_bucket_labels:
        display_bucket_labels = [
            label.replace(", ", ",\n") for label in bucket_labels
        ]
    ax_m.set_xticklabels(
        display_bucket_labels,
        rotation=0,
        ha="center",
        fontsize=OVERVIEW_XTICK_FONTSIZE,
    )
    ax_m.tick_params(
        axis="y", labelcolor=DARK, labelsize=OVERVIEW_YTICK_FONTSIZE
    )
    ax_v.tick_params(
        axis="y", labelcolor=DARK, labelsize=OVERVIEW_YTICK_FONTSIZE
    )
    makespan_values = [makespan_dheft, makespan_nheft]
    vcpu_values = [vcpu_dheft, vcpu_nheft]
    if include_gheft:
        makespan_values.append(makespan_gheft)
        vcpu_values.append(vcpu_gheft)
    ax_m.set_ylim(0, finite_max(np.concatenate(makespan_values)) * 1.35)
    ax_v.set_ylim(
        0,
        finite_max(np.concatenate(vcpu_values)) * 1.25,
    )
    ax_m.grid(axis="y", linestyle="--", linewidth=0.6, alpha=0.35)

    annotate_line_points(
        ax_m,
        x,
        makespan_dheft,
        DARK,
        "{:.2f}",
        xytext=dheft_annotation_xytext,
        xytexts=dheft_annotation_xytexts,
        has=dheft_annotation_has,
        ha=dheft_annotation_ha,
    )
    annotate_line_points(
        ax_m,
        x,
        makespan_nheft,
        WASEDA_RED,
        "{:.2f}",
        xytext=(0, -12),
        va="top",
    )
    if include_gheft:
        annotate_line_points(
            ax_m,
            x,
            makespan_gheft,
            GREEN,
            "{:.2f}",
            xytext=gheft_annotation_xytext,
            xytexts=gheft_annotation_xytexts,
            has=gheft_annotation_has,
            ha=gheft_annotation_ha,
        )

    if split_legend:
        # The mean figures use two separate boxes so that the line and bar
        # encodings can be read independently.
        resource_handles = [bars_d, bars_n]
        resource_labels = ["DHEFT", "NHEFT"]
        performance_handles = [line_d[0], line_n[0]]
        performance_labels = ["DHEFT", "NHEFT"]
        if include_gheft:
            resource_handles.append(bars_g)
            resource_labels.append("GHEFT")
            performance_handles.append(line_g[0])
            performance_labels.append("GHEFT")
        resource_legend = ax_m.legend(
            resource_handles,
            resource_labels,
            title="Mean used vCPUs",
            loc="upper left",
            fontsize=OVERVIEW_LEGEND_FONTSIZE,
            title_fontsize=OVERVIEW_LEGEND_FONTSIZE,
            ncol=3,
            frameon=True,
        )
        ax_m.add_artist(resource_legend)
        ax_m.legend(
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
            # Preserve the original legend order for the three-algorithm
            # plots: all makespan lines, then all vCPU bars.
            handles = [
                line_d[0],
                line_n[0],
                line_g[0],
                bars_d,
                bars_n,
                bars_g,
            ]
        else:
            handles = [line_d[0], line_n[0], bars_d, bars_n]
        labels = [handle.get_label() for handle in handles]
        ax_m.legend(
            handles,
            labels,
            loc="upper left",
            fontsize=OVERVIEW_LEGEND_FONTSIZE,
            ncol=3,
            frameon=True,
        )
    if SHOW_OVERVIEW_TITLE:
        ax_m.set_title(title, fontsize=OVERVIEW_TITLE_FONTSIZE)

    fig.tight_layout(pad=0.6)
    output_path = os.path.join(output_dir, filename)
    fig.savefig(output_path, dpi=PLOT_DPI, bbox_inches="tight")
    # Keep the PNG output unchanged and also write a vector PDF beside it.
    vector_output_path = os.path.splitext(output_path)[0] + ".pdf"
    fig.savefig(vector_output_path, format="pdf", bbox_inches="tight")
    plt.close(fig)
    return output_path


def save_all_overview_plots(summary_df, output_dir):
    ordered_df = summary_df.reset_index(drop=True)
    plot_specs = [
        (
            ordered_df,
            "e3x_makespan_vcpu_overview.png",
            "E3X overview: baseline vs IRT-only GHEFT across 8 buckets",
        ),
        (
            ordered_df.iloc[:4].reset_index(drop=True),
            "e3x_makespan_vcpu_overview-1.png",
            "E3X overview: baseline vs IRT-only GHEFT (lower 4 buckets)",
        ),
        (
            ordered_df.iloc[4:8].reset_index(drop=True),
            "e3x_makespan_vcpu_overview-2.png",
            "E3X overview: baseline vs IRT-only GHEFT (upper 4 buckets)",
        ),
    ]

    output_paths = []
    for plot_df, filename, title in plot_specs:
        if plot_df.empty:
            continue
        output_paths.append(
            save_overview_plot(
                summary_df=plot_df,
                output_dir=output_dir,
                filename=filename,
                title=title,
            )
        )
    return output_paths


def save_three_composition_mean_outputs(mean_df):
    summary_csv = os.path.join(
        THIS_DIR, f"e3xyz_mean_bucket_summary_{TARGET_SEED_COUNT}.csv"
    )
    mean_df.to_csv(summary_csv, index=False)

    plot_specs = [
        (
            mean_df.iloc[:4].reset_index(drop=True),
            "e3xyz_mean_makespan_vcpu_overview-low.png",
            "Mean across 3 communication compositions (lower 4 NCCR buckets)",
            # low 图：前三个点在圆点正上方，第四个点移到圆点右侧。
            [(-8, 10), (-8, 8), (-8, 6), (-50, 0)],
            [(7, 4), (7, 4), (7, 6), (8, 0)],
            "center",
            ["right", "right", "right", "left"],
            ["left", "left", "left", "left"],
        ),
        (
            mean_df.iloc[4:8].reset_index(drop=True),
            "e3xyz_mean_makespan_vcpu_overview-high.png",
            "Mean across 3 communication compositions (upper 4 NCCR buckets)",
            # high 图的 GHEFT 四个标注：第 1 个下移，第 2 个不变，
            # 第 3 个上移，第 4 个不变。
            None,
            [(-50, 0), (-20, 4), (-25, 4), (-25, 4)],
            "left",
            None,
            None,
        ),
    ]

    plot_paths = []
    for (
        plot_df,
        filename,
        title,
        dheft_annotation_xytexts,
        gheft_annotation_xytexts,
        gheft_annotation_ha,
        dheft_annotation_has,
        gheft_annotation_has,
    ) in plot_specs:
        if plot_df.empty:
            continue
        plot_paths.append(
            save_overview_plot(
                summary_df=plot_df,
                output_dir=THIS_DIR,
                filename=filename,
                title=title,
                wrap_bucket_labels=False,
                split_legend=True,
                dheft_annotation_xytext=(0, 10),
                dheft_annotation_ha="center",
                gheft_annotation_xytext=(8, 6),
                gheft_annotation_xytexts=gheft_annotation_xytexts,
                dheft_annotation_xytexts=dheft_annotation_xytexts,
                gheft_annotation_ha=gheft_annotation_ha,
                dheft_annotation_has=dheft_annotation_has,
                gheft_annotation_has=gheft_annotation_has,
            )
        )

    # Keep the original three-algorithm low/high figures above unchanged.
    # These additional figures reuse the same means but omit GHEFT so that
    # DHEFT and NHEFT can be compared without the third bar/line.
    no_gheft_plot_specs = [
        (
            mean_df.iloc[:4].reset_index(drop=True),
            "e3xyz_mean_makespan_vcpu_overview-low-dheft-nheft.png",
            "Mean across 3 communication compositions (lower 4 NCCR buckets)",
            [(0, 10), (0, 10), (0, 10), (0, 10)],
            ["center", "center", "center", "center"],
        ),
        (
            mean_df.iloc[4:8].reset_index(drop=True),
            "e3xyz_mean_makespan_vcpu_overview-high-dheft-nheft.png",
            "Mean across 3 communication compositions (upper 4 NCCR buckets)",
            None,
            None,
        ),
    ]
    for (
        plot_df,
        filename,
        title,
        dheft_annotation_xytexts,
        dheft_annotation_has,
    ) in no_gheft_plot_specs:
        if plot_df.empty:
            continue
        plot_paths.append(
            save_overview_plot(
                summary_df=plot_df,
                output_dir=THIS_DIR,
                filename=filename,
                title=title,
                wrap_bucket_labels=False,
                split_legend=True,
                include_gheft=False,
                dheft_annotation_xytext=(0, 10),
                dheft_annotation_ha="center",
                dheft_annotation_xytexts=dheft_annotation_xytexts,
                dheft_annotation_has=dheft_annotation_has,
            )
        )
    return summary_csv, plot_paths


def format_md_int(value):
    if pd.isna(value):
        return "-"
    try:
        return str(int(value))
    except (TypeError, ValueError):
        return "-"


def format_md_pct(value):
    if pd.isna(value):
        return "-"
    try:
        return f"{float(value):.1f}%"
    except (TypeError, ValueError):
        return "-"


def format_md_float(value, digits=2):
    if pd.isna(value):
        return "-"
    try:
        return f"{float(value):.{digits}f}"
    except (TypeError, ValueError):
        return "-"


def format_md_p_value(value):
    if pd.isna(value):
        return "-"
    value = float(value)
    if value < 0.0001:
        return f"{value:.2e}"
    return f"{value:.4f}"


def build_statistical_summary(composition_summaries):
    bucket_order = {
        bucket_label: index
        for index, (bucket_label, _, _, _, _) in enumerate(BUCKET_SPECS)
    }
    composition_order = {"x": 0, "y": 1, "z": 2}
    combined = pd.concat(
        [composition_summaries[key] for key in ("x", "y", "z")],
        ignore_index=True,
    )
    combined["bucket_order"] = combined["bucket_label"].map(bucket_order)
    combined["composition_order"] = combined["composition_key"].map(
        composition_order
    )
    combined = combined.sort_values(
        ["bucket_order", "composition_order"]
    ).reset_index(drop=True)

    for spec in GHEFT_WILCOXON_SPECS:
        prefix = f"wilcoxon_{spec['key']}"
        raw_col = f"{prefix}_p_raw"
        holm_col = f"{prefix}_p_holm"
        significant_col = f"{prefix}_significant_holm"
        combined[holm_col] = holm_adjust(combined[raw_col].to_numpy(dtype=float))
        combined[significant_col] = (
            combined[holm_col].notna() & (combined[holm_col] < STAT_ALPHA)
        )

    return combined


def write_statistical_report(output_dir, statistical_df):
    output_path = os.path.join(output_dir, "e3xyz_statistical_report.md")
    lines = [
        "# GHEFT Paired Statistical Analysis",
        "",
        "## Method",
        "",
        (
            "- All statistics use paired per-seed observations after the same "
            "NCCR and CCR/IDR scenario filters used by the figures."
        ),
        (
            "- Variation is reported as the sample standard deviation of the "
            "per-seed percentage effect."
        ),
        (
            f"- The 95% confidence interval is a percentile bootstrap interval "
            f"for the mean ({BOOTSTRAP_RESAMPLES:,} resamples, fixed seed)."
        ),
        (
            "- Significance is tested with a two-sided paired Wilcoxon signed-rank "
            "test. Zero paired differences are excluded from the signed-rank sum."
        ),
        (
            "- Holm correction is applied across the 24 scenarios separately "
            "within each comparison family."
        ),
        (
            f"- `Significant` means Holm-adjusted p < {STAT_ALPHA:.2f}. A win rate "
            "is descriptive evidence and is not used as a replacement for this test."
        ),
    ]

    for spec in GHEFT_WILCOXON_SPECS:
        key = spec["key"]
        effect_prefix = spec["effect_prefix"]
        test_prefix = f"wilcoxon_{key}"
        significant_col = f"{test_prefix}_significant_holm"
        significant_count = int(statistical_df[significant_col].sum())

        lines.extend(
            [
                "",
                f"## {spec['title']}",
                "",
                f"Effect: {spec['effect_label']}. {spec['effect_interpretation']}",
                "",
                (
                    f"Holm-significant scenarios: {significant_count} / "
                    f"{len(statistical_df)}."
                ),
                "",
                "| NCCR bucket | Composition | Paired n | Mean effect | SD | 95% CI for mean | Nonzero n | W | Raw p | Holm p | Significant |",
                "| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | :---: |",
            ]
        )

        for _, row in statistical_df.iterrows():
            ci_text = "[{low}, {high}]".format(
                low=format_md_float(row.get(f"{effect_prefix}_ci95_low")),
                high=format_md_float(row.get(f"{effect_prefix}_ci95_high")),
            )
            lines.append(
                "| {bucket} | {composition} | {n} | {mean} | {sd} | {ci} | {nonzero} | {w} | {raw_p} | {holm_p} | {significant} |".format(
                    bucket=row["bucket_label"],
                    composition=row["composition_label"],
                    n=format_md_int(row.get(f"{test_prefix}_n")),
                    mean=format_md_float(row.get(f"{effect_prefix}_mean")),
                    sd=format_md_float(row.get(f"{effect_prefix}_sd")),
                    ci=ci_text,
                    nonzero=format_md_int(row.get(f"{test_prefix}_nonzero_n")),
                    w=format_md_float(row.get(f"{test_prefix}_statistic")),
                    raw_p=format_md_p_value(row.get(f"{test_prefix}_p_raw")),
                    holm_p=format_md_p_value(row.get(f"{test_prefix}_p_holm")),
                    significant=("Yes" if row.get(significant_col, False) else "No"),
                )
            )

    with open(output_path, "w", encoding="utf-8") as target:
        target.write("\n".join(lines) + "\n")
    return output_path


def resolve_nheft_source_run(latest_run_rel):
    """Resolve old `experiments/eNN/run_*` paths after the move to `three/`."""
    parts = os.path.normpath(str(latest_run_rel)).split(os.sep)
    if parts and parts[0] == "experiments":
        parts = parts[1:]
    run_dir = os.path.join(THREE_DIR, *parts)
    if not os.path.isdir(run_dir):
        raise FileNotFoundError(
            f"NHEFT source run does not exist: {run_dir} "
            f"(from {latest_run_rel})"
        )
    return run_dir


def scenario_true_mask(series):
    if pd.api.types.is_bool_dtype(series):
        return series.fillna(False)
    return (
        series.astype(str)
        .str.strip()
        .str.lower()
        .isin({"true", "1", "yes", "y"})
    )


def build_nheft_statistical_summary():
    """Build NHEFT statistics from the exact raw data behind Table I."""
    if not os.path.isfile(NHEFT_SOURCE_SUMMARY):
        raise FileNotFoundError(
            f"Authoritative NHEFT summary not found: {NHEFT_SOURCE_SUMMARY}"
        )

    source_summary = pd.read_csv(NHEFT_SOURCE_SUMMARY)
    required_summary_columns = {
        "family_key",
        "exp_dir",
        "scenario",
        "bucket_label",
        "latest_run_rel",
        "gain_N_over_D_mean",
        "win_rate_N_over_D",
    }
    missing = required_summary_columns - set(source_summary.columns)
    if missing:
        raise RuntimeError(
            "NHEFT source summary is missing columns: " + ", ".join(sorted(missing))
        )

    rows = []
    for _, source_row in source_summary.iterrows():
        family_key = str(source_row["family_key"])
        composition_key = NHEFT_FAMILY_TO_COMPOSITION.get(family_key)
        if composition_key is None:
            raise RuntimeError(f"Unexpected NHEFT family key: {family_key}")

        experiment_key = str(source_row["exp_dir"])
        scenario_key = str(source_row["scenario"])
        run_dir = resolve_nheft_source_run(source_row["latest_run_rel"])
        seed_csv = os.path.join(
            run_dir,
            f"{experiment_key}_seed_metrics_with_{scenario_key}_flag.csv",
        )
        if not os.path.isfile(seed_csv):
            raise FileNotFoundError(f"NHEFT per-seed source not found: {seed_csv}")

        seed_df = pd.read_csv(seed_csv)
        required_seed_columns = {
            "seed",
            "DHEFT",
            "NHEFT",
            f"{scenario_key}_match",
        }
        missing_seed = required_seed_columns - set(seed_df.columns)
        if missing_seed:
            raise RuntimeError(
                f"{seed_csv} is missing columns: " + ", ".join(sorted(missing_seed))
            )

        match_column = f"{scenario_key}_match"
        paired = seed_df[scenario_true_mask(seed_df[match_column])].copy()
        for column in ("seed", "DHEFT", "NHEFT"):
            paired[column] = pd.to_numeric(paired[column], errors="coerce")
        paired = (
            paired.dropna(subset=["seed", "DHEFT", "NHEFT"])
            .sort_values("seed")
            .drop_duplicates("seed")
        )
        if paired.empty:
            raise RuntimeError(f"No qualifying NHEFT pairs remain in {seed_csv}")

        gain_pct = safe_percent(
            paired["DHEFT"] - paired["NHEFT"],
            paired["DHEFT"],
        )
        win_rate_pct = float((paired["NHEFT"] < paired["DHEFT"]).mean() * 100.0)

        summary = {
            "bucket_label": str(source_row["bucket_label"]),
            "composition_key": composition_key,
            "composition_label": COMPOSITION_LABELS[composition_key],
            "experiment_key": experiment_key,
            "scenario_key": scenario_key,
            "paired_seed_count": int(len(paired)),
            "nheft_win_rate_pct": win_rate_pct,
            "source_run_dir": relpath(run_dir, base=os.path.dirname(EXPERIMENTS_DIR)),
            "source_seed_csv": relpath(seed_csv, base=os.path.dirname(EXPERIMENTS_DIR)),
        }
        summary.update(
            summarize_distribution(
                "dheft_makespan",
                paired["DHEFT"],
                f"original-nheft:{experiment_key}:dheft-makespan",
            )
        )
        summary.update(
            summarize_distribution(
                "nheft_makespan",
                paired["NHEFT"],
                f"original-nheft:{experiment_key}:nheft-makespan",
            )
        )
        summary.update(
            summarize_distribution(
                "nheft_gain_over_dheft_pct",
                gain_pct,
                f"original-nheft:{experiment_key}:gain",
            )
        )
        summary.update(
            summarize_paired_wilcoxon(
                "nheft_vs_dheft_makespan",
                paired["DHEFT"],
                paired["NHEFT"],
            )
        )

        # These checks make the new statistical table traceable to the existing
        # NHEFT gain/win table instead of silently changing the seed subset.
        expected_gain = float(source_row["gain_N_over_D_mean"])
        expected_win_pct = float(source_row["win_rate_N_over_D"]) * 100.0
        if not np.isclose(
            summary["nheft_gain_over_dheft_pct_mean"],
            expected_gain,
            rtol=1e-10,
            atol=1e-10,
        ):
            raise RuntimeError(
                f"NHEFT gain mismatch for {experiment_key}: "
                f"recomputed={summary['nheft_gain_over_dheft_pct_mean']}, "
                f"source={expected_gain}"
            )
        if not np.isclose(
            win_rate_pct,
            expected_win_pct,
            rtol=1e-10,
            atol=1e-10,
        ):
            raise RuntimeError(
                f"NHEFT win-rate mismatch for {experiment_key}: "
                f"recomputed={win_rate_pct}, source={expected_win_pct}"
            )
        rows.append(summary)

    result = pd.DataFrame(rows)
    if len(result) != 24:
        raise RuntimeError(
            f"Expected 24 original NHEFT scenarios, found {len(result)}"
        )

    bucket_order = {
        bucket_label: index
        for index, (bucket_label, _, _, _, _) in enumerate(BUCKET_SPECS)
    }
    composition_order = {"x": 0, "y": 1, "z": 2}
    result["bucket_order"] = result["bucket_label"].map(bucket_order)
    result["composition_order"] = result["composition_key"].map(composition_order)
    result = result.sort_values(["bucket_order", "composition_order"]).reset_index(
        drop=True
    )

    raw_column = "wilcoxon_nheft_vs_dheft_makespan_p_raw"
    holm_column = "wilcoxon_nheft_vs_dheft_makespan_p_holm"
    result[holm_column] = holm_adjust(result[raw_column].to_numpy(dtype=float))
    result["wilcoxon_nheft_vs_dheft_makespan_significant_holm"] = (
        result[holm_column].notna() & (result[holm_column] < STAT_ALPHA)
    )
    return result


def format_latex_p_value(value):
    if pd.isna(value):
        return "--"
    value = float(value)
    if value < 0.001:
        return r"$<.001$"
    return f"{value:.3f}"


def write_nheft_statistical_report(output_dir, statistical_df):
    output_path = os.path.join(
        output_dir, "nheft_vs_dheft_statistical_report.md"
    )
    significant_column = (
        "wilcoxon_nheft_vs_dheft_makespan_significant_holm"
    )
    significant_count = int(statistical_df[significant_column].sum())
    lines = [
        "# NHEFT vs DHEFT Paired Statistical Analysis",
        "",
        "## Method",
        "",
        (
            "- Source: the exact original 500-seed per-scenario files used to "
            "produce the paper's NHEFT gain-rate and win-rate table."
        ),
        "- Unit of analysis: a DHEFT/NHEFT pair generated from the same seed.",
        (
            "- Variation: sample standard deviation of the per-seed NHEFT "
            "gain over DHEFT."
        ),
        (
            f"- Confidence interval: {BOOTSTRAP_CONFIDENCE:.0%} percentile "
            f"bootstrap interval for the mean gain ({BOOTSTRAP_RESAMPLES:,} "
            "resamples, fixed random seed)."
        ),
        (
            "- Significance test: two-sided paired Wilcoxon signed-rank test "
            "for DHEFT and NHEFT makespan."
        ),
        (
            "- Multiple comparisons: Holm correction across all 24 scenarios; "
            f"significant means adjusted p < {STAT_ALPHA:.2f}."
        ),
        "",
        f"Holm-significant scenarios: {significant_count} / 24.",
        "",
        "| NCCR bucket | Composition | Paired n | Gain mean | Gain SD | 95% CI | Win rate | Raw p | Holm p | Significant |",
        "| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | :---: |",
    ]
    for _, row in statistical_df.iterrows():
        lines.append(
            "| {bucket} | {composition} | {n} | {mean:.2f}% | {sd:.2f} | "
            "[{low:.2f}, {high:.2f}] | {win:.1f}% | {raw_p} | {holm_p} | "
            "{significant} |".format(
                bucket=row["bucket_label"],
                composition=row["composition_label"],
                n=int(row["paired_seed_count"]),
                mean=float(row["nheft_gain_over_dheft_pct_mean"]),
                sd=float(row["nheft_gain_over_dheft_pct_sd"]),
                low=float(row["nheft_gain_over_dheft_pct_ci95_low"]),
                high=float(row["nheft_gain_over_dheft_pct_ci95_high"]),
                win=float(row["nheft_win_rate_pct"]),
                raw_p=format_md_p_value(
                    row["wilcoxon_nheft_vs_dheft_makespan_p_raw"]
                ),
                holm_p=format_md_p_value(
                    row["wilcoxon_nheft_vs_dheft_makespan_p_holm"]
                ),
                significant=("Yes" if row[significant_column] else "No"),
            )
        )
    with open(output_path, "w", encoding="utf-8") as target:
        target.write("\n".join(lines) + "\n")
    return output_path


def write_nheft_statistical_latex(output_dir, statistical_df):
    output_path = os.path.join(
        output_dir, "nheft_vs_dheft_statistical_table.tex"
    )
    lines = [
        "% Auto-generated by experiments/four/e3x/analyze_results.py",
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
    for bucket_label, _, _, _, _ in BUCKET_SPECS:
        row_cells = [bucket_label]
        for composition_key in ("x", "y", "z"):
            matching_rows = statistical_df[
                (statistical_df["bucket_label"] == bucket_label)
                & (statistical_df["composition_key"] == composition_key)
            ]
            if len(matching_rows) != 1:
                raise RuntimeError(
                    "Expected exactly one NHEFT statistical row for "
                    f"{bucket_label} / {composition_key}, found "
                    f"{len(matching_rows)}."
                )
            row = matching_rows.iloc[0]
            gain_text = "{mean:.2f}$\\pm${sd:.2f}".format(
                mean=float(row["nheft_gain_over_dheft_pct_mean"]),
                sd=float(row["nheft_gain_over_dheft_pct_sd"]),
            )
            if bool(
                row[
                    "wilcoxon_nheft_vs_dheft_makespan_significant_holm"
                ]
            ):
                gain_text += r"$^{*}$"
            row_cells.extend(
                [
                    gain_text,
                    "[{low:.2f},{high:.2f}]".format(
                        low=float(row["nheft_gain_over_dheft_pct_ci95_low"]),
                        high=float(row["nheft_gain_over_dheft_pct_ci95_high"]),
                    ),
                ]
            )
        lines.append(" & ".join(row_cells) + r" \\")
    lines.append(r"\hline")
    lines.extend(
        [
            r"\end{tabular}",
            r"}",
            r"\vspace{1mm}",
            (
                r"\parbox{\columnwidth}{\scriptsize All entries are percentages. "
                r"Gain is computed per seed before averaging; SD is the sample "
                r"standard deviation, and CI is a 10,000-resample 95\% "
                r"percentile-bootstrap interval for the mean. A superscript "
                r"$*$ marks a paired Wilcoxon signed-rank test that remains "
                r"significant after Holm correction across the 24 scenarios.}"
            ),
            r"\end{table}",
        ]
    )
    with open(output_path, "w", encoding="utf-8") as target:
        target.write("\n".join(lines) + "\n")
    return output_path


def save_nheft_gain_win_rate_combined_plot(output_dir, statistical_df):
    """Plot NHEFT-over-DHEFT gain and win rates on one percentage axis."""
    output_path = os.path.join(
        output_dir, "nheft_gain_win_rate_combined.png"
    )
    bucket_labels = [spec[0] for spec in BUCKET_SPECS]
    bucket_order = {label: index for index, label in enumerate(bucket_labels)}
    x = np.arange(len(bucket_labels))

    composition_styles = {
        "x": {
            "label": r"Balanced ($\mathrm{CCR}\approx\mathrm{IDR}$)",
            "color": "#4472C4",
            "marker": "o",
        },
        "y": {
            "label": r"Image-dominant ($\mathrm{CCR}<\mathrm{IDR}$)",
            "color": "#ED7D31",
            "marker": "s",
        },
        "z": {
            "label": r"Data-dominant ($\mathrm{CCR}>\mathrm{IDR}$)",
            "color": "#548235",
            "marker": "^",
        },
    }

    fig, ax = plt.subplots(figsize=NHEFT_GAIN_WIN_FIGSIZE)
    for composition_key, style in composition_styles.items():
        subset = statistical_df[
            statistical_df["composition_key"] == composition_key
        ].copy()
        subset["plot_order"] = subset["bucket_label"].map(bucket_order)
        subset = subset.sort_values("plot_order")
        if len(subset) != len(bucket_labels):
            raise RuntimeError(
                "Combined NHEFT gain/win plot requires all 8 buckets for "
                f"composition {composition_key}; found {len(subset)}"
            )

        gain = subset["nheft_gain_over_dheft_pct_mean"].to_numpy(dtype=float)
        win = subset["nheft_win_rate_pct"].to_numpy(dtype=float)
        ax.plot(
            x,
            gain,
            color=style["color"],
            marker=style["marker"],
            markersize=NHEFT_GAIN_WIN_MARKER_SIZE,
            linewidth=NHEFT_GAIN_WIN_LINE_WIDTH,
            linestyle="-",
            zorder=3,
        )
        ax.plot(
            x,
            win,
            color=style["color"],
            marker=style["marker"],
            markersize=NHEFT_GAIN_WIN_MARKER_SIZE,
            markerfacecolor="white",
            markeredgewidth=1.5,
            linewidth=NHEFT_GAIN_WIN_LINE_WIDTH,
            linestyle="--",
            zorder=3,
        )

    ax.axhline(0, color=DARK, linewidth=0.9, alpha=0.7, zorder=1)
    if SHOW_NHEFT_GAIN_WIN_X_AXIS_LABEL:
        ax.set_xlabel(
            "NCCR bucket",
            fontsize=NHEFT_GAIN_WIN_AXIS_LABEL_FONTSIZE,
        )
    ax.set_ylabel(
        "Percentage (%)",
        fontsize=NHEFT_GAIN_WIN_AXIS_LABEL_FONTSIZE,
    )
    ax.set_xticks(x)
    ax.set_xticklabels(
        [label.replace(", ", ",\n") for label in bucket_labels],
        rotation=0,
        fontsize=NHEFT_GAIN_WIN_XTICK_FONTSIZE,
    )
    # Keep a small band above the 100% win-rate curves, while removing the
    # unused 140%-160% region from the vertical scale.
    ax.set_ylim(-5, 140)
    ax.set_yticks([0, 20, 40, 60, 80, 100])
    ax.tick_params(axis="y", labelsize=NHEFT_GAIN_WIN_YTICK_FONTSIZE)
    # Make horizontal reference lines easier to follow without overpowering
    # the gain/win curves.
    ax.grid(
        axis="y",
        linestyle="--",
        linewidth=1.0,
        color="#8A8A8A",
        alpha=0.8,
    )

    win_handles = [
        Line2D(
            [0],
            [0],
            color=style["color"],
            marker=style["marker"],
            markersize=NHEFT_GAIN_WIN_MARKER_SIZE,
            markerfacecolor="white",
            markeredgecolor=style["color"],
            markeredgewidth=1.5,
            linewidth=NHEFT_GAIN_WIN_LINE_WIDTH,
            linestyle="--",
            label=style["label"],
        )
        for style in composition_styles.values()
    ]
    gain_handles = [
        Line2D(
            [0],
            [0],
            color=style["color"],
            marker=style["marker"],
            markersize=NHEFT_GAIN_WIN_MARKER_SIZE,
            markerfacecolor=style["color"],
            markeredgecolor=style["color"],
            linewidth=NHEFT_GAIN_WIN_LINE_WIDTH,
            linestyle="-",
            label=style["label"],
        )
        for style in composition_styles.values()
    ]

    # Split the legend by metric so each group sits near its three curves.
    win_legend = ax.legend(
        handles=win_handles,
        title="Win rate",
        loc="upper left",
        bbox_to_anchor=(0.01, NHEFT_GAIN_WIN_WIN_LEGEND_Y),
        fontsize=NHEFT_GAIN_WIN_LEGEND_FONTSIZE,
        title_fontsize=NHEFT_GAIN_WIN_LEGEND_TITLE_FONTSIZE,
        frameon=True,
        ncol=1,
    )
    ax.add_artist(win_legend)
    ax.legend(
        handles=gain_handles,
        title="Gain rate",
        loc="center right",
        bbox_to_anchor=(0.99, NHEFT_GAIN_WIN_GAIN_LEGEND_Y),
        fontsize=NHEFT_GAIN_WIN_LEGEND_FONTSIZE,
        title_fontsize=NHEFT_GAIN_WIN_LEGEND_TITLE_FONTSIZE,
        frameon=True,
        ncol=1,
    )

    fig.tight_layout()
    fig.savefig(output_path, dpi=PLOT_DPI, bbox_inches="tight")
    # Keep the PNG output unchanged and also write a vector PDF beside it.
    vector_output_path = os.path.splitext(output_path)[0] + ".pdf"
    fig.savefig(vector_output_path, format="pdf", bbox_inches="tight")
    plt.close(fig)
    return output_path


def write_nheft_statistical_outputs(output_dir):
    statistical_df = build_nheft_statistical_summary()
    csv_path = os.path.join(
        output_dir, "nheft_vs_dheft_statistical_summary.csv"
    )
    statistical_df.to_csv(csv_path, index=False)
    report_path = write_nheft_statistical_report(output_dir, statistical_df)
    latex_path = write_nheft_statistical_latex(output_dir, statistical_df)
    combined_plot_path = save_nheft_gain_win_rate_combined_plot(
        output_dir, statistical_df
    )
    return statistical_df, (
        csv_path,
        report_path,
        latex_path,
        combined_plot_path,
    )


def build_gheft_metrics_table_df(statistical_df):
    columns = {
        "bucket_label": "nccr_bucket",
        "composition_key": "composition_key",
        "composition_label": "composition",
        "paired_seed_count": "paired_n",
        "gheft_gain_over_dheft_pct_mean": "gain_g_over_d_pct",
        "gate_makespan_change_vs_nheft_pct_mean": "delta_m_g_over_n_pct",
        "gate_vcpu_reduction_vs_nheft_pct_mean": "delta_u_g_over_n_pct",
        "gheft_joint_success_rate_pct": "joint_success_rate_pct",
        "wilcoxon_gheft_vs_dheft_makespan_significant_holm": "gain_g_over_d_significant",
        "wilcoxon_gheft_vs_nheft_makespan_significant_holm": "delta_m_g_over_n_significant",
        "wilcoxon_gheft_vs_nheft_vcpus_significant_holm": "delta_u_g_over_n_significant",
    }
    table_df = statistical_df[list(columns)].rename(columns=columns).copy()
    return table_df


def write_gheft_metrics_markdown(output_dir, table_df):
    output_path = os.path.join(output_dir, "e3xyz_gheft_metrics_table.md")
    lines = [
        "# GHEFT Metrics by Scenario",
        "",
        (
            "- `Gain_G/D`: GHEFT makespan gain over DHEFT. Positive values mean "
            "that GHEFT is faster than DHEFT."
        ),
        (
            "- `DeltaM_G/N`: GHEFT makespan change from NHEFT. Positive values "
            "mean that GHEFT is slower than NHEFT."
        ),
        (
            "- `DeltaU_G/N`: GHEFT used-vCPU reduction from NHEFT. Positive "
            "values mean that GHEFT uses fewer vCPUs than NHEFT."
        ),
        (
            "- `Joint`: percentage of paired seeds for which GHEFT is faster "
            "than DHEFT and uses fewer vCPUs than NHEFT at the same time."
        ),
        (
            "- Every percentage is calculated for each paired seed first and "
            "then averaged within the scenario."
        ),
        (
            "- `*` marks a corresponding paired Wilcoxon signed-rank test that "
            "remains significant after Holm correction across the 24 scenarios."
        ),
    ]

    for composition_key in ("x", "y", "z"):
        composition_df = table_df[
            table_df["composition_key"] == composition_key
        ]
        if composition_df.empty:
            continue
        composition_label = composition_df.iloc[0]["composition"]
        lines.extend(
            [
                "",
                f"## {composition_label}",
                "",
                "| NCCR bucket | Paired n | Gain_G/D (%) | DeltaM_G/N (%) | DeltaU_G/N (%) | Joint (%) |",
                "| --- | ---: | ---: | ---: | ---: | ---: |",
            ]
        )
        for _, row in composition_df.iterrows():
            gain = format_md_float(row["gain_g_over_d_pct"])
            delta_m = format_md_float(row["delta_m_g_over_n_pct"])
            delta_u = format_md_float(row["delta_u_g_over_n_pct"])
            if bool(row["gain_g_over_d_significant"]):
                gain += "*"
            if bool(row["delta_m_g_over_n_significant"]):
                delta_m += "*"
            if bool(row["delta_u_g_over_n_significant"]):
                delta_u += "*"
            lines.append(
                "| {bucket} | {n} | {gain} | {delta_m} | {delta_u} | {joint} |".format(
                    bucket=row["nccr_bucket"],
                    n=format_md_int(row["paired_n"]),
                    gain=gain,
                    delta_m=delta_m,
                    delta_u=delta_u,
                    joint=format_md_float(row["joint_success_rate_pct"]),
                )
            )

    with open(output_path, "w", encoding="utf-8") as target:
        target.write("\n".join(lines) + "\n")
    return output_path


def write_gheft_metrics_latex(output_dir, table_df):
    output_path = os.path.join(output_dir, "e3xyz_gheft_metrics_table.tex")
    lines = [
        "% Auto-generated by experiments/four/e3x/analyze_results.py",
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

    for bucket_label, _, _, _, _ in BUCKET_SPECS:
        row_cells = [bucket_label]
        for composition_key in ("x", "y", "z"):
            matching_rows = table_df[
                (table_df["nccr_bucket"] == bucket_label)
                & (table_df["composition_key"] == composition_key)
            ]
            if len(matching_rows) != 1:
                raise RuntimeError(
                    "Expected exactly one GHEFT metrics row for "
                    f"{bucket_label} / {composition_key}, found "
                    f"{len(matching_rows)}."
                )
            row = matching_rows.iloc[0]
            gain_star = r"^{*}" if bool(row["gain_g_over_d_significant"]) else ""
            delta_m_star = r"^{*}" if bool(row["delta_m_g_over_n_significant"]) else ""
            delta_u_star = r"^{*}" if bool(row["delta_u_g_over_n_significant"]) else ""
            row_cells.extend(
                [
                    "${gain:.2f}{gain_star}$".format(
                    gain=float(row["gain_g_over_d_pct"]),
                    gain_star=gain_star,
                    ),
                    "${delta_m:.2f}{delta_m_star}$".format(
                    delta_m=float(row["delta_m_g_over_n_pct"]),
                    delta_m_star=delta_m_star,
                    ),
                    "${delta_u:.2f}{delta_u_star}$".format(
                    delta_u=float(row["delta_u_g_over_n_pct"]),
                    delta_u_star=delta_u_star,
                    ),
                ]
            )
        lines.append(" & ".join(row_cells) + r" \\")
    lines.append(r"\hline")

    lines.extend(
        [
            r"\end{tabular}",
            r"}",
            r"\vspace{1mm}",
            (
                r"\parbox{\columnwidth}{\scriptsize All metric entries are percentages "
                r"and are means of per-seed values. In each communication-composition "
                r"group, Gain denotes $\mathrm{Gain}_{G/D}$. Positive Gain "
                r"means that GHEFT is faster than DHEFT; positive $\Delta M_{G/N}$ "
                r"means that GHEFT is slower than NHEFT; positive $\Delta U_{G/N}$ "
                r"means that GHEFT uses fewer vCPUs than NHEFT. A superscript $*$ marks "
                r"a corresponding paired Wilcoxon signed-rank test that remains "
                r"significant after Holm correction across the 24 scenarios.}"
            ),
            r"\end{table}",
        ]
    )

    with open(output_path, "w", encoding="utf-8") as target:
        target.write("\n".join(lines) + "\n")
    return output_path


def write_gheft_metrics_outputs(output_dir, statistical_df):
    table_df = build_gheft_metrics_table_df(statistical_df)
    csv_path = os.path.join(output_dir, "e3xyz_gheft_metrics_table.csv")
    table_df.to_csv(csv_path, index=False)
    markdown_path = write_gheft_metrics_markdown(output_dir, table_df)
    latex_path = write_gheft_metrics_latex(output_dir, table_df)
    return csv_path, markdown_path, latex_path


def build_gheft_success_rates_df(statistical_df):
    columns = {
        "bucket_label": "nccr_bucket",
        "composition_key": "composition_key",
        "composition_label": "composition",
        "paired_seed_count": "paired_n",
        "gheft_performance_retention_count": "performance_retention_count",
        "gheft_performance_retention_rate_pct": "performance_retention_rate_pct",
        "gheft_performance_retention_ci95_low": "performance_retention_ci95_low",
        "gheft_performance_retention_ci95_high": "performance_retention_ci95_high",
        "gheft_resource_saving_count": "resource_saving_count",
        "gheft_resource_saving_rate_pct": "resource_saving_rate_pct",
        "gheft_resource_saving_ci95_low": "resource_saving_ci95_low",
        "gheft_resource_saving_ci95_high": "resource_saving_ci95_high",
        "gheft_joint_success_count": "joint_success_count",
        "gheft_joint_success_rate_pct": "joint_success_rate_pct",
        "gheft_joint_success_ci95_low": "joint_success_ci95_low",
        "gheft_joint_success_ci95_high": "joint_success_ci95_high",
    }
    return statistical_df[list(columns)].rename(columns=columns).copy()


def format_success_rate_cell(row, prefix):
    return "{count}/{n} ({rate}%; 95% CI [{low}, {high}])".format(
        count=format_md_int(row[f"{prefix}_count"]),
        n=format_md_int(row["paired_n"]),
        rate=format_md_float(row[f"{prefix}_rate_pct"]),
        low=format_md_float(row[f"{prefix}_ci95_low"]),
        high=format_md_float(row[f"{prefix}_ci95_high"]),
    )


def write_gheft_success_rates_markdown(output_dir, table_df):
    output_path = os.path.join(output_dir, "e3xyz_gheft_success_rates.md")
    lines = [
        "# GHEFT Paired-Seed Success Rates",
        "",
        "## Definitions",
        "",
        (
            "- Performance retention: `GHEFT makespan < DHEFT makespan` for "
            "the same seed."
        ),
        (
            "- Resource saving: `GHEFT used vCPUs < NHEFT used vCPUs` for "
            "the same seed."
        ),
        (
            "- Joint success: both strict conditions hold for the same seed."
        ),
        "- Ties are not counted as successes.",
        (
            f"- Each 95% CI is a {BOOTSTRAP_RESAMPLES:,}-resample percentile "
            "bootstrap interval for the paired-seed success rate."
        ),
    ]

    for composition_key in ("x", "y", "z"):
        composition_df = table_df[
            table_df["composition_key"] == composition_key
        ]
        if composition_df.empty:
            continue
        lines.extend(
            [
                "",
                f"## {composition_df.iloc[0]['composition']}",
                "",
                "| NCCR bucket | Performance retention | Resource saving | Joint success |",
                "| --- | ---: | ---: | ---: |",
            ]
        )
        for _, row in composition_df.iterrows():
            lines.append(
                "| {bucket} | {retention} | {saving} | {joint} |".format(
                    bucket=row["nccr_bucket"],
                    retention=format_success_rate_cell(
                        row, "performance_retention"
                    ),
                    saving=format_success_rate_cell(row, "resource_saving"),
                    joint=format_success_rate_cell(row, "joint_success"),
                )
            )

    with open(output_path, "w", encoding="utf-8") as target:
        target.write("\n".join(lines) + "\n")
    return output_path


def write_gheft_success_rates_latex(output_dir, table_df):
    output_path = os.path.join(output_dir, "e3xyz_gheft_success_rates.tex")
    composition_labels = {
        "x": r"Balanced ($\mathrm{CCR}\approx\mathrm{IDR}$)",
        "y": r"Image-dominant ($\mathrm{CCR}<\mathrm{IDR}$)",
        "z": r"Data-dominant ($\mathrm{CCR}>\mathrm{IDR}$)",
    }
    lines = [
        "% Auto-generated by experiments/four/e3x/analyze_results.py",
        r"\begin{table}[t]",
        r"\centering",
        r"\caption{Strict paired-seed target-achievement rates for GHEFT.}",
        r"\label{tab:gheft_success_rates}",
        r"\scriptsize",
        r"\setlength{\tabcolsep}{2.5pt}",
        r"\begin{tabular}{lrrrr}",
        r"\hline",
        r"NCCR bucket & $n$ & Retain & Save & Joint \\",
        r"\hline",
    ]

    for composition_key in ("x", "y", "z"):
        composition_df = table_df[
            table_df["composition_key"] == composition_key
        ]
        if composition_df.empty:
            continue
        lines.append(
            rf"\multicolumn{{5}}{{l}}{{\textit{{{composition_labels[composition_key]}}}}} \\"
        )
        for _, row in composition_df.iterrows():
            lines.append(
                "{bucket} & {n} & {retention:.1f} & {saving:.1f} & "
                "{joint:.1f} \\\\".format(
                    bucket=row["nccr_bucket"],
                    n=int(row["paired_n"]),
                    retention=float(row["performance_retention_rate_pct"]),
                    saving=float(row["resource_saving_rate_pct"]),
                    joint=float(row["joint_success_rate_pct"]),
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
                r"both strict inequalities hold for the same seed. Ties are "
                r"not successes.}"
            ),
            r"\end{table}",
        ]
    )

    with open(output_path, "w", encoding="utf-8") as target:
        target.write("\n".join(lines) + "\n")
    return output_path


def write_gheft_success_rates_outputs(output_dir, statistical_df):
    table_df = build_gheft_success_rates_df(statistical_df)
    csv_path = os.path.join(output_dir, "e3xyz_gheft_success_rates.csv")
    table_df.to_csv(csv_path, index=False)
    markdown_path = write_gheft_success_rates_markdown(output_dir, table_df)
    latex_path = write_gheft_success_rates_latex(output_dir, table_df)
    return csv_path, markdown_path, latex_path


def write_statistical_outputs(output_dir, composition_summaries):
    statistical_df = build_statistical_summary(composition_summaries)
    csv_path = os.path.join(output_dir, "e3xyz_statistical_summary.csv")
    statistical_df.to_csv(csv_path, index=False)
    report_path = write_statistical_report(output_dir, statistical_df)
    gheft_table_paths = write_gheft_metrics_outputs(output_dir, statistical_df)
    gheft_success_rate_paths = write_gheft_success_rates_outputs(
        output_dir, statistical_df
    )
    nheft_statistical_df, nheft_statistical_paths = (
        write_nheft_statistical_outputs(output_dir)
    )
    return (
        statistical_df,
        csv_path,
        report_path,
        gheft_table_paths,
        gheft_success_rate_paths,
        nheft_statistical_df,
        nheft_statistical_paths,
    )


def write_seed_coverage_md(output_dir, summary_df):
    output_path = os.path.join(output_dir, "e3x_seed_coverage_report.md")
    lines = [
        "# E3X Seed Coverage Report",
        "",
        "## Definitions",
        "- Baseline side: shared baseline results from `e01x` to `e08x`.",
        "- GHEFT side: IRT-only gate results from `e31x` to `e38x`.",
        "- Recorded seeds: unique seeds that appear in the raw CSV.",
        "- OK seeds: recorded seeds that contain at least one `status = ok` row.",
        (
            "- Valid seeds: OK seeds that satisfy the current bucket rule "
            f"and the x-condition (`|CCR_data - IDR_image| <= {BALANCED_ABS_TOL:.4f}`)."
        ),
        (
            "- Paired seeds: seeds that are valid on both sides and therefore "
            "actually used in the final aggregation."
        ),
        "",
        "## Coverage Table",
        "",
        "| Bucket | Baseline recorded | Baseline valid | GHEFT recorded | GHEFT valid | Paired seeds | Paired / Baseline valid | Paired / GHEFT valid |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]

    for _, row in summary_df.iterrows():
        lines.append(
            "| {bucket} | {b_rec} | {b_val} | {g_rec} | {g_val} | {paired} | {p_b} | {p_g} |".format(
                bucket=row["bucket_label"],
                b_rec=format_md_int(row.get("baseline_recorded_seed_count")),
                b_val=format_md_int(row.get("baseline_valid_seed_count")),
                g_rec=format_md_int(row.get("gate_recorded_seed_count")),
                g_val=format_md_int(row.get("gate_valid_seed_count")),
                paired=format_md_int(row.get("paired_seed_count")),
                p_b=format_md_pct(row.get("pair_rate_vs_baseline_valid_pct")),
                p_g=format_md_pct(row.get("pair_rate_vs_gate_valid_pct")),
            )
        )

    low_coverage = summary_df[summary_df["paired_seed_count"] < 100]
    if not low_coverage.empty:
        lines.extend(
            [
                "",
                "## Low-Coverage Buckets",
                "",
                "The following buckets have fewer than 100 paired seeds:",
                "",
            ]
        )
        for _, row in low_coverage.iterrows():
            lines.append(
                f"- {row['bucket_label']}: paired seeds = {int(row['paired_seed_count'])}"
            )

    with open(output_path, "w", encoding="utf-8") as target:
        target.write("\n".join(lines) + "\n")
    return output_path


def write_manifest(output_dir, summary_df):
    payload = {
        "analysis": "E3X cross-bucket aggregation",
        "timestamp": datetime.now().strftime("%Y%m%d_%H%M%S"),
        "bucket_count": int(len(summary_df)),
        "target_seed_count": TARGET_SEED_COUNT,
        "balanced_abs_tol": BALANCED_ABS_TOL,
        "gate_variant": GATE_VARIANT,
        "statistical_analysis": {
            "gheft_unit": (
                "strict DHEFT/NHEFT/GHEFT paired per-seed observations after "
                "scenario filtering"
            ),
            "nheft_unit": (
                "original DHEFT/NHEFT paired 500-seed observations used by "
                "the paper's NHEFT gain/win table"
            ),
            "nheft_source_summary": relpath(
                NHEFT_SOURCE_SUMMARY,
                base=os.path.dirname(EXPERIMENTS_DIR),
            ),
            "test": "two-sided paired Wilcoxon signed-rank test",
            "multiple_comparison_correction": (
                "Holm correction across 24 scenarios per comparison family"
            ),
            "alpha": STAT_ALPHA,
            "confidence_interval": (
                f"{BOOTSTRAP_CONFIDENCE:.0%} percentile bootstrap CI for the mean"
            ),
            "bootstrap_resamples": BOOTSTRAP_RESAMPLES,
            "bootstrap_random_seed": BOOTSTRAP_RANDOM_SEED,
            "gheft_success_rates": {
                "performance_retention": "GHEFT makespan < DHEFT makespan",
                "resource_saving": "GHEFT used vCPUs < NHEFT used vCPUs",
                "joint_success": (
                    "both strict conditions hold for the same paired seed"
                ),
                "ties_count_as_success": False,
            },
        },
        "note": (
            "Each bucket uses only paired seeds after x-condition filtering. "
            "GHEFT corresponds to the irt_only gate side."
        ),
        "buckets": summary_df.to_dict(orient="records"),
    }
    with open(
        os.path.join(output_dir, "analysis_manifest.json"), "w", encoding="utf-8"
    ) as target:
        json.dump(payload, target, indent=2, ensure_ascii=False)


def main():
    args = parse_args()
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_dir = args.output_dir or os.path.join(
        THIS_DIR, f"analysis_{timestamp}_{TARGET_SEED_COUNT}"
    )
    os.makedirs(output_dir, exist_ok=True)

    composition_summaries = {
        key: collect_composition_summary(key) for key in ("x", "y", "z")
    }
    (
        _,
        statistical_csv_path,
        statistical_report_path,
        gheft_table_paths,
        gheft_success_rate_paths,
        _,
        nheft_statistical_paths,
    ) = write_statistical_outputs(output_dir, composition_summaries)
    summary_df = composition_summaries["x"]
    summary_csv = os.path.join(output_dir, "e3x_bucket_summary.csv")
    summary_df.to_csv(summary_csv, index=False)
    plot_paths = save_all_overview_plots(summary_df, output_dir)
    coverage_md_path = write_seed_coverage_md(output_dir, summary_df)
    write_manifest(output_dir, summary_df)

    mean_df = build_three_composition_mean(composition_summaries)
    mean_summary_csv, mean_plot_paths = save_three_composition_mean_outputs(mean_df)

    print("E3X cross-bucket aggregation complete.")
    print(f"Target seed count: {TARGET_SEED_COUNT}")
    print(f"Output dir: {relpath(output_dir)}")
    print(f"Summary CSV: {relpath(summary_csv)}")
    print(f"Coverage MD: {relpath(coverage_md_path)}")
    print(f"Statistical CSV: {relpath(statistical_csv_path)}")
    print(f"Statistical report: {relpath(statistical_report_path)}")
    for statistical_path in nheft_statistical_paths:
        print(f"NHEFT statistical output: {relpath(statistical_path)}")
    for table_path in gheft_table_paths:
        print(f"GHEFT metrics table: {relpath(table_path)}")
    for table_path in gheft_success_rate_paths:
        print(f"GHEFT success-rate table: {relpath(table_path)}")
    for plot_path in plot_paths:
        print(f"Plot: {relpath(plot_path)}")
    print(f"Three-composition mean CSV: {relpath(mean_summary_csv)}")
    for plot_path in mean_plot_paths:
        print(f"Three-composition mean plot: {relpath(plot_path)}")


if __name__ == "__main__":
    main()
