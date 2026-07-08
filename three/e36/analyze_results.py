#!/usr/bin/env python3
"""
Analyze E36 results for the fixed B36 scenario (no variable sweep).

Usage:
  python3 analyze_results.py <result_folder>
  python3 analyze_results.py run_20260601_120000_150_100
"""

import os
import sys
import json
import shutil
import re

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy import stats

THIS_DIR = os.path.dirname(os.path.abspath(__file__))
FLOAT_PAT = r"[-+]?(?:\d+\.?\d*|\.\d+)(?:[eE][-+]?\d+)?"
B36_REL_TOL_PCT = float(os.getenv("E36_B36_REL_TOL_PCT", "10.0"))
CCR_LINE_RE = re.compile(
    rf"CCR_data:\s*({FLOAT_PAT})\s*/\s*IDR_image:\s*({FLOAT_PAT})\s*/\s*NCCR_total:\s*({FLOAT_PAT})"
)


def resolve_result_dir(arg):
    """Resolve result directory path (absolute, relative, or basename)."""
    if os.path.isdir(arg):
        return arg

    candidate = os.path.join(THIS_DIR, arg)
    if os.path.isdir(candidate):
        return candidate

    try:
        matches = [
            d
            for d in os.listdir(THIS_DIR)
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


def draw_table_image(display_df, title, out_path):
    fig_height = max(3.2, 0.65 * (len(display_df) + 2))
    fig, ax = plt.subplots(figsize=(14, fig_height))
    ax.axis("off")
    ax.set_title(title, fontsize=14, fontweight="bold", pad=14)

    table = ax.table(
        cellText=display_df.values,
        colLabels=display_df.columns,
        cellLoc="center",
        loc="center",
    )
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
    """Ensure run logs are stored under result_dir/logs."""
    logs_dir = os.path.join(result_dir, "logs")
    os.makedirs(logs_dir, exist_ok=True)

    moved = 0
    for name in os.listdir(result_dir):
        src = os.path.join(result_dir, name)
        if not os.path.isfile(src):
            continue
        if not (name.startswith("run_seed_") and name.endswith(".log")):
            continue
        dst = os.path.join(logs_dir, name)
        try:
            shutil.move(src, dst)
            moved += 1
        except Exception:
            pass
    return moved


def parse_ccr_idr_nccr_from_log(log_path):
    """
    Parse CCR_data / IDR_image / NCCR_total from one run log.
    Returns (ccr_data, idr_image, nccr_total) or (np.nan, np.nan, np.nan).
    """
    if not os.path.exists(log_path):
        return np.nan, np.nan, np.nan

    try:
        ccr_val = np.nan
        idr_val = np.nan
        nccr_val = np.nan
        with open(log_path, "r", errors="ignore") as f:
            for line in f:
                m = CCR_LINE_RE.search(line)
                if not m:
                    continue
                ccr_val = float(m.group(1))
                idr_val = float(m.group(2))
                nccr_val = float(m.group(3))
        return ccr_val, idr_val, nccr_val
    except Exception:
        return np.nan, np.nan, np.nan


def calc_relative_gap_pct(a, b):
    """
    Symmetric relative gap between CCR and IDR, reported as percent:
      |a-b| / ((a+b)/2) * 100
    """
    if pd.isna(a) or pd.isna(b):
        return np.nan
    avg = (a + b) / 2.0
    if avg == 0:
        return np.nan
    return abs(a - b) / avg * 100.0


def main():
    if len(sys.argv) < 2:
        print("Usage: analyze_results.py <result_folder>")
        raise SystemExit(1)

    result_dir = resolve_result_dir(sys.argv[1])
    if not result_dir:
        print(f"Result folder not found: {sys.argv[1]}")
        print(f"Available run_* folders in {THIS_DIR}:")
        for d in sorted(os.listdir(THIS_DIR)):
            if os.path.isdir(os.path.join(THIS_DIR, d)) and d.startswith("run_"):
                print(f"  {d}")
        raise SystemExit(1)

    moved_logs = normalize_log_layout(result_dir)
    if moved_logs > 0:
        print(f"Moved {moved_logs} legacy log files into: {os.path.join(result_dir, 'logs')}")

    csv_path = os.path.join(result_dir, "grid_e36_results.csv")
    if not os.path.exists(csv_path):
        print(f"CSV not found: {csv_path}")
        raise SystemExit(1)

    df_all = pd.read_csv(csv_path)
    total_runs = len(df_all)

    # Attach CCR_data / IDR_image / NCCR_total from per-seed logs.
    logs_dir = os.path.join(result_dir, "logs")
    ccr_list = []
    idr_list = []
    nccr_list = []
    for _, row in df_all.iterrows():
        seed = int(row["seed"])
        log_path = os.path.join(logs_dir, f"run_seed_{seed}.log")
        ccr_val, idr_val, nccr_val = parse_ccr_idr_nccr_from_log(log_path)
        ccr_list.append(ccr_val)
        idr_list.append(idr_val)
        nccr_list.append(nccr_val)

    df_all["CCR_data"] = ccr_list
    df_all["IDR_image"] = idr_list
    df_all["NCCR_total"] = nccr_list
    df_all["CCR_IDR_abs_diff"] = (df_all["CCR_data"] - df_all["IDR_image"]).abs()
    df_all["CCR_IDR_rel_gap_pct"] = [
        calc_relative_gap_pct(a, b) for a, b in zip(df_all["CCR_data"], df_all["IDR_image"])
    ]
    df_all["b36_match"] = (
        (df_all["NCCR_total"] > 1.78)
        & (df_all["NCCR_total"] <= 3.16)
        & (df_all["CCR_IDR_rel_gap_pct"] <= B36_REL_TOL_PCT)
    )

    seed_metrics_csv = os.path.join(result_dir, "e36_seed_metrics_with_b36_flag.csv")
    df_all.to_csv(seed_metrics_csv, index=False)

    # Step 1: algorithm-valid runs
    df_algo_valid = df_all[(df_all["HEFT"] > 0) & (df_all["DHEFT"] > 0) & (df_all["NHEFT"] > 0)].copy()
    algo_valid_runs = len(df_algo_valid)
    if algo_valid_runs == 0:
        print("No valid runs found (all HEFT/DHEFT/NHEFT are zero or invalid).")
        raise SystemExit(1)

    # Step 2: keep only seeds that satisfy B36 condition
    df = df_algo_valid[df_algo_valid["b36_match"]].copy()
    qualified_runs = len(df)
    if qualified_runs == 0:
        print(
            f"No runs satisfy B36 condition: 1.78 < NCCR_total <= 3.16 AND "
            f"relative CCR/IDR gap <= {B36_REL_TOL_PCT:.2f}%"
        )
        print(f"Algorithm-valid runs: {algo_valid_runs}, total runs: {total_runs}")
        raise SystemExit(1)

    df["gain_N_over_D"] = (df["DHEFT"] - df["NHEFT"]) / df["DHEFT"] * 100.0
    df["gain_D_over_H"] = (df["HEFT"] - df["DHEFT"]) / df["HEFT"] * 100.0
    df["gain_N_over_H"] = (df["HEFT"] - df["NHEFT"]) / df["HEFT"] * 100.0

    wins_n_over_d = int((df["NHEFT"] < df["DHEFT"]).sum())
    wins_n_over_h = int((df["NHEFT"] < df["HEFT"]).sum())

    p_ttest = np.nan
    p_wilcoxon = np.nan
    if qualified_runs >= 2:
        try:
            _, p_ttest = stats.ttest_rel(df["DHEFT"], df["NHEFT"])
            p_ttest = float(p_ttest)
        except Exception:
            p_ttest = np.nan
        try:
            _, p_wilcoxon = stats.wilcoxon(df["DHEFT"], df["NHEFT"])
            p_wilcoxon = float(p_wilcoxon)
        except Exception:
            p_wilcoxon = np.nan

    summary = {
        "scenario": "b36",
        "b36_rel_tolerance_pct": B36_REL_TOL_PCT,
        "total_runs": total_runs,
        "algo_valid_runs": algo_valid_runs,
        "b36_qualified_runs": qualified_runs,
        "b36_qualified_rate_in_algo_valid": qualified_runs / algo_valid_runs if algo_valid_runs > 0 else np.nan,
        "HEFT_mean": df["HEFT"].mean(),
        "HEFT_std": df["HEFT"].std(),
        "HEFT_median": df["HEFT"].median(),
        "DHEFT_mean": df["DHEFT"].mean(),
        "DHEFT_std": df["DHEFT"].std(),
        "DHEFT_median": df["DHEFT"].median(),
        "NHEFT_mean": df["NHEFT"].mean(),
        "NHEFT_std": df["NHEFT"].std(),
        "NHEFT_median": df["NHEFT"].median(),
        "gain_N_over_D_mean": df["gain_N_over_D"].mean(),
        "gain_N_over_D_median": df["gain_N_over_D"].median(),
        "gain_N_over_D_trimmed": stats.trim_mean(df["gain_N_over_D"], 0.1),
        "gain_N_over_D_std": df["gain_N_over_D"].std(),
        "wins_N_over_D": wins_n_over_d,
        "wins_N_over_H": wins_n_over_h,
        "win_rate_N_over_D": wins_n_over_d / qualified_runs,
        "win_rate_N_over_H": wins_n_over_h / qualified_runs,
        "ttest_p_DHEFT_vs_NHEFT": p_ttest,
        "wilcoxon_p_DHEFT_vs_NHEFT": p_wilcoxon,
    }

    summary_df = pd.DataFrame([summary])
    summary_csv = os.path.join(result_dir, "grid_e36_summary.csv")
    summary_df.to_csv(summary_csv, index=False)

    # Build loss-seed details JSON (NHEFT loses to DHEFT)
    loss_group = df[df["NHEFT"] > df["DHEFT"]].sort_values("seed")
    seed_map = {}
    for _, row in loss_group.iterrows():
        seed_key = str(int(row["seed"]))
        dheft_val = float(row["DHEFT"])
        nheft_val = float(row["NHEFT"])
        seed_map[seed_key] = {
            "HEFT": round(float(row["HEFT"]), 6),
            "DHEFT": round(dheft_val, 6),
            "NHEFT": round(nheft_val, 6),
            "gain_N_over_D_percent": round(float(row["gain_N_over_D"]), 6),
            "nheft_minus_dheft": round(nheft_val - dheft_val, 6),
            "time_sec": round(float(row["time_sec"]), 6) if "time_sec" in row.index else None,
        }

    loss_json = {"b36": seed_map}
    loss_json_path = os.path.join(result_dir, "e36_nheft_loss_seeds_by_scenario.json")
    with open(loss_json_path, "w") as f:
        json.dump(loss_json, f, indent=2)

    print(f"\nSummary CSV: {summary_csv}")
    print(f"Loss-seeds JSON saved: {loss_json_path}")
    print(f"Seed metrics with B36 flag: {seed_metrics_csv}")

    # Console/table summary
    print("\n=== E36 Results (B36 Fixed Scenario) ===")
    wins_n_over_d_display = f"{wins_n_over_d}/{qualified_runs} ({summary['win_rate_N_over_D'] * 100:.2f}%)"
    console_row = {
        "scenario": "b36",
        "b36_rel_tol_pct": B36_REL_TOL_PCT,
        "algo_valid_runs": f"{algo_valid_runs}/{total_runs}",
        "b36_qualified_runs": f"{qualified_runs}/{algo_valid_runs}",
        "HEFT_mean": summary["HEFT_mean"],
        "DHEFT_mean": summary["DHEFT_mean"],
        "NHEFT_mean": summary["NHEFT_mean"],
        "gain_N_over_D_median": summary["gain_N_over_D_median"],
        "gain_N_over_D_mean": summary["gain_N_over_D_mean"],
        "wins_N_over_D": wins_n_over_d_display,
        "ttest_p": summary["ttest_p_DHEFT_vs_NHEFT"],
    }
    console_df = pd.DataFrame([console_row])
    print(console_df.to_string(index=False))

    table_df = console_df.copy()
    for col in ["HEFT_mean", "DHEFT_mean", "NHEFT_mean", "gain_N_over_D_median", "gain_N_over_D_mean"]:
        table_df[col] = table_df[col].map(lambda x: f"{float(x):.6f}")
    table_df["ttest_p"] = table_df["ttest_p"].map(lambda x: "" if pd.isna(x) else f"{float(x):.6e}")

    summary_table_path = os.path.join(result_dir, "e36_summary_table.png")
    draw_table_image(table_df, "E36 Summary (B36 Fixed Scenario)", summary_table_path)
    print(f"Summary table image saved: {summary_table_path}")

    robust_df = pd.DataFrame([
        {
            "scenario": "b36",
            "b36_rel_tol_pct": B36_REL_TOL_PCT,
            "gain_median": summary["gain_N_over_D_median"],
            "gain_trimmed": summary["gain_N_over_D_trimmed"],
            "gain_mean": summary["gain_N_over_D_mean"],
            "wins_N_over_D": wins_n_over_d_display,
            "wilcoxon_p": summary["wilcoxon_p_DHEFT_vs_NHEFT"],
        }
    ])

    robust_print = robust_df.copy()
    robust_print["gain_median"] = robust_print["gain_median"].map(lambda x: f"{float(x):.6f}")
    robust_print["gain_trimmed"] = robust_print["gain_trimmed"].map(lambda x: f"{float(x):.6f}")
    robust_print["gain_mean"] = robust_print["gain_mean"].map(lambda x: f"{float(x):.6f}")
    robust_print["wilcoxon_p"] = robust_print["wilcoxon_p"].map(lambda x: "" if pd.isna(x) else f"{float(x):.6e}")
    print("\n=== Robust Statistics ===")
    print(robust_print.to_string(index=False))

    robust_table_path = os.path.join(result_dir, "e36_robust_table.png")
    draw_table_image(robust_print, "E36 Robust Statistics (B36 Fixed Scenario)", robust_table_path)
    print(f"Robust table image saved: {robust_table_path}")

    # Plot 1: mean makespan comparison (HEFT / DHEFT / NHEFT)
    means = [summary["HEFT_mean"], summary["DHEFT_mean"], summary["NHEFT_mean"]]
    labels = ["HEFT", "DHEFT", "NHEFT"]
    colors = ["#4E79A7", "#FF6B8B", "#06A77D"]

    fig, ax = plt.subplots(figsize=(8, 6))
    bars = ax.bar(labels, means, color=colors, edgecolor="black", linewidth=1.2, alpha=0.85)
    ax.set_ylabel("Average Makespan (seconds)", fontsize=12, fontweight="bold")
    ax.set_title("E36 Mean Makespan Comparison (B36 Fixed Scenario)", fontsize=13, fontweight="bold")
    ax.grid(True, axis="y", linestyle="--", alpha=0.3)

    for bar in bars:
        h = bar.get_height()
        ax.text(bar.get_x() + bar.get_width() / 2.0, h, f"{h:.2f}", ha="center", va="bottom", fontsize=10)

    plt.tight_layout()
    chart_means = os.path.join(result_dir, "e36_makespan_mean_comparison.png")
    plt.savefig(chart_means, dpi=300, bbox_inches="tight")
    plt.close()
    print(f"Chart saved: {chart_means}")

    # Plot 2: boxplot of per-seed makespan distribution
    fig, ax = plt.subplots(figsize=(9, 6))
    ax.boxplot(
        [df["HEFT"].values, df["DHEFT"].values, df["NHEFT"].values],
        labels=["HEFT", "DHEFT", "NHEFT"],
        showmeans=True,
    )
    ax.set_ylabel("Makespan (seconds)", fontsize=12, fontweight="bold")
    ax.set_title("E36 Makespan Distribution by Seed (B36 Fixed Scenario)", fontsize=13, fontweight="bold")
    ax.grid(True, axis="y", linestyle="--", alpha=0.3)

    plt.tight_layout()
    chart_box = os.path.join(result_dir, "e36_makespan_boxplot.png")
    plt.savefig(chart_box, dpi=300, bbox_inches="tight")
    plt.close()
    print(f"Chart saved: {chart_box}")

    # Plot 3: histogram of NHEFT gain over DHEFT
    fig, ax = plt.subplots(figsize=(9, 6))
    ax.hist(df["gain_N_over_D"].values, bins=20, color="#06A77D", alpha=0.85, edgecolor="black")
    ax.axvline(summary["gain_N_over_D_median"], color="#A23B82", linestyle="--", linewidth=2, label="median")
    ax.axvline(summary["gain_N_over_D_mean"], color="#F18F01", linestyle=":", linewidth=2, label="mean")
    ax.set_xlabel("NHEFT Gain % over DHEFT", fontsize=12, fontweight="bold")
    ax.set_ylabel("Seed Count", fontsize=12, fontweight="bold")
    ax.set_title("E36 Gain Distribution (B36 Fixed Scenario)", fontsize=13, fontweight="bold")
    ax.grid(True, axis="y", linestyle="--", alpha=0.3)
    ax.legend(loc="best")

    plt.tight_layout()
    chart_hist = os.path.join(result_dir, "e36_gain_histogram.png")
    plt.savefig(chart_hist, dpi=300, bbox_inches="tight")
    plt.close()
    print(f"Chart saved: {chart_hist}")


if __name__ == "__main__":
    main()
