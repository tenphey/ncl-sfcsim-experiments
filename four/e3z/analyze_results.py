#!/usr/bin/env python3
"""Aggregate all E3Z bucket results into one cross-bucket overview.

This script combines the latest raw results of:

  baseline side: e01z, e02z, e03z, e04z, e05z, e06z, e07z, e08z
  GHEFT side:    e31z, e32z, e33z, e34z, e35z, e36z, e37z, e38z

Each bucket keeps the original z-condition filtering:

  NCCR bucket AND CCR_data > IDR_image AND relative CCR/IDR gap >= min_rel_gap_pct

Only paired seeds are used in the final aggregation.
A seed is counted only when:

  - the baseline side has a valid `baseline` row
  - the GHEFT side has a valid `irt_only` row
  - both rows satisfy the same bucket + z-condition

Usage from the simulator repository root:

  experiments/.venv/bin/python experiments/four/e3z/analyze_results.py
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
MIN_REL_GAP_PCT = float(os.getenv("E3Z_MIN_REL_GAP_PCT", "20.0"))

BASE_VARIANT = "baseline"
GATE_VARIANT = "irt_only"

BUCKET_SPECS = [
    ("(0.10, 0.18]", 0.10, 0.18, "e01z", "e31z"),
    ("(0.18, 0.32]", 0.18, 0.32, "e02z", "e32z"),
    ("(0.32, 0.56]", 0.32, 0.56, "e03z", "e33z"),
    ("(0.56, 1.00]", 0.56, 1.00, "e04z", "e34z"),
    ("(1.00, 1.78]", 1.00, 1.78, "e05z", "e35z"),
    ("(1.78, 3.16]", 1.78, 3.16, "e06z", "e36z"),
    ("(3.16, 5.62]", 3.16, 5.62, "e07z", "e37z"),
    ("(5.62, 10.00]", 5.62, 10.00, "e08z", "e38z"),
]


def parse_args():
    parser = argparse.ArgumentParser(
        description="Aggregate baseline e01z-e08z and GHEFT e31z-e38z into one z-condition overview figure."
    )
    parser.add_argument(
        "--output-dir",
        help="Optional output directory. Default: experiments/four/e3z/analysis_<timestamp>",
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
    if not os.path.isdir(bucket_dir):
        return None

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


def filter_bucket_rows(ok, lower, upper):
    scenario_ok = ok.dropna(subset=["ccr_data", "idr_image", "nccr_total"]).copy()
    if scenario_ok.empty:
        raise RuntimeError("No ok rows have complete CCR/IDR/NCCR metrics")

    scenario_ok["ccr_idr_rel_gap_pct"] = [
        calc_relative_gap_pct(a, b)
        for a, b in zip(scenario_ok["ccr_data"], scenario_ok["idr_image"])
    ]
    scenario_ok["ccr_minus_idr"] = scenario_ok["ccr_data"] - scenario_ok["idr_image"]
    scenario_ok["scenario_match"] = (
        (scenario_ok["nccr_total"] > lower)
        & (scenario_ok["nccr_total"] <= upper)
        & (scenario_ok["ccr_data"] > scenario_ok["idr_image"])
        & (scenario_ok["ccr_idr_rel_gap_pct"] >= MIN_REL_GAP_PCT)
    )
    filtered = scenario_ok[scenario_ok["scenario_match"]].copy()
    if filtered.empty:
        raise RuntimeError(
            "No ok rows satisfy the scenario rule: "
            f"{lower:.2f} < NCCR_total <= {upper:.2f} "
            f"AND CCR_data > IDR_image "
            f"AND relative CCR/IDR gap >= {MIN_REL_GAP_PCT:.2f}%"
        )
    validate_filtered_rows(filtered, lower, upper)
    return filtered


def validate_filtered_rows(filtered, lower, upper):
    bad_nccr = filtered[
        ~((filtered["nccr_total"] > lower) & (filtered["nccr_total"] <= upper))
    ]
    if not bad_nccr.empty:
        raise RuntimeError(
            "Filtered rows contain out-of-bucket NCCR values, "
            "which should never happen in e3z aggregation"
        )

    bad_direction = filtered[filtered["ccr_data"] <= filtered["idr_image"]]
    if not bad_direction.empty:
        raise RuntimeError(
            "Filtered rows violate the z-condition CCR_data > IDR_image"
        )

    bad_gap = filtered[filtered["ccr_idr_rel_gap_pct"] < MIN_REL_GAP_PCT]
    if not bad_gap.empty:
        raise RuntimeError(
            "Filtered rows violate the z-condition relative gap threshold "
            f">= {MIN_REL_GAP_PCT:.2f}%"
        )


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
    gain_nheft_over_dheft = safe_percent(
        merged["dheft_makespan"] - merged["nheft_makespan_baseline"],
        merged["dheft_makespan"],
    )
    gain_gheft_over_dheft = safe_percent(
        merged["dheft_makespan"] - merged["nheft_makespan_gate"],
        merged["dheft_makespan"],
    )

    baseline_planned = baseline_manifest.get("num_seeds")
    gate_planned = gate_manifest.get("num_seeds")
    baseline_recorded = unique_seed_count(baseline_raw_df)
    gate_recorded = unique_seed_count(gate_raw_df)
    baseline_ok = unique_seed_count(baseline_ok_df)
    gate_ok = unique_seed_count(gate_ok_df)
    baseline_valid = unique_seed_count(baseline_bucket_df)
    gate_valid = unique_seed_count(gate_bucket_df)

    return {
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
        "matched_rel_gap_pct_max": float(
            max(
                baseline["ccr_idr_rel_gap_pct"].max(),
                gate["ccr_idr_rel_gap_pct"].max(),
            )
        ),
        "dheft_makespan_mean": float(merged["dheft_makespan"].mean()),
        "dheft_vcpus_mean": float(merged["dheft_vcpus"].mean()),
        "nheft_makespan_mean": float(merged["nheft_makespan_baseline"].mean()),
        "nheft_vcpus_mean": float(merged["nheft_vcpus_baseline"].mean()),
        "gheft_makespan_mean": float(merged["nheft_makespan_gate"].mean()),
        "gheft_vcpus_mean": float(merged["nheft_vcpus_gate"].mean()),
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

    handles = [
        line_d[0],
        line_n[0],
        line_g[0],
        bars_d,
        bars_n,
        bars_g,
    ]
    labels = [handle.get_label() for handle in handles]
    ax_m.legend(handles, labels, loc="upper left", fontsize=9, ncol=2)
    ax_m.set_title("E3Z overview: baseline vs IRT-only GHEFT across 8 buckets")

    fig.tight_layout()
    output_path = os.path.join(output_dir, "e3z_makespan_vcpu_overview.png")
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
    output_path = os.path.join(output_dir, "e3z_seed_coverage_report.md")
    lines = [
        "# E3Z Seed Coverage Report",
        "",
        "## Definitions",
        "- Baseline side: shared baseline results from `e01z` to `e08z`.",
        "- GHEFT side: IRT-only gate results from `e31z` to `e38z`.",
        "- Recorded seeds: unique seeds that appear in the raw CSV.",
        "- OK seeds: recorded seeds that contain at least one `status = ok` row.",
        (
            "- Valid seeds: OK seeds that satisfy the current bucket rule "
            f"and the z-condition (`CCR_data > IDR_image` and relative gap >= {MIN_REL_GAP_PCT:.2f}%)."
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
        "analysis": "E3Z cross-bucket aggregation",
        "timestamp": datetime.now().strftime("%Y%m%d_%H%M%S"),
        "bucket_count": int(len(summary_df)),
        "min_rel_gap_pct": MIN_REL_GAP_PCT,
        "gate_variant": GATE_VARIANT,
        "note": (
            "Each bucket uses only paired seeds after z-condition filtering. "
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
    output_dir = args.output_dir or os.path.join(THIS_DIR, f"analysis_{timestamp}")
    os.makedirs(output_dir, exist_ok=True)

    summary_rows = []

    for bucket_label, lower, upper, baseline_key, gate_key in BUCKET_SPECS:
        baseline_dir = os.path.join(FOUR_DIR, baseline_key)
        gate_dir = os.path.join(FOUR_DIR, gate_key)
        baseline_csv_name = f"{baseline_key}_results.csv"
        gate_csv_name = f"{gate_key}_results.csv"

        baseline_run_dir = find_latest_run_dir(baseline_dir, baseline_csv_name)
        gate_run_dir = find_latest_run_dir(gate_dir, gate_csv_name)
        if baseline_run_dir is None:
            raise RuntimeError(
                f"No run_* directory with {baseline_csv_name} found under {baseline_dir}"
            )
        if gate_run_dir is None:
            raise RuntimeError(
                f"No run_* directory with {gate_csv_name} found under {gate_dir}"
            )

        baseline_manifest = read_manifest(baseline_run_dir)
        gate_manifest = read_manifest(gate_run_dir)
        baseline_raw_df = load_raw_csv(baseline_run_dir, baseline_csv_name)
        gate_raw_df = load_raw_csv(gate_run_dir, gate_csv_name)
        baseline_ok_df = filter_ok_rows(baseline_raw_df)
        gate_ok_df = filter_ok_rows(gate_raw_df)
        baseline_bucket_df = filter_bucket_rows(baseline_ok_df, lower, upper)
        gate_bucket_df = filter_bucket_rows(gate_ok_df, lower, upper)

        require_variant(baseline_bucket_df, BASE_VARIANT, baseline_key)
        require_variant(gate_bucket_df, GATE_VARIANT, gate_key)

        summary_rows.append(
            build_bucket_summary(
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
        )

    summary_df = pd.DataFrame(summary_rows)
    summary_csv = os.path.join(output_dir, "e3z_bucket_summary.csv")
    summary_df.to_csv(summary_csv, index=False)
    plot_path = save_overview_plot(summary_df, output_dir)
    coverage_md_path = write_seed_coverage_md(output_dir, summary_df)
    write_manifest(output_dir, summary_df)

    print("E3Z cross-bucket aggregation complete.")
    print(f"Output dir: {relpath(output_dir)}")
    print(f"Summary CSV: {relpath(summary_csv)}")
    print(f"Coverage MD: {relpath(coverage_md_path)}")
    print(f"Plot: {relpath(plot_path)}")


if __name__ == "__main__":
    main()
