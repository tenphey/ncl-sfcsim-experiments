#!/usr/bin/env python3
"""Analyze E22Z NHEFT comp+DRT gate results.

This script reads an existing run_* folder produced by run_experiment.py.  It
never launches Java and never modifies the raw CSV.

The main comparison is paired by seed:

- baseline: current NHEFT behavior
- comp_drt: NHEFT with the comp+DRT gates enabled

If a run was stopped in the middle of a seed, that incomplete seed is excluded
from all summaries and plots.  A seed is used only when it has all expected E22Z
variants.

Usage from the simulator repository root:

  experiments/.venv/bin/python \
      experiments/four/e22z/analyze_results.py

  experiments/.venv/bin/python \
      experiments/four/e22z/analyze_results.py \
      run_20260810_170000_151_50
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


RAW_CSV_NAME = "e22z_results.csv"
BASE_VARIANT = "baseline"
WASEDA_RED = "#8E1728"
GREY = "#CFCFCF"
DARK = "#172A33"
GREEN = "#0B7F5B"
ORANGE = "#D97904"
PLOT_DPI = 300
FIGSIZE_COMBINED = (9.2, 5.8)
FIGSIZE_DELTA = (9.2, 5.8)


def parse_args():
    parser = argparse.ArgumentParser(
        description="Analyze an existing E22Z comp+DRT result folder."
    )
    parser.add_argument(
        "result_folder",
        nargs="?",
        help=(
            "run_* folder path or basename. If omitted, the latest run_* folder "
            "with e22z_results.csv is used."
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


def read_manifest(result_dir):
    manifest_path = os.path.join(result_dir, "run_manifest.json")
    if not os.path.exists(manifest_path):
        return {}
    with open(manifest_path, encoding="utf-8") as source:
        return json.load(source)


def expected_variants_from_manifest(manifest, df):
    variants = manifest.get("variants") or []
    labels = []
    display = {}
    for variant in variants:
        label = str(variant.get("label", "")).strip()
        if not label:
            continue
        labels.append(label)
        display[label] = variant.get("display_label", label)

    if not labels:
        labels = sorted(str(value) for value in df["variant"].dropna().unique())
        if BASE_VARIANT in labels:
            labels.remove(BASE_VARIANT)
            labels.insert(0, BASE_VARIANT)
        display = {
            label: df.loc[df["variant"] == label, "variant_display_label"].dropna().iloc[0]
            if "variant_display_label" in df.columns
            and not df.loc[df["variant"] == label, "variant_display_label"].dropna().empty
            else label
            for label in labels
        }

    if BASE_VARIANT not in labels:
        raise RuntimeError("The baseline variant is required for E22Z paired analysis")
    if len(labels) < 2:
        raise RuntimeError("At least two variants are required for E22Z analysis")
    return labels, display


def safe_percent(numerator, denominator):
    denominator = np.asarray(denominator, dtype=float)
    numerator = np.asarray(numerator, dtype=float)
    with np.errstate(divide="ignore", invalid="ignore"):
        result = numerator / denominator * 100.0
    return np.where(np.isfinite(result), result, np.nan)

MIN_REL_GAP_PCT = float(os.getenv("E22Z_MIN_REL_GAP_PCT", "20.0"))


def calc_relative_gap_pct(a, b):
    if pd.isna(a) or pd.isna(b):
        return np.nan
    avg = (a + b) / 2.0
    if avg == 0:
        return np.nan
    return abs(a - b) / avg * 100.0


def filter_scenario_rows(ok):
    required = ["ccr_data", "idr_image", "nccr_total"]
    missing = [col for col in required if col not in ok.columns]
    if missing:
        raise RuntimeError(f"Missing scenario columns: {missing}")

    scenario_ok = ok.dropna(subset=required).copy()
    if scenario_ok.empty:
        raise RuntimeError("No ok rows have complete CCR/IDR/NCCR metrics")

    scenario_ok["ccr_idr_rel_gap_pct"] = [
        calc_relative_gap_pct(a, b)
        for a, b in zip(scenario_ok["ccr_data"], scenario_ok["idr_image"])
    ]
    scenario_ok["scenario_match"] = (
        (scenario_ok["nccr_total"] > 0.10)
        & (scenario_ok["nccr_total"] <= 0.18)
        & (scenario_ok["ccr_data"] > scenario_ok["idr_image"])
        & (scenario_ok["ccr_idr_rel_gap_pct"] >= MIN_REL_GAP_PCT)
    )

    scenario_rule = (
        f"0.18 < NCCR_total <= 0.32 AND CCR_data > IDR_image AND relative CCR/IDR gap >= {MIN_REL_GAP_PCT:.2f}%"
    )
    filtered = scenario_ok[scenario_ok["scenario_match"]].copy()
    if filtered.empty:
        raise RuntimeError(f"No ok rows satisfy the scenario rule: {scenario_rule}")
    return filtered, scenario_rule



def load_raw_csv(result_dir):
    csv_path = os.path.join(result_dir, RAW_CSV_NAME)
    if not os.path.exists(csv_path):
        raise FileNotFoundError(f"CSV not found: {csv_path}")

    df = pd.read_csv(csv_path)
    if df.empty:
        raise RuntimeError(f"CSV is empty: {csv_path}")

    numeric_cols = [
        "seed",
        "is_baseline_nheft",
        "configured_tolerance",
        "configured_comp_advantage",
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

    df["variant"] = df["variant"].astype(str)
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
        "configured_tolerance",
        "configured_comp_advantage",
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

    ok = ok.dropna(subset=[col for col in required if col != "variant"]).copy()
    if ok.empty:
        raise RuntimeError("No ok rows have complete core metrics")
    return ok


def filter_complete_seeds(ok, expected_variants):
    expected_set = set(expected_variants)
    report_rows = []
    complete_seeds = []
    for seed, group in ok.groupby("seed", sort=True):
        observed_set = set(group["variant"].dropna().astype(str))
        missing = [label for label in expected_variants if label not in observed_set]
        extra = sorted(observed_set - expected_set)
        is_complete = len(missing) == 0
        if is_complete:
            complete_seeds.append(seed)
        report_rows.append(
            {
                "seed": int(seed),
                "is_complete": is_complete,
                "completed_variant_count": len(observed_set & expected_set),
                "expected_variant_count": len(expected_variants),
                "completed_variants": ",".join(
                    label for label in expected_variants if label in observed_set
                ),
                "missing_variants": ",".join(missing),
                "extra_variants": ",".join(extra),
            }
        )

    if not complete_seeds:
        raise RuntimeError(
            "No complete seeds found. At least one seed must have all expected "
            f"variants: {', '.join(expected_variants)}"
        )

    complete_ok = ok[ok["seed"].isin(complete_seeds)].copy()
    report = pd.DataFrame(report_rows)
    return complete_ok, report


def build_paired_metrics(ok):
    baseline = ok[ok["variant"] == BASE_VARIANT].copy()
    if baseline.empty:
        raise RuntimeError("No baseline rows were found")

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
        raise RuntimeError("No rows can be paired with the baseline variant")

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
    paired["vcpu_not_more_than_base"] = paired["nheft_vcpus"] <= paired["base_nheft_vcpus"]
    paired["vcpu_strictly_reduced"] = paired["nheft_vcpus"] < paired["base_nheft_vcpus"]
    return paired


def bool_mean_percent(series):
    return float(series.mean() * 100.0) if len(series) else np.nan


def build_variant_summary(paired, expected_variants, display_labels):
    order_map = {label: index for index, label in enumerate(expected_variants)}
    rows = []
    for variant, group in paired.groupby("variant", sort=False):
        rows.append(
            {
                "variant": variant,
                "variant_order": order_map.get(variant, 999),
                "display_label": display_labels.get(variant, variant),
                "paired_rows": len(group),
                "paired_seeds": group["seed"].nunique(),
                "configured_tolerance_mean": group["configured_tolerance"].mean(),
                "configured_comp_advantage_mean": group[
                    "configured_comp_advantage"
                ].mean(),
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
                "vcpu_not_more_than_base_rate_pct": bool_mean_percent(
                    group["vcpu_not_more_than_base"]
                ),
                "vcpu_strictly_reduced_rate_pct": bool_mean_percent(
                    group["vcpu_strictly_reduced"]
                ),
            }
        )

    summary = pd.DataFrame(rows).sort_values("variant_order").reset_index(drop=True)
    return summary


def build_reference_summary(paired):
    baseline = paired[paired["variant"] == BASE_VARIANT].copy()
    rows = []
    for label, prefix in [
        ("HEFT", "heft"),
        ("DHEFT", "dheft"),
        ("NHEFT", "nheft"),
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


def save_combined_makespan_vcpu_plot(summary, reference, output_dir):
    dheft = reference[reference["algorithm"] == "DHEFT"].iloc[0]

    labels = ["DHEFT"] + summary["display_label"].tolist()
    makespan_values = [dheft["makespan_mean"]] + summary[
        "nheft_makespan_mean"
    ].tolist()
    vcpu_values = [dheft["vcpus_mean"]] + summary["nheft_vcpus_mean"].tolist()

    x = np.arange(len(labels))
    fig, ax_makespan = plt.subplots(figsize=FIGSIZE_COMBINED)
    ax_vcpu = ax_makespan.twinx()

    bars = ax_vcpu.bar(
        x,
        vcpu_values,
        width=0.52,
        color=GREY,
        edgecolor=DARK,
        linewidth=0.8,
        alpha=0.8,
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
    ax_makespan.set_xticklabels(labels, rotation=15, ha="right")
    ax_makespan.set_ylim(0, finite_max(makespan_values) * 1.25)
    add_grid(ax_makespan)

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
    legend_labels = [handle.get_label() for handle in handles]
    ax_makespan.legend(handles, legend_labels, loc="upper left")
    ax_makespan.set_title("Mean Makespan and vCPU Use")
    fig.tight_layout()
    fig.savefig(
        os.path.join(output_dir, "makespan_vcpu_combined_line_bar.png"),
        dpi=PLOT_DPI,
    )
    plt.close(fig)


def save_delta_plot(summary, output_dir):
    non_base = summary[summary["variant"] != BASE_VARIANT].copy()
    if non_base.empty:
        return

    x = np.arange(len(non_base))
    labels = non_base["display_label"].tolist()
    fig, ax1 = plt.subplots(figsize=FIGSIZE_DELTA)
    ax2 = ax1.twinx()

    bars = ax2.bar(
        x,
        non_base["vcpu_reduction_vs_base_pct_mean"],
        width=0.48,
        color=GREY,
        edgecolor=DARK,
        linewidth=0.8,
        alpha=0.8,
        label="vCPU reduction vs NHEFT",
        zorder=1,
    )
    line = ax1.plot(
        x,
        non_base["makespan_change_vs_base_pct_mean"],
        color=WASEDA_RED,
        marker="o",
        linewidth=2.6,
        label="makespan change vs NHEFT",
        zorder=4,
    )

    ax1.axhline(0, color=DARK, linewidth=1.0, alpha=0.6)
    ax2.axhline(0, color=DARK, linewidth=1.0, alpha=0.25)
    ax1.set_xticks(x)
    ax1.set_xticklabels(labels, rotation=10, ha="right")
    ax1.set_ylabel("Makespan change (%)", color=WASEDA_RED)
    ax1.tick_params(axis="y", labelcolor=WASEDA_RED)
    ax2.set_ylabel("vCPU reduction (%)", color=DARK)
    ax2.tick_params(axis="y", labelcolor=DARK)
    add_grid(ax1)

    handles = [line[0], bars]
    legend_labels = [handle.get_label() for handle in handles]
    ax1.legend(handles, legend_labels, loc="best")
    ax1.set_title("Resource Saving and Makespan Cost vs Baseline NHEFT")
    fig.tight_layout()
    fig.savefig(os.path.join(output_dir, "delta_vs_baseline_nheft.png"), dpi=PLOT_DPI)
    plt.close(fig)


def save_summary_table(summary, output_dir):
    display_cols = [
        "display_label",
        "paired_seeds",
        "configured_tolerance_mean",
        "configured_comp_advantage_mean",
        "nheft_makespan_mean",
        "makespan_change_vs_base_pct_mean",
        "nheft_vcpus_mean",
        "vcpu_reduction_vs_base_pct_mean",
        "gain_nheft_over_dheft_pct_mean",
        "win_rate_over_dheft_pct",
        "vcpu_strictly_reduced_rate_pct",
    ]
    display = summary[display_cols].copy()
    display = display.rename(
        columns={
            "display_label": "method",
            "paired_seeds": "seeds",
            "configured_tolerance_mean": "tol",
            "configured_comp_advantage_mean": "comp gate",
            "nheft_makespan_mean": "mean makespan",
            "makespan_change_vs_base_pct_mean": "makespan change vs NHEFT (%)",
            "nheft_vcpus_mean": "mean vCPUs",
            "vcpu_reduction_vs_base_pct_mean": "vCPU reduction vs NHEFT (%)",
            "gain_nheft_over_dheft_pct_mean": "gain over DHEFT (%)",
            "win_rate_over_dheft_pct": "win rate over DHEFT (%)",
            "vcpu_strictly_reduced_rate_pct": "fewer-vCPU rate vs NHEFT (%)",
        }
    )
    for col in display.columns:
        if col not in ("method", "seeds"):
            display[col] = display[col].map(lambda v: "" if pd.isna(v) else f"{v:.2f}")

    fig_height = max(3.0, 0.55 * (len(display) + 2))
    fig, ax = plt.subplots(figsize=(15, fig_height))
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
    fig.savefig(os.path.join(output_dir, "variant_summary_table.png"), dpi=PLOT_DPI)
    plt.close(fig)


def write_analysis_manifest(
    output_dir,
    result_dir,
    raw_df,
    ok_df,
    scenario_ok_df,
    complete_ok_df,
    paired_df,
    summary_df,
    complete_seed_report,
    expected_variants,
    scenario_rule,
):
    manifest = {
        "analysis": "E22Z NHEFT comp+DRT gate analysis",
        "timestamp": datetime.now().strftime("%Y%m%d_%H%M%S"),
        "result_dir": result_dir,
        "raw_csv": os.path.join(result_dir, RAW_CSV_NAME),
        "raw_rows": int(len(raw_df)),
        "ok_rows": int(len(ok_df)),
        "scenario_ok_rows": int(len(scenario_ok_df)),
        "complete_ok_rows": int(len(complete_ok_df)),
        "complete_seeds": int(complete_seed_report["is_complete"].sum()),
        "incomplete_seeds": int((~complete_seed_report["is_complete"]).sum()),
        "paired_rows": int(len(paired_df)),
        "paired_seeds": int(paired_df["seed"].nunique()),
        "complete_seed_rule": (
            "Only seeds with all expected E22Z variants are included in summaries "
            "and plots."
        ),
        "expected_variants_for_complete_seed": expected_variants,
        "baseline": "variant=baseline is treated as current NHEFT behavior",
        "notes": [
            "Makespan change vs baseline is positive when the variant is slower.",
            "vCPU reduction vs baseline is positive when the variant uses fewer vCPUs.",
            "Gain over DHEFT is the mean of per-run gains, not the gain from bucket-level means.",
        ],
        "variants": summary_df["variant"].tolist(),
    }
    with open(os.path.join(output_dir, "analysis_manifest.json"), "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)
        f.write("\n")


def main():
    args = parse_args()
    result_dir = resolve_result_dir(args.result_folder)
    if not result_dir:
        print("No E22Z result folder found.")
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
    manifest = read_manifest(result_dir)
    expected_variants, display_labels = expected_variants_from_manifest(manifest, raw_df)
    ok_df = filter_ok_rows(raw_df)
    scenario_ok_df, scenario_rule = filter_scenario_rows(ok_df)
    complete_ok_df, complete_seed_report = filter_complete_seeds(scenario_ok_df, expected_variants)
    paired_df = build_paired_metrics(complete_ok_df)
    summary_df = build_variant_summary(paired_df, expected_variants, display_labels)
    reference_df = build_reference_summary(paired_df)

    paired_csv = os.path.join(output_dir, "e22z_seed_variant_paired_metrics.csv")
    summary_csv = os.path.join(output_dir, "e22z_variant_summary.csv")
    reference_csv = os.path.join(output_dir, "e22z_reference_summary.csv")
    complete_seed_report_csv = os.path.join(output_dir, "e22z_complete_seed_report.csv")
    paired_df.to_csv(paired_csv, index=False)
    summary_df.to_csv(summary_csv, index=False)
    reference_df.to_csv(reference_csv, index=False)
    complete_seed_report.to_csv(complete_seed_report_csv, index=False)

    save_combined_makespan_vcpu_plot(summary_df, reference_df, output_dir)
    save_delta_plot(summary_df, output_dir)
    save_summary_table(summary_df, output_dir)
    write_analysis_manifest(
        output_dir,
        result_dir,
        raw_df,
        ok_df,
        scenario_ok_df,
        complete_ok_df,
        paired_df,
        summary_df,
        complete_seed_report,
        expected_variants,
        scenario_rule,
    )

    non_base = summary_df[summary_df["variant"] != BASE_VARIANT].copy()

    print("=== E22Z Analysis Complete ===")
    print(f"Input result dir: {result_dir}")
    print(f"Output dir: {output_dir}")
    print(f"Raw rows: {len(raw_df)}")
    print(f"OK rows: {len(ok_df)}")
    print(f"Scenario-qualified OK rows: {len(scenario_ok_df)}")
    print(f"Scenario rule: {scenario_rule}")
    print(f"Complete seeds: {int(complete_seed_report['is_complete'].sum())}")
    print(f"Incomplete seeds dropped: {int((~complete_seed_report['is_complete']).sum())}")
    print(f"Expected variants: {', '.join(expected_variants)}")
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
        "makespan_vcpu_combined_line_bar.png",
        "delta_vs_baseline_nheft.png",
        "variant_summary_table.png",
    ]:
        print(f"  {relpath(os.path.join(output_dir, name))}")

    if not non_base.empty:
        best_resource_row = non_base.sort_values(
            ["vcpu_reduction_vs_base_pct_mean", "makespan_change_vs_base_pct_mean"],
            ascending=[False, True],
        ).iloc[0]
        print()
        print(
            "Largest mean vCPU reduction vs baseline NHEFT: "
            f"{best_resource_row['display_label']}, "
            f"vCPU reduction={best_resource_row['vcpu_reduction_vs_base_pct_mean']:.2f}%, "
            f"makespan change={best_resource_row['makespan_change_vs_base_pct_mean']:.2f}%"
        )


if __name__ == "__main__":
    main()
