#!/usr/bin/env python3
"""
Analyze E16 results: DHEFT vs NHEFT under different total VNF counts.

Usage:
  python3 analyze_results.py <result_folder>
  python3 analyze_results.py run_160_20260530_123000
"""

import os
import sys
import json
import glob
import shutil

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy import stats

THIS_DIR = os.path.dirname(os.path.abspath(__file__))


def resolve_result_dir(arg):
    if os.path.isdir(arg):
        return arg
    candidate = os.path.join(THIS_DIR, arg)
    if os.path.isdir(candidate):
        return candidate
    try:
        matches = [
            d for d in os.listdir(THIS_DIR)
            if os.path.isdir(os.path.join(THIS_DIR, d)) and d.startswith(arg)
        ]
        if len(matches) == 1:
            return os.path.join(THIS_DIR, matches[0])
        if len(matches) > 1:
            print(f"Multiple matching folders for '{arg}':")
            for m in matches:
                print("  ", m)
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
            f"{height:.1f}",
            ha="center",
            va="bottom",
            fontsize=10,
            fontweight="bold",
        )


def draw_table_image(display_df, title, out_path):
    fig_height = max(3.8, 0.55 * (len(display_df) + 2))
    fig, ax = plt.subplots(figsize=(15, fig_height))
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


def resolve_log_path(result_dir, seed, effective_total_vnf_num, multiple_sfc_num):
    """Resolve per-run log path under logs/ (supports both new and legacy patterns)."""
    logs_dir = os.path.join(result_dir, "logs")
    seed_i = int(seed)
    total_i = int(effective_total_vnf_num)
    msfc_i = int(multiple_sfc_num)

    # Preferred canonical pattern.
    new_name = os.path.join(logs_dir, f"run_seed_{seed_i}_total_{total_i}_msfc_{msfc_i}.log")
    if os.path.exists(new_name):
        return new_name

    # Legacy pattern contains master seed prefix.
    legacy_pattern = os.path.join(logs_dir, f"run_*_seed_{seed_i}_total_{total_i}_msfc_{msfc_i}.log")
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
        print("Usage: analyze_results.py <result_folder>")
        raise SystemExit(1)

    result_dir = resolve_result_dir(sys.argv[1])
    if not result_dir:
        print(f"Result folder not found: {sys.argv[1]}")
        raise SystemExit(1)

    moved_logs = normalize_log_layout(result_dir)
    if moved_logs > 0:
        print(f"Moved {moved_logs} legacy log files into: {os.path.join(result_dir, 'logs')}")

    csv_path = os.path.join(result_dir, "grid_e16_results.csv")
    if not os.path.exists(csv_path):
        print(f"CSV not found: {csv_path}")
        raise SystemExit(1)

    df = pd.read_csv(csv_path)
    df = df[(df["HEFT"] > 0) & (df["DHEFT"] > 0) & (df["NHEFT"] > 0)]
    df["gain_N_over_D"] = (df["DHEFT"] - df["NHEFT"]) / df["DHEFT"] * 100

    grouped = df.groupby("effective_total_vnf_num")
    summary_rows = []

    for total_vnf_num, group in grouped:
        n_runs = len(group)
        dheft_mean = group["DHEFT"].mean()
        dheft_std = group["DHEFT"].std()
        nheft_mean = group["NHEFT"].mean()
        nheft_std = group["NHEFT"].std()
        gain_mean = group["gain_N_over_D"].mean()
        gain_median = group["gain_N_over_D"].median()
        gain_trimmed = stats.trim_mean(group["gain_N_over_D"], 0.1)
        wins = (group["NHEFT"] < group["DHEFT"]).sum()

        if n_runs >= 2:
            _, p_val = stats.ttest_rel(group["DHEFT"], group["NHEFT"])
            p_val = float(p_val)
            try:
                _, w_pval = stats.wilcoxon(group["DHEFT"], group["NHEFT"])
                w_pval = float(w_pval)
            except Exception:
                w_pval = np.nan
        else:
            p_val = np.nan
            w_pval = np.nan

        summary_rows.append(
            {
                "effective_total_vnf_num": int(total_vnf_num),
                "DHEFT_mean": dheft_mean,
                "DHEFT_std": dheft_std,
                "NHEFT_mean": nheft_mean,
                "NHEFT_std": nheft_std,
                "gain_N_over_D_mean": gain_mean,
                "gain_N_over_D_median": gain_median,
                "gain_N_over_D_trimmed": gain_trimmed,
                "wins_count": int(wins),
                "p_value": p_val,
                "wilcoxon_p": w_pval,
                "n_runs": n_runs,
            }
        )

    summary_df = pd.DataFrame(summary_rows).sort_values("effective_total_vnf_num")
    summary_csv = os.path.join(result_dir, "grid_e16_summary.csv")
    summary_df.to_csv(summary_csv, index=False)

    # Build an effective_total_vnf_num -> {seed -> execution details} JSON where NHEFT loses to DHEFT.
    if "seed" not in df.columns:
        raise SystemExit("Missing required column: seed")
    loss_details_by_total_vnf = {}
    for total_vnf_num in sorted(df["effective_total_vnf_num"].unique()):
        group = df[df["effective_total_vnf_num"] == total_vnf_num]
        loss_group = group[group["NHEFT"] > group["DHEFT"]].sort_values("seed")
        seed_map = {}
        for _, row in loss_group.iterrows():
            seed_key = str(int(row["seed"]))
            dheft_val = float(row["DHEFT"])
            nheft_val = float(row["NHEFT"])
            if "multiple_sfc_num" in row.index and not pd.isna(row["multiple_sfc_num"]):
                msfc_for_log = int(row["multiple_sfc_num"])
            else:
                msfc_for_log = 0
            log_path = resolve_log_path(
                result_dir,
                row["seed"],
                row["effective_total_vnf_num"],
                msfc_for_log,
            )
            log_meta = read_log_meta(log_path)
            seed_map[seed_key] = {
                "HEFT": round(float(row["HEFT"]), 6),
                "DHEFT": round(dheft_val, 6),
                "NHEFT": round(nheft_val, 6),
                "gain_N_over_D_percent": round(float(row["gain_N_over_D"]), 6),
                "nheft_minus_dheft": round(nheft_val - dheft_val, 6),
                "effective_total_vnf_num": int(row["effective_total_vnf_num"]),
                "multiple_sfc_num": int(row["multiple_sfc_num"]) if "multiple_sfc_num" in row.index else None,
                "per_sfc_vnf_num": int(row["per_sfc_vnf_num"]) if "per_sfc_vnf_num" in row.index else None,
                "vnf_type_min": int(row["vnf_type_min"]) if "vnf_type_min" in row.index else None,
                "vnf_type_max": int(row["vnf_type_max"]) if "vnf_type_max" in row.index else None,
                "vnf_image_size_min": int(row["vnf_image_size_min"]) if "vnf_image_size_min" in row.index else None,
                "vnf_image_size_max": int(row["vnf_image_size_max"]) if "vnf_image_size_max" in row.index else None,
                "repository_bw": int(row["repository_bw"]) if "repository_bw" in row.index else None,
                "datacenter_externalbw_min": int(row["datacenter_externalbw_min"]) if "datacenter_externalbw_min" in row.index else None,
                "datacenter_externalbw_max": int(row["datacenter_externalbw_max"]) if "datacenter_externalbw_max" in row.index else None,
                "host_bw_min": int(row["host_bw_min"]) if "host_bw_min" in row.index else None,
                "host_bw_max": int(row["host_bw_max"]) if "host_bw_max" in row.index else None,
                "time_sec": round(float(row["time_sec"]), 6) if "time_sec" in row.index else None,
                "log_file": os.path.relpath(log_meta["log_file"], result_dir) if log_meta["log_file"] else None,
                "log_exists": log_meta["log_exists"],
                "log_readable": log_meta["log_readable"],
                "log_size_bytes": log_meta["log_size_bytes"],
            }
        loss_details_by_total_vnf[str(int(total_vnf_num))] = seed_map

    loss_json_path = os.path.join(result_dir, "e16_nheft_loss_seeds_by_effective_total_vnf_num.json")
    with open(loss_json_path, "w") as f:
        json.dump(loss_details_by_total_vnf, f, indent=2)

    print(f"\nSummary CSV: {summary_csv}")
    print(f"Loss-seeds JSON saved: {loss_json_path}")
    print("\n=== E16 Results by effective_total_vnf_num ===")
    console_df = summary_df[
        [
            "effective_total_vnf_num",
            "DHEFT_mean",
            "NHEFT_mean",
            "gain_N_over_D_median",
            "gain_N_over_D_mean",
            "wins_count",
            "p_value",
            "n_runs",
        ]
    ].copy()
    console_df["wins_count"] = console_df.apply(
        lambda row: f"{int(row['wins_count'])}/{int(row['n_runs'])}",
        axis=1,
    )
    display_df = console_df.drop(columns=["n_runs"]).copy()
    display_df["effective_total_vnf_num"] = display_df["effective_total_vnf_num"].map(lambda x: f"{int(x)}")
    for col in ["DHEFT_mean", "NHEFT_mean", "gain_N_over_D_median", "gain_N_over_D_mean"]:
        display_df[col] = display_df[col].map(lambda x: f"{float(x):.6f}")
    display_df["p_value"] = display_df["p_value"].map(lambda x: "" if pd.isna(x) else f"{float(x):.6e}")
    print(console_df.drop(columns=["n_runs"]).to_string(index=False))
    table_path = os.path.join(result_dir, "e16_summary_table.png")
    draw_table_image(display_df, "E16 Results by effective_total_vnf_num", table_path)
    print(f"Summary table image saved: {table_path}")

    # Plot 1: gain trend
    fig, ax = plt.subplots(figsize=(12, 7))

    x = summary_df["effective_total_vnf_num"].values
    gains_mean = summary_df["gain_N_over_D_mean"].values
    gains_median = summary_df["gain_N_over_D_median"].values
    gains_trimmed = summary_df["gain_N_over_D_trimmed"].values

    ax.plot(
        x,
        gains_median,
        marker="o",
        markersize=10,
        linewidth=2.5,
        label="NHEFT gain % (median, robust)",
        color="#06A77D",
        linestyle="-",
    )
    ax.plot(
        x,
        gains_trimmed,
        marker="s",
        markersize=8,
        linewidth=2,
        label="NHEFT gain % (trimmed mean 10%-90%)",
        color="#A23B72",
        linestyle="--",
    )
    ax.plot(
        x,
        gains_mean,
        marker="^",
        markersize=8,
        linewidth=1.5,
        label="NHEFT gain % (arithmetic mean)",
        color="#F18F01",
        linestyle=":",
    )
    ax.axhline(y=0, color="red", linestyle="--", alpha=0.5, linewidth=1)

    ax.set_xlabel("effective_total_vnf_num", fontsize=13, fontweight="bold")
    ax.set_ylabel("NHEFT Gain % over DHEFT", fontsize=13, fontweight="bold")
    ax.set_title("E16 Experiment: NHEFT Gain vs VNF Scale", fontsize=14, fontweight="bold")
    ax.grid(True, alpha=0.3, linestyle="--")
    ax.set_xticks(x)
    ax.set_xticklabels([str(int(v)) for v in x], fontsize=12)
    ax.legend(fontsize=11, loc="best")

    plt.tight_layout()
    trend_path = os.path.join(result_dir, "e16_gain_trend.png")
    plt.savefig(trend_path, dpi=300, bbox_inches="tight")
    plt.close()
    print(f"Gain trend chart saved: {trend_path}")

    # Plot 2: grouped bars
    fig, ax = plt.subplots(figsize=(12, 7))

    labels = summary_df["effective_total_vnf_num"].astype(str).values
    dheft_means = summary_df["DHEFT_mean"].values
    nheft_means = summary_df["NHEFT_mean"].values

    x_pos = np.arange(len(labels))
    bar_width = 0.35

    bars1 = ax.bar(
        x_pos - bar_width / 2,
        dheft_means,
        bar_width,
        label="DHEFT",
        color="#FF6B6B",
        alpha=0.85,
        edgecolor="black",
        linewidth=1.0,
    )
    bars2 = ax.bar(
        x_pos + bar_width / 2,
        nheft_means,
        bar_width,
        label="NHEFT",
        color="#06A77D",
        alpha=0.85,
        edgecolor="black",
        linewidth=1.0,
    )

    ax.set_xlabel("effective_total_vnf_num", fontsize=13, fontweight="bold")
    ax.set_ylabel("Average Makespan (seconds)", fontsize=13, fontweight="bold")
    ax.set_title("E16 Experiment: DHEFT vs NHEFT Makespan", fontsize=14, fontweight="bold")
    ax.set_xticks(x_pos)
    ax.set_xticklabels(labels, fontsize=12)
    ax.legend(fontsize=12, loc="best")
    ax.grid(True, alpha=0.3, axis="y", linestyle="--")

    add_value_labels(ax, bars1)
    add_value_labels(ax, bars2)

    plt.tight_layout()
    bar_path = os.path.join(result_dir, "e16_makespan_comparison.png")
    plt.savefig(bar_path, dpi=300, bbox_inches="tight")
    plt.close()
    print(f"Grouped bar chart saved: {bar_path}")


if __name__ == "__main__":
    main()
