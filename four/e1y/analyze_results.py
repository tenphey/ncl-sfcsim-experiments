#!/usr/bin/env python3
"""Aggregate all E1Y bucket results into one cross-bucket overview.

This script combines the latest raw results of:

  e11y, e12y, e13y, e14y, e15y, e16y, e17y, e18y

Each bucket keeps the original y-condition filtering:

  NCCR bucket AND CCR_data < IDR_image AND relative CCR/IDR gap >= min_rel_gap_pct

Only complete seeds are used. A seed is counted only when both expected E1
variants exist inside the same bucket after scenario filtering:

  - baseline       -> plotted as NHEFT
  - comp_advantage -> plotted as GHEFT

The output is one overview figure:

  - x axis: 8 NCCR buckets
  - left y axis: DHEFT / NHEFT / GHEFT mean makespan lines
  - right y axis: DHEFT / NHEFT / GHEFT mean used-vCPU bars

Usage from the simulator repository root:

  experiments/.venv/bin/python experiments/four/e1y/analyze_results.py
"""

import argparse
import json
import os
from datetime import datetime


THIS_DIR = os.path.dirname(os.path.abspath(__file__))
FOUR_DIR = os.path.dirname(THIS_DIR)
CACHE_DIR = os.path.join(THIS_DIR, ".plot_cache")
os.makedirs(CACHE_DIR, exist_ok=True)
os.environ.setdefault("MPLCONFIGDIR", CACHE_DIR)
os.environ.setdefault("XDG_CACHE_HOME", CACHE_DIR)

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


WASEDA_RED = "#8E1728"
GREEN = "#0B7F5B"
GREY = "#BDBDBD"
DARK = "#172A33"
PLOT_DPI = 300
FIGSIZE_OVERVIEW = (13.8, 7.6)
MIN_REL_GAP_PCT = float(os.getenv("E1Y_MIN_REL_GAP_PCT", "20.0"))

BASE_VARIANT = "baseline"
GATE_VARIANT = "comp_advantage"

BUCKET_SPECS = [
    ("e11y", "(0.10, 0.18]", 0.10, 0.18),
    ("e12y", "(0.18, 0.32]", 0.18, 0.32),
    ("e13y", "(0.32, 0.56]", 0.32, 0.56),
    ("e14y", "(0.56, 1.00]", 0.56, 1.00),
    ("e15y", "(1.00, 1.78]", 1.00, 1.78),
    ("e16y", "(1.78, 3.16]", 1.78, 3.16),
    ("e17y", "(3.16, 5.62]", 3.16, 5.62),
    ("e18y", "(5.62, 10.00]", 5.62, 10.00),
]


def parse_args():
    parser = argparse.ArgumentParser(
        description="Aggregate e11y-e18y into one y-condition overview figure."
    )
    parser.add_argument(
        "--output-dir",
        help="Optional output directory. Default: experiments/four/e1y/analysis_<timestamp>",
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



def calc_relative_gap_pct(a, b):
    if pd.isna(a) or pd.isna(b):
        return np.nan
    avg = (a + b) / 2.0
    if avg == 0:
        return np.nan
    return abs(a - b) / avg * 100.0



def find_latest_run_dir(bucket_dir, raw_csv_name):
    candidates = []
    for name in os.listdir(bucket_dir):
        path = os.path.join(bucket_dir, name)
        if (
            os.path.isdir(path)
            and name.startswith("run_")
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
    ]
    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

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



def filter_bucket_rows(ok, lower, upper):
    scenario_ok = ok.dropna(subset=["ccr_data", "idr_image", "nccr_total"]).copy()
    if scenario_ok.empty:
        raise RuntimeError("No ok rows have complete CCR/IDR/NCCR metrics")

    scenario_ok["ccr_idr_rel_gap_pct"] = [
        calc_relative_gap_pct(a, b)
        for a, b in zip(scenario_ok["ccr_data"], scenario_ok["idr_image"])
    ]
    scenario_ok["idr_minus_ccr"] = scenario_ok["idr_image"] - scenario_ok["ccr_data"]
    scenario_ok["scenario_match"] = (
        (scenario_ok["nccr_total"] > lower)
        & (scenario_ok["nccr_total"] <= upper)
        & (scenario_ok["ccr_data"] < scenario_ok["idr_image"])
        & (scenario_ok["ccr_idr_rel_gap_pct"] >= MIN_REL_GAP_PCT)
    )
    filtered = scenario_ok[scenario_ok["scenario_match"]].copy()
    if filtered.empty:
        raise RuntimeError(
            "No ok rows satisfy the scenario rule: "
            f"{lower:.2f} < NCCR_total <= {upper:.2f} "
            f"AND CCR_data < IDR_image "
            f"AND relative CCR/IDR gap >= {MIN_REL_GAP_PCT:.2f}%"
        )
    validate_filtered_rows(filtered, lower, upper)
    return filtered



def validate_filtered_rows(filtered, lower, upper):
    """Defensive guard for y-condition aggregation.

    The overview script must never summarize rows outside:
      lower < NCCR_total <= upper
      AND CCR_data < IDR_image
      AND relative CCR/IDR gap >= MIN_REL_GAP_PCT
    """
    bad_nccr = filtered[
        ~((filtered["nccr_total"] > lower) & (filtered["nccr_total"] <= upper))
    ]
    if not bad_nccr.empty:
        raise RuntimeError(
            "Filtered rows contain out-of-bucket NCCR values, "
            "which should never happen in e1y aggregation"
        )

    bad_order = filtered[filtered["ccr_data"] >= filtered["idr_image"]]
    if not bad_order.empty:
        raise RuntimeError(
            "Filtered rows violate the y-condition CCR_data < IDR_image"
        )

    bad_gap = filtered[filtered["ccr_idr_rel_gap_pct"] < MIN_REL_GAP_PCT]
    if not bad_gap.empty:
        raise RuntimeError(
            "Filtered rows violate the y-condition relative CCR/IDR gap "
            f">= {MIN_REL_GAP_PCT:.2f}%"
        )



def expected_variants_from_manifest(manifest, df):
    variants = manifest.get("variants") or []
    labels = []
    for variant in variants:
        label = str(variant.get("label", "")).strip()
        if label:
            labels.append(label)

    if not labels:
        labels = sorted(str(value) for value in df["variant"].dropna().unique())
        if BASE_VARIANT in labels:
            labels.remove(BASE_VARIANT)
            labels.insert(0, BASE_VARIANT)

    if BASE_VARIANT not in labels:
        raise RuntimeError("The baseline variant is required")
    if GATE_VARIANT not in labels:
        raise RuntimeError(
            f"The {GATE_VARIANT} variant is required for e1y aggregation"
        )
    if len(labels) != 2:
        raise RuntimeError(
            "e1y aggregation expects exactly two variants: "
            f"{BASE_VARIANT} and {GATE_VARIANT}. Observed: {labels}"
        )
    return labels



def filter_complete_seeds(filtered, expected_variants):
    report_rows = []
    complete_seeds = []

    for seed, group in filtered.groupby("seed", sort=True):
        observed_set = set(group["variant"].dropna().astype(str))
        missing = [label for label in expected_variants if label not in observed_set]
        is_complete = len(missing) == 0
        if is_complete:
            complete_seeds.append(seed)
        report_rows.append(
            {
                "seed": int(seed),
                "is_complete": is_complete,
                "completed_variants": ",".join(
                    label for label in expected_variants if label in observed_set
                ),
                "missing_variants": ",".join(missing),
            }
        )

    if not complete_seeds:
        raise RuntimeError(
            "No complete seeds found after scenario filtering. "
            f"Expected variants: {expected_variants}"
        )

    complete_df = filtered[filtered["seed"].isin(complete_seeds)].copy()
    report_df = pd.DataFrame(report_rows)
    return complete_df, report_df



def build_bucket_summary(
    complete_df,
    bucket_key,
    bucket_label,
    result_dir,
    planned_seed_count,
    recorded_seed_count,
    ok_seed_count,
    scenario_valid_seed_count,
    complete_seed_count,
):
    baseline = (
        complete_df[complete_df["variant"] == BASE_VARIANT]
        .sort_values(["seed", "time_sec"])
        .drop_duplicates("seed")
        .copy()
    )
    gate = (
        complete_df[complete_df["variant"] == GATE_VARIANT]
        .sort_values(["seed", "time_sec"])
        .drop_duplicates("seed")
        .copy()
    )

    paired_seeds = sorted(set(baseline["seed"]) & set(gate["seed"]))
    if not paired_seeds:
        raise RuntimeError("No paired seeds remain after baseline/gate alignment")

    baseline = baseline[baseline["seed"].isin(paired_seeds)].copy()
    gate = gate[gate["seed"].isin(paired_seeds)].copy()

    merged = baseline[["seed", "nheft_makespan", "nheft_vcpus"]].merge(
        gate[["seed", "nheft_makespan", "nheft_vcpus"]],
        on="seed",
        suffixes=("_baseline", "_gate"),
        how="inner",
    )
    if merged.empty:
        raise RuntimeError("No seed pairs remain after merge")

    makespan_change_gate_vs_nheft = safe_percent(
        merged["nheft_makespan_gate"] - merged["nheft_makespan_baseline"],
        merged["nheft_makespan_baseline"],
    )
    vcpu_reduction_gate_vs_nheft = safe_percent(
        merged["nheft_vcpus_baseline"] - merged["nheft_vcpus_gate"],
        merged["nheft_vcpus_baseline"],
    )
    gain_nheft_over_dheft = safe_percent(
        baseline["dheft_makespan"] - baseline["nheft_makespan"],
        baseline["dheft_makespan"],
    )
    gain_gheft_over_dheft = safe_percent(
        gate["dheft_makespan"] - gate["nheft_makespan"],
        gate["dheft_makespan"],
    )

    return {
        "bucket_key": bucket_key,
        "bucket_label": bucket_label,
        "result_dir": result_dir,
        "planned_seed_count": planned_seed_count,
        "recorded_seed_count": recorded_seed_count,
        "ok_seed_count": ok_seed_count,
        "scenario_valid_seed_count": scenario_valid_seed_count,
        "complete_seed_count": complete_seed_count,
        "scenario_valid_rate_vs_recorded_pct": safe_ratio_pct(
            scenario_valid_seed_count, recorded_seed_count
        ),
        "complete_rate_vs_recorded_pct": safe_ratio_pct(
            complete_seed_count, recorded_seed_count
        ),
        "complete_rate_vs_valid_pct": safe_ratio_pct(
            complete_seed_count, scenario_valid_seed_count
        ),
        "paired_seeds": len(paired_seeds),
        "matched_nccr_min": float(complete_df["nccr_total"].min()),
        "matched_nccr_max": float(complete_df["nccr_total"].max()),
        "matched_rel_gap_min": float(complete_df["ccr_idr_rel_gap_pct"].min()),
        "matched_rel_gap_max": float(complete_df["ccr_idr_rel_gap_pct"].max()),
        "matched_idr_minus_ccr_min": float(complete_df["idr_minus_ccr"].min()),
        "dheft_makespan_mean": float(baseline["dheft_makespan"].mean()),
        "dheft_vcpus_mean": float(baseline["dheft_vcpus"].mean()),
        "nheft_makespan_mean": float(baseline["nheft_makespan"].mean()),
        "nheft_vcpus_mean": float(baseline["nheft_vcpus"].mean()),
        "gheft_makespan_mean": float(gate["nheft_makespan"].mean()),
        "gheft_vcpus_mean": float(gate["nheft_vcpus"].mean()),
        "gate_makespan_change_vs_nheft_pct_mean": float(
            np.nanmean(makespan_change_gate_vs_nheft)
        ),
        "gate_vcpu_reduction_vs_nheft_pct_mean": float(
            np.nanmean(vcpu_reduction_gate_vs_nheft)
        ),
        "nheft_gain_over_dheft_pct_mean": float(np.nanmean(gain_nheft_over_dheft)),
        "gheft_gain_over_dheft_pct_mean": float(np.nanmean(gain_gheft_over_dheft)),
    }



def annotate_line_points(ax, x_values, y_values, color, fmt):
    for x, y in zip(x_values, y_values):
        ax.annotate(
            fmt.format(y),
            (x, y),
            textcoords="offset points",
            xytext=(0, 8),
            ha="center",
            va="bottom",
            fontsize=9,
            color=color,
        )



def save_overview_plot(summary_df, output_dir):
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
    bars_d = ax_v.bar(
        x - bar_width,
        vcpu_dheft,
        width=bar_width,
        color=GREY,
        edgecolor=DARK,
        linewidth=0.8,
        alpha=0.65,
        label="DHEFT mean used vCPUs",
        zorder=1,
    )
    bars_n = ax_v.bar(
        x,
        vcpu_nheft,
        width=bar_width,
        color=WASEDA_RED,
        edgecolor=WASEDA_RED,
        linewidth=0.8,
        alpha=0.25,
        label="NHEFT mean used vCPUs",
        zorder=1,
    )
    bars_g = ax_v.bar(
        x + bar_width,
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
        markersize=6,
        linewidth=2.4,
        label="DHEFT mean makespan",
        zorder=4,
    )
    line_n = ax_m.plot(
        x,
        makespan_nheft,
        color=WASEDA_RED,
        marker="o",
        markersize=6,
        linewidth=2.6,
        label="NHEFT mean makespan",
        zorder=4,
    )
    line_g = ax_m.plot(
        x,
        makespan_gheft,
        color=GREEN,
        marker="o",
        markersize=6,
        linewidth=2.6,
        label="GHEFT mean makespan",
        zorder=4,
    )

    ax_m.set_xlabel("NCCR bucket")
    ax_m.set_ylabel("Mean makespan", color=DARK)
    ax_v.set_ylabel("Mean used vCPUs", color=DARK)
    ax_m.set_xticks(x)
    ax_m.set_xticklabels(bucket_labels, rotation=12, ha="right")
    ax_m.tick_params(axis="y", labelcolor=DARK)
    ax_v.tick_params(axis="y", labelcolor=DARK)
    ax_m.set_ylim(
        0,
        finite_max(
            np.concatenate([makespan_dheft, makespan_nheft, makespan_gheft])
        )
        * 1.20,
    )
    ax_v.set_ylim(
        0,
        finite_max(np.concatenate([vcpu_dheft, vcpu_nheft, vcpu_gheft])) * 1.25,
    )
    ax_m.grid(axis="y", linestyle="--", linewidth=0.6, alpha=0.35)

    annotate_line_points(ax_m, x, makespan_dheft, DARK, "{:.2f}")
    annotate_line_points(ax_m, x, makespan_nheft, WASEDA_RED, "{:.2f}")
    annotate_line_points(ax_m, x, makespan_gheft, GREEN, "{:.2f}")

    handles = [line_d[0], line_n[0], line_g[0], bars_d, bars_n, bars_g]
    labels = [handle.get_label() for handle in handles]
    ax_m.legend(handles, labels, loc="upper left", fontsize=9, ncol=2)
    ax_m.set_title("E1Y overview: makespan lines and used-vCPU bars across 8 buckets")

    fig.tight_layout()
    output_path = os.path.join(output_dir, "e1y_makespan_vcpu_overview.png")
    fig.savefig(output_path, dpi=PLOT_DPI)
    plt.close(fig)
    return output_path



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



def write_seed_coverage_md(output_dir, summary_df):
    output_path = os.path.join(output_dir, "e1y_seed_coverage_report.md")
    lines = [
        "# E1Y Seed Coverage Report",
        "",
        "## Definitions",
        "- Planned seeds: target seed count written in `run_manifest.json` (if available).",
        "- Recorded seeds: unique seeds that appear in the raw CSV for that bucket.",
        "- OK seeds: recorded seeds that contain at least one `status = ok` row.",
        (
            "- Scenario-valid seeds: OK seeds that satisfy the current bucket rule "
            f"and the y-condition (`CCR_data < IDR_image` and relative CCR/IDR gap >= {MIN_REL_GAP_PCT:.1f}%)."
        ),
        (
            "- Complete valid seeds: scenario-valid seeds that contain both expected "
            "variants (`baseline` and `comp_advantage`) and are actually used in the final aggregation."
        ),
        "",
        "## Coverage Table",
        "",
        "| Bucket | Planned seeds | Recorded seeds | OK seeds | Scenario-valid seeds | Complete valid seeds | Valid / Recorded | Used / Valid |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]

    for _, row in summary_df.iterrows():
        lines.append(
            "| {bucket} | {planned} | {recorded} | {ok} | {valid} | {complete} | {valid_rate} | {used_rate} |".format(
                bucket=row["bucket_label"],
                planned=format_md_int(row.get("planned_seed_count")),
                recorded=format_md_int(row.get("recorded_seed_count")),
                ok=format_md_int(row.get("ok_seed_count")),
                valid=format_md_int(row.get("scenario_valid_seed_count")),
                complete=format_md_int(row.get("complete_seed_count")),
                valid_rate=format_md_pct(row.get("scenario_valid_rate_vs_recorded_pct")),
                used_rate=format_md_pct(row.get("complete_rate_vs_valid_pct")),
            )
        )

    low_coverage = summary_df[summary_df["complete_seed_count"] < 100]
    if not low_coverage.empty:
        lines.extend(
            [
                "",
                "## Low-Coverage Buckets",
                "",
                "The following buckets have fewer than 100 complete valid seeds:",
                "",
            ]
        )
        for _, row in low_coverage.iterrows():
            lines.append(
                f"- {row['bucket_label']}: complete valid seeds = {int(row['complete_seed_count'])}"
            )

    with open(output_path, "w", encoding="utf-8") as target:
        target.write("\n".join(lines) + "\n")
    return output_path



def write_manifest(output_dir, summary_df):
    payload = {
        "analysis": "E1Y cross-bucket aggregation",
        "timestamp": datetime.now().strftime("%Y%m%d_%H%M%S"),
        "bucket_count": int(len(summary_df)),
        "min_rel_gap_pct": MIN_REL_GAP_PCT,
        "note": (
            "Each bucket uses only complete seeds after y-condition filtering. "
            "GHEFT corresponds to the comp_advantage variant."
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
    output_dir = args.output_dir or os.path.join(THIS_DIR, f"analysis_{timestamp}")
    os.makedirs(output_dir, exist_ok=True)

    summary_rows = []
    seed_report_rows = []

    for bucket_key, bucket_label, lower, upper in BUCKET_SPECS:
        bucket_dir = os.path.join(FOUR_DIR, bucket_key)
        raw_csv_name = f"{bucket_key}_results.csv"
        latest_run_dir = find_latest_run_dir(bucket_dir, raw_csv_name)
        if latest_run_dir is None:
            raise RuntimeError(
                f"No run_* directory with {raw_csv_name} found under {bucket_dir}"
            )

        manifest = read_manifest(latest_run_dir)
        raw_df = load_raw_csv(latest_run_dir, raw_csv_name)
        ok_df = filter_ok_rows(raw_df)
        bucket_df = filter_bucket_rows(ok_df, lower, upper)
        expected_variants = expected_variants_from_manifest(manifest, bucket_df)
        complete_df, seed_report_df = filter_complete_seeds(bucket_df, expected_variants)

        planned_seed_count = manifest.get("num_seeds")
        recorded_seed_count = unique_seed_count(raw_df)
        ok_seed_count = unique_seed_count(ok_df)
        scenario_valid_seed_count = unique_seed_count(bucket_df)
        complete_seed_count = unique_seed_count(complete_df)

        summary_rows.append(
            build_bucket_summary(
                complete_df,
                bucket_key=bucket_key,
                bucket_label=bucket_label,
                result_dir=latest_run_dir,
                planned_seed_count=planned_seed_count,
                recorded_seed_count=recorded_seed_count,
                ok_seed_count=ok_seed_count,
                scenario_valid_seed_count=scenario_valid_seed_count,
                complete_seed_count=complete_seed_count,
            )
        )

        seed_report_df.insert(0, "bucket_key", bucket_key)
        seed_report_rows.append(seed_report_df)

    summary_df = pd.DataFrame(summary_rows)
    seed_report_df = pd.concat(seed_report_rows, ignore_index=True)

    summary_csv = os.path.join(output_dir, "e1y_bucket_summary.csv")
    seed_report_csv = os.path.join(output_dir, "e1y_complete_seed_report.csv")
    summary_df.to_csv(summary_csv, index=False)
    seed_report_df.to_csv(seed_report_csv, index=False)
    plot_path = save_overview_plot(summary_df, output_dir)
    coverage_md_path = write_seed_coverage_md(output_dir, summary_df)
    write_manifest(output_dir, summary_df)

    print("E1Y cross-bucket aggregation complete.")
    print(f"Output dir: {relpath(output_dir)}")
    print(f"Summary CSV: {relpath(summary_csv)}")
    print(f"Seed report: {relpath(seed_report_csv)}")
    print(f"Coverage MD: {relpath(coverage_md_path)}")
    print(f"Plot: {relpath(plot_path)}")


if __name__ == "__main__":
    main()
