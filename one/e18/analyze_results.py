#!/usr/bin/env python3
"""
Analyze E18 results: high repository bandwidth x SFC fragmentation trade-off.

Outputs:
- grid_e18_summary.csv
- e18_summary_table.png
- e18_gain_heatmap.png
- e18_winrate_heatmap.png
- e18_fragmentation_trend.png
- e18_repo_bw_trend.png

Usage:
  python3 analyze_results.py <result_folder>
  python3 analyze_results.py run_YYYYMMDD_HHMMSS_150_100
"""

import os
import sys
import tempfile
import json
import glob
import shutil

CACHE_ROOT = os.path.join(tempfile.gettempdir(), "e18_mpl_cache")
os.makedirs(CACHE_ROOT, exist_ok=True)
os.environ.setdefault("MPLBACKEND", "Agg")
os.environ.setdefault("XDG_CACHE_HOME", CACHE_ROOT)
os.environ.setdefault("MPLCONFIGDIR", os.path.join(CACHE_ROOT, "mplconfig"))
os.makedirs(os.environ["MPLCONFIGDIR"], exist_ok=True)

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


def draw_heatmap(matrix_df, title, colorbar_label, out_path, fmt="{:.2f}", cmap="YlGn"):
    fig, ax = plt.subplots(figsize=(9, 7))
    values = matrix_df.values.astype(float)
    im = ax.imshow(values, cmap=cmap, aspect="auto")

    ax.set_xticks(np.arange(len(matrix_df.columns)))
    ax.set_yticks(np.arange(len(matrix_df.index)))
    ax.set_xticklabels([str(int(v)) for v in matrix_df.columns], fontsize=11)
    ax.set_yticklabels([str(int(v)) for v in matrix_df.index], fontsize=11)

    ax.set_xlabel("repository_bw", fontsize=12, fontweight="bold")
    ax.set_ylabel("multiple_sfc_num", fontsize=12, fontweight="bold")
    ax.set_title(title, fontsize=14, fontweight="bold")

    cbar = fig.colorbar(im, ax=ax)
    cbar.set_label(colorbar_label, fontsize=11, fontweight="bold")

    for i in range(values.shape[0]):
        for j in range(values.shape[1]):
            ax.text(
                j,
                i,
                fmt.format(values[i, j]),
                ha="center",
                va="center",
                color="black",
                fontsize=10,
                fontweight="bold",
            )

    plt.tight_layout()
    plt.savefig(out_path, dpi=300, bbox_inches="tight")
    plt.close()


def draw_summary_table(summary_df, out_path):
    display_df = summary_df[
        [
            "repository_bw",
            "multiple_sfc_num",
            "per_sfc_vnf_num",
            "DHEFT_mean",
            "NHEFT_mean",
            "gain_N_over_D_median",
            "gain_N_over_D_mean",
            "wins_count",
            "win_rate",
            "p_value",
            "n_runs",
        ]
    ].copy()
    display_df["wins_count"] = display_df.apply(
        lambda row: f"{int(row['wins_count'])}/{int(row['n_runs'])}",
        axis=1,
    )

    int_cols = ["repository_bw", "multiple_sfc_num", "per_sfc_vnf_num"]
    float6_cols = [
        "DHEFT_mean",
        "NHEFT_mean",
        "gain_N_over_D_median",
        "gain_N_over_D_mean",
        "win_rate",
    ]

    for col in int_cols:
        display_df[col] = display_df[col].map(lambda x: f"{int(x)}")
    for col in float6_cols:
        display_df[col] = display_df[col].map(lambda x: f"{float(x):.6f}")
    display_df["p_value"] = display_df["p_value"].map(
        lambda x: "" if pd.isna(x) else f"{float(x):.6e}"
    )
    display_df = display_df.drop(columns=["n_runs"])

    fig_height = max(3.8, 0.55 * (len(display_df) + 2))
    fig, ax = plt.subplots(figsize=(18, fig_height))
    ax.axis("off")
    ax.set_title(
        "E18 Results by repository_bw x fragmentation level",
        fontsize=14,
        fontweight="bold",
        pad=14,
    )

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


def resolve_log_path(result_dir, seed, repository_bw, multiple_sfc_num, per_sfc_vnf_num):
    """Resolve per-run log path under logs/ (supports both new and legacy patterns)."""
    logs_dir = os.path.join(result_dir, "logs")
    seed_i = int(seed)
    rb_i = int(repository_bw)
    msfc_i = int(multiple_sfc_num)
    per_i = int(per_sfc_vnf_num)

    # Preferred canonical pattern.
    new_name = os.path.join(logs_dir, f"run_seed_{seed_i}_rb_{rb_i}_msfc_{msfc_i}_per_{per_i}.log")
    if os.path.exists(new_name):
        return new_name

    # Legacy pattern contains master-seed prefix.
    legacy_pattern = os.path.join(logs_dir, f"run_*_seed_{seed_i}_rb_{rb_i}_msfc_{msfc_i}_per_{per_i}.log")
    matches = sorted(glob.glob(legacy_pattern))
    if matches:
        return matches[0]

    # Last fallback when per_sfc is unknown or changed.
    fallback_pattern = os.path.join(logs_dir, f"run_*_seed_{seed_i}_rb_{rb_i}_msfc_{msfc_i}_per_*.log")
    fallback_matches = sorted(glob.glob(fallback_pattern))
    if fallback_matches:
        return fallback_matches[0]

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
        print(f"Available run_* folders in {THIS_DIR}:")
        for d in sorted(os.listdir(THIS_DIR)):
            if os.path.isdir(os.path.join(THIS_DIR, d)) and d.startswith("run_"):
                print(f"  {d}")
        raise SystemExit(1)

    moved_logs = normalize_log_layout(result_dir)
    if moved_logs > 0:
        print(f"Moved {moved_logs} legacy log files into: {os.path.join(result_dir, 'logs')}")

    csv_path = os.path.join(result_dir, "grid_e18_results.csv")
    if not os.path.exists(csv_path):
        print(f"CSV not found: {csv_path}")
        raise SystemExit(1)

    df = pd.read_csv(csv_path)
    df = df[(df["HEFT"] > 0) & (df["DHEFT"] > 0) & (df["NHEFT"] > 0)]
    df["gain_N_over_D"] = (df["DHEFT"] - df["NHEFT"]) / df["DHEFT"] * 100

    grouped = df.groupby(["repository_bw", "multiple_sfc_num", "per_sfc_vnf_num"])
    summary_rows = []

    for (repo_bw, msfc, per_sfc), group in grouped:
        n_runs = len(group)
        dheft_mean = group["DHEFT"].mean()
        dheft_std = group["DHEFT"].std()
        nheft_mean = group["NHEFT"].mean()
        nheft_std = group["NHEFT"].std()
        gain_mean = group["gain_N_over_D"].mean()
        gain_median = group["gain_N_over_D"].median()
        gain_trimmed = stats.trim_mean(group["gain_N_over_D"], 0.1)
        wins = int((group["NHEFT"] < group["DHEFT"]).sum())
        win_rate = wins / n_runs if n_runs else np.nan

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
                "repository_bw": int(repo_bw),
                "multiple_sfc_num": int(msfc),
                "per_sfc_vnf_num": int(per_sfc),
                "DHEFT_mean": dheft_mean,
                "DHEFT_std": dheft_std,
                "NHEFT_mean": nheft_mean,
                "NHEFT_std": nheft_std,
                "gain_N_over_D_mean": gain_mean,
                "gain_N_over_D_median": gain_median,
                "gain_N_over_D_trimmed": gain_trimmed,
                "wins_count": wins,
                "win_rate": win_rate,
                "p_value": p_val,
                "wilcoxon_p": w_pval,
                "n_runs": n_runs,
            }
        )

    summary_df = pd.DataFrame(summary_rows).sort_values(
        ["repository_bw", "multiple_sfc_num", "per_sfc_vnf_num"]
    )
    summary_csv = os.path.join(result_dir, "grid_e18_summary.csv")
    summary_df.to_csv(summary_csv, index=False)

    # Build a repository_bw -> multiple_sfc_num -> {seed -> execution details}
    # JSON where NHEFT loses to DHEFT.
    if "seed" not in df.columns:
        raise SystemExit("Missing required column: seed")
    loss_details_by_repo_msfc = {}
    grouped_cells = df.groupby(["repository_bw", "multiple_sfc_num"])
    for (repo_bw, msfc), group in grouped_cells:
        repo_key = str(int(repo_bw))
        msfc_key = str(int(msfc))
        loss_group = group[group["NHEFT"] > group["DHEFT"]].sort_values("seed")
        seed_map = {}
        for _, row in loss_group.iterrows():
            seed_key = str(int(row["seed"]))
            dheft_val = float(row["DHEFT"])
            nheft_val = float(row["NHEFT"])

            if "per_sfc_vnf_num" in row.index and not pd.isna(row["per_sfc_vnf_num"]):
                per_sfc_vnf_num = int(row["per_sfc_vnf_num"])
            elif "effective_total_vnf_num" in row.index and not pd.isna(row["effective_total_vnf_num"]):
                per_sfc_vnf_num = int(row["effective_total_vnf_num"]) // int(row["multiple_sfc_num"])
            else:
                per_sfc_vnf_num = 0

            log_path = resolve_log_path(
                result_dir,
                row["seed"],
                row["repository_bw"],
                row["multiple_sfc_num"],
                per_sfc_vnf_num,
            )
            log_meta = read_log_meta(log_path)
            seed_map[seed_key] = {
                "HEFT": round(float(row["HEFT"]), 6),
                "DHEFT": round(dheft_val, 6),
                "NHEFT": round(nheft_val, 6),
                "gain_N_over_D_percent": round(float(row["gain_N_over_D"]), 6),
                "nheft_minus_dheft": round(nheft_val - dheft_val, 6),
                "repository_bw": int(row["repository_bw"]) if "repository_bw" in row.index else None,
                "multiple_sfc_num": int(row["multiple_sfc_num"]) if "multiple_sfc_num" in row.index else None,
                "per_sfc_vnf_num": per_sfc_vnf_num,
                "effective_total_vnf_num": int(row["effective_total_vnf_num"]) if "effective_total_vnf_num" in row.index else None,
                "vnf_type_min": int(row["vnf_type_min"]) if "vnf_type_min" in row.index else None,
                "vnf_type_max": int(row["vnf_type_max"]) if "vnf_type_max" in row.index else None,
                "vnf_image_size_min": int(row["vnf_image_size_min"]) if "vnf_image_size_min" in row.index else None,
                "vnf_image_size_max": int(row["vnf_image_size_max"]) if "vnf_image_size_max" in row.index else None,
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

        if repo_key not in loss_details_by_repo_msfc:
            loss_details_by_repo_msfc[repo_key] = {}
        loss_details_by_repo_msfc[repo_key][msfc_key] = seed_map

    loss_json_path = os.path.join(result_dir, "e18_nheft_loss_seeds_by_repository_bw_multiple_sfc_num.json")
    with open(loss_json_path, "w") as f:
        json.dump(loss_details_by_repo_msfc, f, indent=2)

    print(f"\nSummary CSV: {summary_csv}")
    print(f"Loss-seeds JSON saved: {loss_json_path}")
    print("\n=== E18 Results by repository_bw x fragmentation level ===")
    console_df = summary_df[
        [
            "repository_bw",
            "multiple_sfc_num",
            "per_sfc_vnf_num",
            "DHEFT_mean",
            "NHEFT_mean",
            "gain_N_over_D_median",
            "gain_N_over_D_mean",
            "wins_count",
            "win_rate",
            "p_value",
            "n_runs",
        ]
    ].copy()
    console_df["wins_count"] = console_df.apply(
        lambda row: f"{int(row['wins_count'])}/{int(row['n_runs'])}",
        axis=1,
    )
    console_df = console_df.drop(columns=["n_runs"])
    print(console_df.to_string(index=False))

    summary_table_path = os.path.join(result_dir, "e18_summary_table.png")
    draw_summary_table(summary_df, summary_table_path)
    print(f"Summary table image saved: {summary_table_path}")

    gain_matrix = summary_df.pivot(
        index="multiple_sfc_num",
        columns="repository_bw",
        values="gain_N_over_D_mean",
    ).sort_index().sort_index(axis=1)
    gain_heatmap = os.path.join(result_dir, "e18_gain_heatmap.png")
    draw_heatmap(
        gain_matrix,
        "E18 Experiment: NHEFT Gain % over DHEFT",
        "Gain %",
        gain_heatmap,
        fmt="{:.2f}",
        cmap="YlGn",
    )
    print(f"Gain heatmap saved: {gain_heatmap}")

    winrate_matrix = summary_df.pivot(
        index="multiple_sfc_num",
        columns="repository_bw",
        values="win_rate",
    ).sort_index().sort_index(axis=1)
    winrate_heatmap = os.path.join(result_dir, "e18_winrate_heatmap.png")
    draw_heatmap(
        winrate_matrix,
        "E18 Experiment: NHEFT Win Rate",
        "Win Rate",
        winrate_heatmap,
        fmt="{:.2f}",
        cmap="Blues",
    )
    print(f"Win-rate heatmap saved: {winrate_heatmap}")

    # Plot 1: multiple_sfc_num as the x-axis, one line per repository_bw
    fig, ax = plt.subplots(figsize=(11, 7))
    repo_levels = sorted(summary_df["repository_bw"].unique())
    msfc_levels = sorted(summary_df["multiple_sfc_num"].unique())
    colors = ["#06A77D", "#A23B72", "#F18F01", "#2E86AB", "#FF6B6B", "#6C757D"]
    markers = ["o", "s", "^", "D", "P", "X"]

    for idx, rb in enumerate(repo_levels):
        row = summary_df[summary_df["repository_bw"] == rb].sort_values("multiple_sfc_num")
        ax.plot(
            row["multiple_sfc_num"].values,
            row["gain_N_over_D_median"].values,
            marker=markers[idx % len(markers)],
            markersize=8,
            linewidth=2.2,
            color=colors[idx % len(colors)],
            label=f"repository_bw={rb}",
        )

    ax.axhline(y=0, color="red", linestyle="--", alpha=0.5, linewidth=1)
    ax.set_xlabel("multiple_sfc_num", fontsize=13, fontweight="bold")
    ax.set_ylabel("NHEFT Gain % over DHEFT (median)", fontsize=13, fontweight="bold")
    ax.set_title(
        "E18 Experiment: Fragmentation Trade-off under High Repository BW",
        fontsize=14,
        fontweight="bold",
    )
    ax.set_xticks(msfc_levels)
    ax.set_xticklabels([str(int(v)) for v in msfc_levels], fontsize=12)
    ax.grid(True, alpha=0.3, linestyle="--")
    ax.legend(fontsize=11, loc="best")

    plt.tight_layout()
    frag_path = os.path.join(result_dir, "e18_fragmentation_trend.png")
    plt.savefig(frag_path, dpi=300, bbox_inches="tight")
    plt.close()
    print(f"Fragmentation trend saved: {frag_path}")

    # Plot 2: repository_bw as the x-axis, one line per multiple_sfc_num
    fig, ax = plt.subplots(figsize=(11, 7))
    for idx, msfc in enumerate(msfc_levels):
        row = summary_df[summary_df["multiple_sfc_num"] == msfc].sort_values("repository_bw")
        ax.plot(
            row["repository_bw"].values,
            row["gain_N_over_D_median"].values,
            marker=markers[idx % len(markers)],
            markersize=8,
            linewidth=2.2,
            color=colors[idx % len(colors)],
            label=f"multiple_sfc_num={msfc}",
        )

    ax.axhline(y=0, color="red", linestyle="--", alpha=0.5, linewidth=1)
    ax.set_xlabel("repository_bw", fontsize=13, fontweight="bold")
    ax.set_ylabel("NHEFT Gain % over DHEFT (median)", fontsize=13, fontweight="bold")
    ax.set_title(
        "E18 Experiment: Repository BW under Different Fragmentation Levels",
        fontsize=14,
        fontweight="bold",
    )
    ax.set_xticks(repo_levels)
    ax.set_xticklabels([str(int(v)) for v in repo_levels], fontsize=12)
    ax.grid(True, alpha=0.3, linestyle="--")
    ax.legend(fontsize=11, loc="best")

    plt.tight_layout()
    repo_path = os.path.join(result_dir, "e18_repo_bw_trend.png")
    plt.savefig(repo_path, dpi=300, bbox_inches="tight")
    plt.close()
    print(f"Repository-BW trend saved: {repo_path}")


if __name__ == "__main__":
    main()
