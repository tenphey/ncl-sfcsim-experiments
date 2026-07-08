#!/usr/bin/env python3
import re
import sys
from collections import defaultdict
from pathlib import Path


SELECT_RE = re.compile(
    r'^\[(?P<algo>DHEFT|NHEFT)-SELECT\]\s+VNF=(?P<vnf>\d+),.*?->\s+vCPU=(?P<vcpu>[^,]+).*?,\s+start=(?P<start>[-\d.]+),\s+finish=(?P<finish>[-\d.]+)'
)

CAND_RE = re.compile(
    r'^\[(?P<algo>DHEFT|NHEFT)-CAND\]\s+VNF=(?P<vnf>\d+),.*?->\s+vCPU=(?P<vcpu>[^,]+).*?,\s+est=(?P<est>[-\d.]+)(?:,\s+dlTime=(?P<dlTime>[-\d.]+))?,\s+execTime=(?P<execTime>[-\d.]+),\s+finish=(?P<finish>[-\d.]+)'
)

DEBUG_RE = re.compile(
    r'^\[(?P<algo>NHEFT)-DEBUG\]\s+VNF=(?P<vnf>\d+)\s+target=(?P<target>\S+)\s+planStart=(?P<planStart>[-\d.]+)\s+planFinish=(?P<planFinish>[-\d.]+)\s+fromRepo=(?P<fromRepo>true|false)'
)

COMMIT_RE = re.compile(
    r'^\[(?P<algo>NHEFT)-COMMIT\]\s+VNF=(?P<vnf>\d+)\s+target=(?P<target>\S+)\s+dlStart=(?P<dlStart>[-\d.]+)\s+dlFinish=(?P<dlFinish>[-\d.]+)\s+fromRepo=(?P<fromRepo>true|false)\s+dynamic=(?P<dynamic>true|false)\s+sourceVM=(?P<sourceVM>\S+)'
)

FINAL_MAKESPAN_RE = re.compile(
    r'^\[(?P<algo>DHEFT|NHEFT)\]makespan:(?P<val>[-\d.]+)'
)


def resolve_log_path(log_arg: str) -> Path:
    """
    Resolve log path for E12:
    1) direct/relative path
    2) search by basename under THIS_DIR/debug*/
    """
    p = Path(log_arg)
    if p.exists() and p.is_file():
        return p.resolve()

    this_dir = Path(__file__).resolve().parent
    candidate = (this_dir / log_arg)
    if candidate.exists() and candidate.is_file():
        return candidate.resolve()

    basename = p.name
    matches = []
    for dbg in sorted(this_dir.glob("debug*")):
        if not dbg.is_dir():
            continue
        hit = dbg / basename
        if hit.exists() and hit.is_file():
            matches.append(hit.resolve())

    if len(matches) == 1:
        return matches[0]
    if len(matches) > 1:
        print("找到多个同名日志，请改用更具体路径：")
        for m in matches:
            print(f"  - {m}")
        sys.exit(1)

    print(f"未找到日志文件: {log_arg}")
    print("已尝试：")
    print("  1) 直接路径/相对路径")
    print("  2) experiments/e12_vnf_type_max/debug*/<log_file>")
    sys.exit(1)


def parse_log(path: Path):
    lines = path.read_text(encoding="utf-8", errors="ignore").splitlines()

    data = defaultdict(lambda: defaultdict(lambda: {
        "select": None,
        "cands": {},
        "debug": {},
        "commit": None,
    }))  # algo -> vnf -> info
    makespans = {}
    vnf_order = []
    seen_vnfs = set()

    for idx, line in enumerate(lines, 1):
        m = FINAL_MAKESPAN_RE.match(line)
        if m:
            makespans[m.group("algo")] = float(m.group("val"))
            continue

        m = SELECT_RE.match(line)
        if m:
            algo = m.group("algo")
            vnf = int(m.group("vnf"))
            if vnf not in seen_vnfs:
                seen_vnfs.add(vnf)
                vnf_order.append(vnf)
            data[algo][vnf]["select"] = {
                "line": idx,
                "raw": line.strip(),
                "vcpu": m.group("vcpu"),
                "start": float(m.group("start")),
                "finish": float(m.group("finish")),
            }
            continue

        m = CAND_RE.match(line)
        if m:
            algo = m.group("algo")
            vnf = int(m.group("vnf"))
            data[algo][vnf]["cands"][m.group("vcpu")] = {
                "line": idx,
                "raw": line.strip(),
                "vcpu": m.group("vcpu"),
                "est": float(m.group("est")),
                "dlTime": float(m.group("dlTime")) if m.group("dlTime") is not None else None,
                "execTime": float(m.group("execTime")),
                "finish": float(m.group("finish")),
            }
            continue

        m = DEBUG_RE.match(line)
        if m:
            vnf = int(m.group("vnf"))
            data["NHEFT"][vnf]["debug"][m.group("target")] = {
                "line": idx,
                "raw": line.strip(),
                "target": m.group("target"),
                "planStart": float(m.group("planStart")),
                "planFinish": float(m.group("planFinish")),
                "fromRepo": m.group("fromRepo") == "true",
            }
            continue

        m = COMMIT_RE.match(line)
        if m:
            vnf = int(m.group("vnf"))
            data["NHEFT"][vnf]["commit"] = {
                "line": idx,
                "raw": line.strip(),
                "target": m.group("target"),
                "dlStart": float(m.group("dlStart")),
                "dlFinish": float(m.group("dlFinish")),
                "fromRepo": m.group("fromRepo") == "true",
                "dynamic": m.group("dynamic") == "true",
                "sourceVM": m.group("sourceVM"),
            }

    return data, makespans, lines, vnf_order


def fmt_time(value):
    if value is None:
        return "-"
    return f"{value:.4f}"


def render_vnf_section(vnf, dheft_info, nheft_info):
    out = []
    out.append(f"## VNF {vnf}")
    out.append("")
    out.append(
        "| 算法 | vCPU | est | 下载时长 | execTime | 开始时间 | 结束时间 | planStart | planFinish | dlStart | dlFinish |"
    )
    out.append("|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|")

    for algo, info in (("DHEFT", dheft_info), ("NHEFT", nheft_info)):
        if info is None or info["select"] is None:
            out.append(f"| {algo} | - | - | - | - | - | - | - | - | - | - |")
            continue

        sel = info["select"]
        cand = info["cands"].get(sel["vcpu"])
        debug = info["debug"].get(sel["vcpu"]) if info["debug"] else None
        commit = info["commit"]

        if algo == "NHEFT" and commit is not None:
            download_time = commit["dlFinish"] - commit["dlStart"]
        else:
            download_time = cand["dlTime"] if cand is not None else None

        out.append(
            "| {algo} | {vcpu} | {est} | {downloadTime} | {execTime} | {start} | {finish} | {planStart} | {planFinish} | {dlStart} | {dlFinish} |".format(
                algo=algo,
                vcpu=sel["vcpu"],
                est=fmt_time(cand["est"]) if cand is not None else "-",
                downloadTime=fmt_time(download_time),
                execTime=fmt_time(cand["execTime"]) if cand is not None else "-",
                start=fmt_time(sel["start"]),
                finish=fmt_time(sel["finish"]),
                planStart=fmt_time(debug["planStart"]) if debug is not None else "-",
                planFinish=fmt_time(debug["planFinish"]) if debug is not None else "-",
                dlStart=fmt_time(commit["dlStart"]) if commit is not None else "-",
                dlFinish=fmt_time(commit["dlFinish"]) if commit is not None else "-",
            )
        )
    out.append("")
    return "\n".join(out)


def main():
    if len(sys.argv) < 2:
        print("用法: python3 pretty_single_seed_report_dheft_nheft_ordered.py <log_file> [output_md]")
        sys.exit(1)

    log_path = resolve_log_path(sys.argv[1])
    out_path = Path(sys.argv[2]) if len(sys.argv) >= 3 else log_path.with_suffix(".dheft_nheft.ordered.pretty.md")

    data, makespans, raw_lines, vnf_order = parse_log(log_path)
    dheft_data = data.get("DHEFT", {})
    nheft_data = data.get("NHEFT", {})

    report = []
    report.append("# DHEFT / NHEFT 单种子保序简化报告 (E12)")
    report.append("")
    report.append(f"- 输入日志: `{log_path.name}`")
    report.append(f"- 日志路径: `{log_path}`")
    report.append(f"- 总行数: **{len(raw_lines)}**")
    report.append(f"- DHEFT VNF 数: **{len(dheft_data)}**")
    report.append(f"- NHEFT VNF 数: **{len(nheft_data)}**")
    report.append(f"- 合并后 VNF 数: **{len(vnf_order)}**")
    report.append("- 表中展示的是每个 VNF 被选中后的关键时间字段；NHEFT 的 `planStart/planFinish` 和 `dlStart/dlFinish` 只在对应日志里存在。")
    if "DHEFT" in makespans:
        report.append(f"- DHEFT makespan: **{makespans['DHEFT']:.4f} s**")
    if "NHEFT" in makespans:
        report.append(f"- NHEFT makespan: **{makespans['NHEFT']:.4f} s**")
    report.append("")

    for vnf in vnf_order:
        report.append(render_vnf_section(vnf, dheft_data.get(vnf), nheft_data.get(vnf)))

    out_path.write_text("\n".join(report), encoding="utf-8")
    print(f"已生成: {out_path}")


if __name__ == "__main__":
    main()
