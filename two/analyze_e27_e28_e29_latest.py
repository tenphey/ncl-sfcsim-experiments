#!/usr/bin/env python3
"""
Aggregate latest runs of e27/e28/e29 and draw cross-scenario bar charts.

Output folder:
  experiments/e27_e28_e29/<timestamp>/

Usage:
  python3 experiments/analyze_e27_e28_e29_latest.py
"""

import os
import re
import math
from datetime import datetime

import numpy as np
import pandas as pd
from PIL import Image, ImageDraw, ImageFont


THIS_DIR = os.path.dirname(os.path.abspath(__file__))
OUT_BASE_DIR = os.path.join(THIS_DIR, "e27_e28_e29")
PROJECT_ROOT = os.path.dirname(THIS_DIR)

# Switch for grouped makespan chart:
#   True  -> show NHEFT win-rate line on right axis
#   False -> hide win-rate line and right axis
# Default is True.
SHOW_WIN_RATE_LINE = True
# Switch for grouped makespan chart:
#   True  -> show NHEFT gain line (vs DHEFT) on separate right axis
#   False -> hide gain line and its axis
# Default is True.
SHOW_GAIN_LINE = True
# Horizontal offset of the 1st right axis (win-rate axis), relative to chart_right.
# Default 10 moves it slightly right.
RIGHT1_AXIS_OFFSET = 10
# Horizontal offset of the 2nd right axis (gain axis), relative to chart_right.
# Keep as 0 for no extra shift. Backup option: 180.
RIGHT2_AXIS_OFFSET = 100  # backup: 180
# Vertical offset of "Common Constraint" relative to chart_bottom.
# Smaller value moves the text upward.
COMMON_CONSTRAINT_Y_OFFSET = 130
# Shift top-right legend leftward toward chart center.
# Increase this value to move legend further toward center.
LEGEND_SHIFT_TO_CENTER = 60
# Anti-alias scale for line overlays (win-rate/gain lines + markers).
# 1 disables smoothing, 2~3 is usually enough.
LINE_ANTIALIAS_SCALE = 3


SCENARIOS = [
    {
        "exp_dir": "e27",
        "scenario": "b7",
        "condition": "CCR_data > IDR_image",
        "summary_csv": "grid_e27_summary.csv",
    },
    {
        "exp_dir": "e28",
        "scenario": "b8",
        "condition": "CCR_data ~= IDR_image",
        "summary_csv": "grid_e28_summary.csv",
    },
    {
        "exp_dir": "e29",
        "scenario": "b9",
        "condition": "CCR_data < IDR_image",
        "summary_csv": "grid_e29_summary.csv",
    },
]


def find_latest_run_dir(exp_abs_dir):
    run_dirs = []
    for name in os.listdir(exp_abs_dir):
        path = os.path.join(exp_abs_dir, name)
        if not os.path.isdir(path):
            continue
        if not name.startswith("run_"):
            continue
        run_dirs.append(path)

    if not run_dirs:
        return None
    run_dirs.sort(key=lambda p: os.path.getmtime(p), reverse=True)
    return run_dirs[0]


def find_qualified_col(columns, scenario):
    exact = f"{scenario}_qualified_runs"
    if exact in columns:
        return exact
    pat = re.compile(r"^b\d+_qualified_runs$")
    for c in columns:
        if pat.match(c):
            return c
    return None


def ensure_float(v, default=np.nan):
    try:
        return float(v)
    except Exception:
        return default


def ensure_int(v, default=0):
    try:
        return int(float(v))
    except Exception:
        return default


def rel_to_project(path):
    try:
        return os.path.relpath(str(path), PROJECT_ROOT)
    except Exception:
        return str(path)


def load_font(size, bold=False):
    """
    Try to load a scalable font; fallback to PIL default if unavailable.
    """
    candidates_bold = [
        "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
        "/Library/Fonts/Arial Bold.ttf",
        "/System/Library/Fonts/Supplemental/Helvetica.ttc",
        "/System/Library/Fonts/Supplemental/Tahoma Bold.ttf",
    ]
    candidates_regular = [
        "/System/Library/Fonts/Supplemental/Arial.ttf",
        "/Library/Fonts/Arial.ttf",
        "/System/Library/Fonts/Supplemental/Helvetica.ttc",
        "/System/Library/Fonts/Supplemental/Tahoma.ttf",
    ]
    candidates = candidates_bold if bold else candidates_regular
    for path in candidates:
        try:
            return ImageFont.truetype(path, size=size)
        except Exception:
            continue
    return ImageFont.load_default()


def draw_antialiased_line_and_markers(base_img, points_xy, color, line_width=3, marker_radius=6, scale=3):
    """
    Draw one polyline with round markers using supersampling anti-aliasing.
    `points_xy` can contain None entries to split segments.
    """
    if scale <= 1:
        draw = ImageDraw.Draw(base_img)
        prev = None
        for pt in points_xy:
            if pt is None:
                prev = None
                continue
            x, y = int(pt[0]), int(pt[1])
            if prev is not None:
                draw.line([(prev[0], prev[1]), (x, y)], fill=color, width=line_width)
            r = int(marker_radius)
            draw.ellipse([(x - r, y - r), (x + r, y + r)], outline=color, fill=color, width=max(1, line_width // 2))
            prev = (x, y)
        return

    hi_w, hi_h = base_img.width * scale, base_img.height * scale
    hi = Image.new("RGBA", (hi_w, hi_h), (0, 0, 0, 0))
    hdraw = ImageDraw.Draw(hi)

    prev = None
    for pt in points_xy:
        if pt is None:
            prev = None
            continue
        x = int(pt[0] * scale)
        y = int(pt[1] * scale)
        if prev is not None:
            hdraw.line([(prev[0], prev[1]), (x, y)], fill=color, width=max(1, line_width * scale))
        r = max(1, int(marker_radius * scale))
        hdraw.ellipse([(x - r, y - r), (x + r, y + r)], outline=color, fill=color, width=max(1, (line_width * scale) // 2))
        prev = (x, y)

    # Back to normal resolution with anti-aliasing filter.
    lanczos = Image.Resampling.LANCZOS if hasattr(Image, "Resampling") else Image.LANCZOS
    lo = hi.resize((base_img.width, base_img.height), resample=lanczos)
    base_rgba = base_img.convert("RGBA")
    base_rgba.alpha_composite(lo)
    base_img.paste(base_rgba.convert("RGB"))


def draw_bar(df, y_col, y_label, title, out_path, ylim_min=0.0):
    width, height = 1400, 900
    margin_left, margin_right, margin_top, margin_bottom = 140, 80, 120, 250
    chart_left = margin_left
    chart_right = width - margin_right
    chart_top = margin_top
    chart_bottom = height - margin_bottom
    chart_w = chart_right - chart_left
    chart_h = chart_bottom - chart_top

    values = [float(v) for v in df[y_col].tolist()]
    labels = df["x_label"].tolist()
    wins = df["wins_display"].tolist()
    colors = ["#4E79A7", "#F28E2B", "#59A14F"]

    vmax = max(values) if values else 1.0
    vmax = max(vmax, 1.0)
    vmin = min(ylim_min, min(values) if values else 0.0)
    if vmax <= vmin:
        vmax = vmin + 1.0

    def y_to_px(v):
        ratio = (v - vmin) / (vmax - vmin)
        return int(chart_bottom - ratio * chart_h)

    img = Image.new("RGB", (width, height), "white")
    draw = ImageDraw.Draw(img)
    font = ImageFont.load_default()
    bold = ImageFont.load_default()

    # Title and axis label
    draw.text((margin_left, 30), title, fill="black", font=bold)
    draw.text((margin_left, 58), y_label, fill="#333333", font=font)

    # Axes
    draw.line([(chart_left, chart_top), (chart_left, chart_bottom)], fill="black", width=2)
    draw.line([(chart_left, chart_bottom), (chart_right, chart_bottom)], fill="black", width=2)

    # Horizontal grid and ticks (5 levels)
    tick_levels = 5
    for i in range(tick_levels + 1):
        v = vmin + (vmax - vmin) * i / tick_levels
        y = y_to_px(v)
        draw.line([(chart_left, y), (chart_right, y)], fill="#DDDDDD", width=1)
        draw.text((20, y - 7), f"{v:.2f}", fill="#555555", font=font)

    n = len(values)
    if n == 0:
        img.save(out_path)
        return

    slot_w = chart_w / n
    bar_w = int(slot_w * 0.50)

    for i, v in enumerate(values):
        cx = chart_left + slot_w * (i + 0.5)
        x0 = int(cx - bar_w / 2)
        x1 = int(cx + bar_w / 2)
        y0 = y_to_px(max(v, 0))
        y_base = y_to_px(0 if vmin <= 0 <= vmax else vmin)
        top = min(y0, y_base)
        bottom = max(y0, y_base)

        draw.rectangle([(x0, top), (x1, bottom)], fill=colors[i % len(colors)], outline="black", width=2)

        # Value + wins annotation above bar
        ann = f"{v:.2f}\n{wins[i]}"
        draw.multiline_text((x0 - 10, top - 36), ann, fill="black", font=font, spacing=2)

        # X labels
        draw.multiline_text((x0 - 25, chart_bottom + 16), labels[i], fill="black", font=font, spacing=2)

    img.save(out_path)


def draw_grouped_makespan_chart(df, out_path):
    """
    Draw one grouped bar chart:
      X major groups: b7 / b8 / b9
      X minor bars in each group: HEFT / DHEFT / NHEFT
      Y-left: mean makespan
      Y-right-1: NHEFT win rate (%)
      Y-right-2: NHEFT gain over DHEFT (%)
    """
    # Increase canvas height and top margin to avoid overlap between
    # top-right legend and right-axis tick labels.
    width, height = 1700, 1320
    margin_left, margin_right, margin_top, margin_bottom = 150, 250, 210, 280
    chart_left = margin_left
    chart_right = width - margin_right
    chart_top = margin_top
    chart_bottom = height - margin_bottom
    chart_w = chart_right - chart_left
    chart_h = chart_bottom - chart_top

    algos = ["HEFT", "DHEFT", "NHEFT"]
    algo_colors = {
        "HEFT": "#4E79A7",
        "DHEFT": "#FF6B6B",
        "NHEFT": "#06A77D",
    }

    values = {
        algo: [float(v) for v in df[f"{algo}_mean"].tolist()]
        for algo in algos
    }
    conditions = df["condition"].tolist()
    win_rates = [ensure_float(v, np.nan) for v in df["win_rate_percent"].tolist()]
    gains = [ensure_float(v, np.nan) for v in df["gain_N_over_D_mean"].tolist()]

    vmax_raw = max(max(values[a]) for a in algos) if len(df) > 0 else 1.0
    vmax_raw = max(vmax_raw, 1.0)
    # Add 50% headroom above the tallest bar.
    vmax_candidate = vmax_raw * 1.50
    vmin = 0.0

    # Convert raw axis maximum into "nice" human-friendly ticks (e.g., 20, 50, 100).
    def calc_nice_step(max_value, target_intervals=6):
        if max_value <= 0:
            return 1.0
        raw_step = max_value / float(target_intervals)
        exp = math.floor(math.log10(raw_step))
        base = 10 ** exp
        frac = raw_step / base
        if frac <= 1.0:
            nice_frac = 1.0
        elif frac <= 2.0:
            nice_frac = 2.0
        elif frac <= 2.5:
            nice_frac = 2.5
        elif frac <= 5.0:
            nice_frac = 5.0
        else:
            nice_frac = 10.0
        return nice_frac * base

    y_step = calc_nice_step(vmax_candidate, target_intervals=6)
    vmax = y_step * math.ceil(vmax_candidate / y_step)

    def fmt_tick(v, step):
        if step >= 1.0:
            if abs(step - round(step)) < 1e-9:
                return f"{v:.0f}"
            return f"{v:.1f}"
        if step >= 0.1:
            return f"{v:.1f}"
        return f"{v:.2f}"

    def y_to_px(v):
        ratio = (v - vmin) / (vmax - vmin)
        return int(chart_bottom - ratio * chart_h)

    def y_win_to_px(v):
        # Right axis fixed at 0..100 (%), mapped to full chart height.
        # This makes 100% align with the left-axis top (vmax).
        vv = max(0.0, min(100.0, float(v)))
        ratio = vv / 100.0
        return int(chart_bottom - ratio * chart_h)

    # Gain axis scale (right-2), computed from actual gain values.
    gain_vals = [g for g in gains if not np.isnan(g)]
    has_gain_data = len(gain_vals) > 0

    if has_gain_data:
        g_min_raw = min(gain_vals)
        g_max_raw = max(gain_vals)
        if abs(g_max_raw - g_min_raw) < 1e-9:
            g_min_candidate = min(0.0, g_min_raw - 1.0)
            g_max_candidate = g_max_raw + 1.0
        else:
            g_span = g_max_raw - g_min_raw
            g_min_candidate = min(0.0, g_min_raw - 0.20 * g_span)
            g_max_candidate = g_max_raw + 0.20 * g_span
    else:
        g_min_candidate, g_max_candidate = 0.0, 1.0

    g_step = calc_nice_step(max(1e-9, g_max_candidate - g_min_candidate), target_intervals=5)
    g_vmin = g_step * math.floor(g_min_candidate / g_step)
    g_vmax = g_step * math.ceil(g_max_candidate / g_step)
    if g_vmax <= g_vmin:
        g_vmax = g_vmin + g_step

    def y_gain_to_px(v):
        vv = float(v)
        ratio = (vv - g_vmin) / (g_vmax - g_vmin)
        return int(chart_bottom - ratio * chart_h)

    img = Image.new("RGB", (width, height), "white")
    draw = ImageDraw.Draw(img)
    font_title = load_font(36, bold=True)
    font_axis = load_font(24, bold=True)
    font_tick = load_font(22, bold=False)
    font_value = load_font(20, bold=False)
    font_algo = load_font(20, bold=True)
    font_group = load_font(24, bold=True)
    font_legend = load_font(20, bold=False)
    font_common = load_font(24, bold=True)

    def text_w(text, font):
        box = draw.textbbox((0, 0), text, font=font)
        return box[2] - box[0]

    # Title
    draw.text(
        (margin_left, 20),
        "E27/E28/E29 Makespan Mean Comparison (Grouped by b7/b8/b9)",
        fill="black",
        font=font_title,
    )
    draw.text((margin_left, 68), "Y-axis: Mean Makespan (seconds)", fill="#333333", font=font_axis)

    # Axes
    draw.line([(chart_left, chart_top), (chart_left, chart_bottom)], fill="black", width=2)
    draw.line([(chart_left, chart_bottom), (chart_right, chart_bottom)], fill="black", width=2)

    # Y ticks/grid (natural/nice values).
    tick_levels = int(round((vmax - vmin) / y_step))
    for i in range(tick_levels + 1):
        v = vmin + y_step * i
        y = y_to_px(v)
        draw.line([(chart_left, y), (chart_right, y)], fill="#DDDDDD", width=1)
        tick_text = fmt_tick(v, y_step)
        # Keep tick labels close to the y-axis and right-aligned to it.
        tick_x = max(4, chart_left - text_w(tick_text, font_tick) - 10)
        draw.text((tick_x, y - 12), tick_text, fill="#555555", font=font_tick)

    win_color = "#F39C12"
    win_axis_x = chart_right + RIGHT1_AXIS_OFFSET
    right_axis_title_y = chart_top - 40
    if SHOW_WIN_RATE_LINE:
        # Right Y axis for win-rate percentage.
        draw.line([(win_axis_x, chart_top), (win_axis_x, chart_bottom)], fill=win_color, width=2)
        for p in range(0, 101, 20):
            y = y_win_to_px(p)
            draw.line([(win_axis_x, y), (win_axis_x + 8, y)], fill=win_color, width=2)
            draw.text((win_axis_x + 12, y - 12), f"{p}%", fill=win_color, font=font_tick)
        # Keep both right-axis titles on the same row:
        # left axis title is right-aligned to its own axis (text stays outside/left).
        win_title = "Win Rate (%)"
        win_title_w = text_w(win_title, font_tick)
        draw.text((int(win_axis_x - win_title_w - 2), right_axis_title_y), win_title, fill=win_color, font=font_tick)

    gain_color = "#8E44AD"
    gain_axis_x = chart_right + RIGHT2_AXIS_OFFSET
    if SHOW_GAIN_LINE and has_gain_data:
        # Secondary right Y axis for gain (%).
        draw.line([(gain_axis_x, chart_top), (gain_axis_x, chart_bottom)], fill=gain_color, width=2)
        g_tick_levels = int(round((g_vmax - g_vmin) / g_step))
        for i in range(g_tick_levels + 1):
            gv = g_vmin + g_step * i
            y = y_gain_to_px(gv)
            draw.line([(gain_axis_x, y), (gain_axis_x + 8, y)], fill=gain_color, width=2)
            draw.text((gain_axis_x + 12, y - 12), f"{fmt_tick(gv, g_step)}%", fill=gain_color, font=font_tick)
        # Keep both right-axis titles on the same row:
        # right axis title is left-aligned to its own axis (text stays outside/right).
        gain_title = "Gain (%)"
        draw.text((gain_axis_x + 2, right_axis_title_y), gain_title, fill=gain_color, font=font_tick)

    n_groups = len(df)
    if n_groups == 0:
        img.save(out_path)
        return

    group_slot_w = chart_w / n_groups
    bar_gap = 14
    bar_w = int(min(78, group_slot_w * 0.18))
    group_inner_w = bar_w * len(algos) + bar_gap * (len(algos) - 1)
    group_centers = []

    for i in range(n_groups):
        group_center = chart_left + group_slot_w * (i + 0.5)
        group_centers.append(group_center)
        group_start = group_center - group_inner_w / 2.0

        for j, algo in enumerate(algos):
            v = values[algo][i]
            x0 = int(group_start + j * (bar_w + bar_gap))
            x1 = x0 + bar_w
            y0 = y_to_px(v)

            draw.rectangle([(x0, y0), (x1, chart_bottom)], fill=algo_colors[algo], outline="black", width=2)
            value_text = f"{v:.2f}"
            draw.text((x0 + max(2, (bar_w - text_w(value_text, font_value)) // 2), y0 - 26), value_text, fill="black", font=font_value)
            algo_x = x0 + max(2, (bar_w - text_w(algo, font_algo)) // 2)
            draw.text((algo_x, chart_bottom + 18), algo, fill="#333333", font=font_algo)

        # Major x-group label
        group_label = conditions[i]
        gl_w = text_w(group_label, font_group)
        draw.text((int(group_center - gl_w / 2), chart_bottom + 58), group_label, fill="black", font=font_group)

    if SHOW_WIN_RATE_LINE:
        # Draw win-rate line on right axis.
        line_points = []
        for cx, wr in zip(group_centers, win_rates):
            if np.isnan(wr):
                line_points.append(None)
            else:
                line_points.append((int(cx), y_win_to_px(wr), float(wr)))

        draw_antialiased_line_and_markers(
            base_img=img,
            points_xy=[None if pt is None else (pt[0], pt[1]) for pt in line_points],
            color=win_color,
            line_width=3,
            marker_radius=6,
            scale=LINE_ANTIALIAS_SCALE,
        )

        for pt in line_points:
            if pt is None:
                continue
            x, y, wr = pt
            label = f"{wr:.1f}%"
            draw.text((x - int(text_w(label, font_value) / 2), y - 30), label, fill=win_color, font=font_value)

    if SHOW_GAIN_LINE and has_gain_data:
        # Draw gain line on secondary right axis.
        line_points = []
        for cx, gv in zip(group_centers, gains):
            if np.isnan(gv):
                line_points.append(None)
            else:
                line_points.append((int(cx), y_gain_to_px(gv), float(gv)))

        draw_antialiased_line_and_markers(
            base_img=img,
            points_xy=[None if pt is None else (pt[0], pt[1]) for pt in line_points],
            color=gain_color,
            line_width=3,
            marker_radius=6,
            scale=LINE_ANTIALIAS_SCALE,
        )

        for pt in line_points:
            if pt is None:
                continue
            x, y, gv = pt
            label = f"{gv:.1f}%"
            draw.text((x - int(text_w(label, font_value) / 2), y - 30), label, fill=gain_color, font=font_value)

    # Common-property line (e.g., NCCR_total > 2)
    common_vals = [str(v) for v in df["nccr_constraint"].dropna().unique().tolist()]
    if common_vals:
        common_text = common_vals[0] if len(common_vals) == 1 else " / ".join(common_vals)
        common_line = f"Common Constraint: {common_text}"
        cw = text_w(common_line, font_common)
        common_y = min(height - 42, chart_bottom + COMMON_CONSTRAINT_Y_OFFSET)
        draw.text((int((width - cw) / 2), int(common_y)), common_line, fill="#222222", font=font_common)

    # Legend (fixed to top-right corner)
    legend_x = width - 235 - LEGEND_SHIFT_TO_CENTER
    legend_y = 26
    for idx, algo in enumerate(algos):
        y = legend_y + idx * 28
        draw.rectangle(
            [(legend_x, y), (legend_x + 18, y + 14)],
            fill=algo_colors[algo],
            outline="black",
            width=1,
        )
        draw.text((legend_x + 28, y - 2), algo, fill="black", font=font_legend)

    legend_cursor_y = legend_y + len(algos) * 28 + 8
    legend_line_gap = 24

    if SHOW_WIN_RATE_LINE:
        # Legend entry for win-rate line.
        y = legend_cursor_y
        draw.line([(legend_x, y + 8), (legend_x + 18, y + 8)], fill=win_color, width=3)
        draw.ellipse([(legend_x + 6, y + 2), (legend_x + 12, y + 14)], outline=win_color, fill=win_color, width=2)
        draw.text((legend_x + 28, y - 2), "NHEFT Win Rate", fill=win_color, font=font_legend)
        legend_cursor_y += legend_line_gap

    if SHOW_GAIN_LINE and has_gain_data:
        # Legend entry for gain line.
        y = legend_cursor_y
        draw.line([(legend_x, y + 8), (legend_x + 18, y + 8)], fill=gain_color, width=3)
        draw.ellipse([(legend_x + 6, y + 2), (legend_x + 12, y + 14)], outline=gain_color, fill=gain_color, width=2)
        draw.text((legend_x + 28, y - 2), "NHEFT Gain over DHEFT", fill=gain_color, font=font_legend)

    img.save(out_path)


def main():
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_dir = os.path.join(OUT_BASE_DIR, timestamp)
    os.makedirs(out_dir, exist_ok=True)

    rows = []

    for meta in SCENARIOS:
        exp_abs = os.path.join(THIS_DIR, meta["exp_dir"])
        latest_run = find_latest_run_dir(exp_abs)
        if not latest_run:
            raise RuntimeError(f"No run_* folder found under: {exp_abs}")

        summary_csv = os.path.join(latest_run, meta["summary_csv"])
        if not os.path.exists(summary_csv):
            raise RuntimeError(f"Summary CSV not found: {summary_csv}")

        sdf = pd.read_csv(summary_csv)
        if sdf.empty:
            raise RuntimeError(f"Summary CSV is empty: {summary_csv}")
        r = sdf.iloc[0]

        qualified_col = find_qualified_col(sdf.columns, meta["scenario"])
        if not qualified_col:
            raise RuntimeError(
                f"Cannot find qualified-runs column for {meta['scenario']} in {summary_csv}"
            )

        total_runs = ensure_int(r.get("total_runs", 0))
        algo_valid = ensure_int(r.get("algo_valid_runs", 0))
        qualified = ensure_int(r.get(qualified_col, 0))
        wins = ensure_int(r.get("wins_N_over_D", 0))
        win_rate = ensure_float(r.get("win_rate_N_over_D", np.nan))

        # Some legacy summaries might miss win_rate, fallback to wins/qualified.
        if np.isnan(win_rate) and qualified > 0:
            win_rate = wins / qualified

        row = {
            "scenario": meta["scenario"],
            "condition": meta["condition"],
            "nccr_constraint": "NCCR_total > 2",
            "exp_dir": meta["exp_dir"],
            "latest_run_dir": latest_run,
            "summary_csv": summary_csv,
            "total_runs": total_runs,
            "algo_valid_runs": algo_valid,
            "qualified_runs": qualified,
            "wins_N_over_D": wins,
            "win_rate_N_over_D": win_rate,
            "win_rate_percent": win_rate * 100.0 if not np.isnan(win_rate) else np.nan,
            "HEFT_mean": ensure_float(r.get("HEFT_mean", np.nan)),
            "gain_N_over_D_mean": ensure_float(r.get("gain_N_over_D_mean", np.nan)),
            "gain_N_over_D_median": ensure_float(r.get("gain_N_over_D_median", np.nan)),
            "DHEFT_mean": ensure_float(r.get("DHEFT_mean", np.nan)),
            "NHEFT_mean": ensure_float(r.get("NHEFT_mean", np.nan)),
        }
        row["wins_display"] = (
            f"{wins}/{qualified} ({row['win_rate_percent']:.2f}%)" if qualified > 0 else "0/0 (n/a)"
        )
        row["x_label"] = f"{meta['scenario']}\n{meta['condition']}"
        rows.append(row)

    df = pd.DataFrame(rows)
    df = df.sort_values("scenario").reset_index(drop=True)
    df["latest_run_dir_rel"] = df["latest_run_dir"].apply(rel_to_project)
    df["summary_csv_rel"] = df["summary_csv"].apply(rel_to_project)

    # Save aggregated table.
    out_csv = os.path.join(out_dir, "e27_e28_e29_latest_summary.csv")
    df.to_csv(out_csv, index=False)

    # Plot 0: grouped makespan mean comparison (b7/b8/b9 x HEFT/DHEFT/NHEFT).
    out_makespan_grouped = os.path.join(out_dir, "makespan_mean_comparison.png")
    draw_grouped_makespan_chart(df=df, out_path=out_makespan_grouped)

    # Plot 1: NHEFT win rate (%) against DHEFT by scenario.
    out_bar_win = os.path.join(out_dir, "e27_e28_e29_win_rate_bar.png")
    draw_bar(
        df=df,
        y_col="win_rate_percent",
        y_label="NHEFT Win Rate over DHEFT (%)",
        title="E27/E28/E29 Latest Runs (NCCR_total > 2)",
        out_path=out_bar_win,
        ylim_min=0.0,
    )

    # Plot 2: median gain (%) by scenario.
    out_bar_gain = os.path.join(out_dir, "e27_e28_e29_gain_median_bar.png")
    draw_bar(
        df=df,
        y_col="gain_N_over_D_median",
        y_label="NHEFT Gain over DHEFT Median (%)",
        title="E27/E28/E29 Median Gain by Scenario",
        out_path=out_bar_gain,
        ylim_min=min(0.0, float(df["gain_N_over_D_median"].min()) - 1.0),
    )

    # Also export a compact text summary.
    out_txt = os.path.join(out_dir, "summary.txt")
    with open(out_txt, "w") as f:
        f.write("E27/E28/E29 latest-run aggregation\n")
        f.write(f"generated_at: {timestamp}\n\n")
        f.write("Data Sources (which experiment folder/run folder was used)\n")
        for _, rsrc in df.iterrows():
            run_dir = str(rsrc["latest_run_dir"])
            run_name = os.path.basename(run_dir.rstrip(os.sep))
            exp_dir = str(rsrc["exp_dir"])
            scenario = str(rsrc["scenario"])
            condition = str(rsrc["condition"])
            summary_csv = str(rsrc["summary_csv"])
            logs_dir = os.path.join(run_dir, "logs")
            f.write(f"[{scenario}] exp={exp_dir}, condition={condition}\n")
            f.write(f"  run_folder: {run_name}\n")
            f.write(f"  run_path: {rel_to_project(run_dir)}\n")
            f.write(f"  logs_path: {rel_to_project(logs_dir)}\n")
            f.write(f"  summary_csv: {rel_to_project(summary_csv)}\n")
        f.write("\n")
        f.write("Aggregated Metrics\n")
        f.write(df[[
            "scenario",
            "condition",
            "qualified_runs",
            "wins_display",
            "gain_N_over_D_median",
            "gain_N_over_D_mean",
            "DHEFT_mean",
            "NHEFT_mean",
            "latest_run_dir_rel",
        ]].to_string(index=False))
        f.write("\n")

    print("=== E27/E28/E29 latest aggregation completed ===")
    print(f"Output directory: {out_dir}")
    print(f"Summary CSV: {out_csv}")
    print(f"Grouped makespan chart: {out_makespan_grouped}")
    print(f"Win-rate bar: {out_bar_win}")
    print(f"Median-gain bar: {out_bar_gain}")
    print(f"Text summary: {out_txt}")


if __name__ == "__main__":
    main()
