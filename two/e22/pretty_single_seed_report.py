#!/usr/bin/env python3
"""
Generate a readable single-seed report in execution order.

Usage:
  python3 pretty_single_seed_report.py <target_folder> [algorithm]

Examples:
  python3 pretty_single_seed_report.py debug_6347
  python3 pretty_single_seed_report.py debug_6347 ""
  python3 pretty_single_seed_report.py debug_6347 dheft
  python3 pretty_single_seed_report.py debug_6347 nheft
"""

import re
import sys
from collections import defaultdict
from pathlib import Path


DHEFT_START_RE = re.compile(
    r"^\[DHEFT-START\]\s+Scheduling\s+VNF=(?P<vnf>\d+),(?:\s*type=(?P<type>-?\d+),)?.*?candidateVCPU=(?P<count>\d+)"
)
DHEFT_CAND_RE = re.compile(
    r"^\[DHEFT-CAND\]\s+VNF=(?P<vnf>\d+),(?:\s*type=(?P<type>-?\d+),)?.*?->\s+vCPU=(?P<vcpu>[^,]+).*?,\s+est=(?P<est>[-\d.]+)(?:,\s+dlTime=(?P<dl>[-\d.]+))?,\s+execTime=(?P<exec>[-\d.]+),\s+finish=(?P<finish>[-\d.]+)"
)
DHEFT_SELECT_RE = re.compile(
    r"^\[DHEFT-SELECT\]\s+VNF=(?P<vnf>\d+),(?:\s*type=(?P<type>-?\d+),)?.*?->\s+vCPU=(?P<vcpu>[^,]+).*?,\s+start=(?P<start>[-\d.]+),\s+finish=(?P<finish>[-\d.]+)"
)
DHEFT_COMMIT_RE = re.compile(
    r"^\[DHEFT-COMMIT\]\s+VNF=(?P<vnf>\d+)\s+target=(?P<target>\S+)\s+dlStart=(?P<dlStart>[-\d.]+)\s+dlFinish=(?P<dlFinish>[-\d.]+)\s+fromRepo=(?P<fromRepo>true|false)\s+sourceVM=(?P<sourceVM>\S+)"
)
DHEFT_DL_SELECT_RE = re.compile(
    r"^\[DHEFT-DL-SELECT\]\s+VNF=(?P<vnf>\d+),.*?target=vCPU=(?P<target>[^,]+),.*?selectedFinish=(?P<dlFinish>[-\d.]+)\s+selectedStart=(?P<dlStart>[-\d.]+)\s+fromRepo=(?P<fromRepo>true|false)\s+sourceVM=(?P<sourceVM>\S+)"
)

NHEFT_START_RE = re.compile(
    r"^\[NHEFT-START\]\s+Scheduling\s+VNF=(?P<vnf>\d+),(?:\s*type=(?P<type>-?\d+),)?.*?candidateVCPU=(?P<count>\d+)"
)
NHEFT_CAND_RE = re.compile(
    r"^\[NHEFT-CAND\]\s+VNF=(?P<vnf>\d+),(?:\s*type=(?P<type>-?\d+),)?.*?->\s+vCPU=(?P<vcpu>[^,]+).*?,\s+est=(?P<est>[-\d.]+)(?:,\s+dlTime=(?P<dl>[-\d.]+))?,\s+execTime=(?P<exec>[-\d.]+),\s+finish=(?P<finish>[-\d.]+)"
)
NHEFT_SELECT_RE = re.compile(
    r"^\[NHEFT-SELECT\]\s+VNF=(?P<vnf>\d+),(?:\s*type=(?P<type>-?\d+),)?.*?->\s+vCPU=(?P<vcpu>[^,]+).*?,\s+start=(?P<start>[-\d.]+),\s+finish=(?P<finish>[-\d.]+)"
)
NHEFT_DEBUG_RE = re.compile(
    r"^\[NHEFT-DEBUG\]\s+VNF=(?P<vnf>\d+)\s+target=(?P<target>\S+)\s+planStart=(?P<planStart>[-\d.]+)\s+planFinish=(?P<planFinish>[-\d.]+)\s+fromRepo=(?P<fromRepo>true|false)"
)
NHEFT_COMMIT_RE = re.compile(
    r"^\[NHEFT-COMMIT\]\s+VNF=(?P<vnf>\d+)\s+target=(?P<target>\S+)\s+dlStart=(?P<dlStart>[-\d.]+)\s+dlFinish=(?P<dlFinish>[-\d.]+)\s+fromRepo=(?P<fromRepo>true|false)\s+dynamic=(?P<dynamic>true|false)\s+sourceVM=(?P<sourceVM>\S+)"
)

DHEFT_FINAL_RE = re.compile(r"^\[DHEFT\]makespan:(?P<val>[-\d.]+)")
NHEFT_FINAL_RE = re.compile(r"^\[NHEFT\]makespan:(?P<val>[-\d.]+)")
CP_BEGIN_RE = re.compile(r"^\[(?P<algo>DHEFT|NHEFT)-CP\]\s+BEGIN\s+size=(?P<size>\d+)")
CP_STEP_RE = re.compile(
    r"^\[(?P<algo>DHEFT|NHEFT)-CP\]\s+#(?P<idx>\d+)\s+VNF=(?P<vnf>\d+)\s+type=(?P<type>-?\d+)\s+pred=(?P<pred>-?\d+)\s+edgeData=(?P<edge>\d+)\s+com=(?P<com>[-+\d.eE]+)\s+arrival=(?P<arrival>[-+\d.eE]+)\s+dlFinish=(?P<dlFinish>[-+\d.eE]+)\s+start=(?P<start>[-+\d.eE]+)\s+finish=(?P<finish>[-+\d.eE]+)\s+wait=(?P<wait>[-+\d.eE]+)\s+vCPU=(?P<vcpu>\S+)"
)
CP_SUMMARY_RE = re.compile(
    r"^\[(?P<algo>DHEFT|NHEFT)-CP\]\s+SUMMARY\s+makespan=(?P<makespan>[-+\d.eE]+)\s+totalExec=(?P<totalExec>[-+\d.eE]+)\s+totalCom=(?P<totalCom>[-+\d.eE]+)\s+totalWait=(?P<totalWait>[-+\d.eE]+)"
)


def find_latest_log(target_dir: Path) -> Path:
    candidates = []
    for base in (target_dir, target_dir / "logs"):
        if not base.exists():
            continue
        candidates.extend([p for p in base.glob("*.log") if p.is_file()])

    if not candidates:
        raise FileNotFoundError(f"No .log file found in: {target_dir}")

    candidates.sort(key=lambda p: p.stat().st_mtime)
    return candidates[-1]


def ordered_vnfs(order, data):
    seen = set(order)
    missing = sorted(v for v in data.keys() if v not in seen)
    return order + missing


def parse_dheft(log_path: Path):
    lines = log_path.read_text(encoding="utf-8", errors="ignore").splitlines()

    data = defaultdict(
        lambda: {
            "type": None,
            "start_events": [],
            "cands": [],
            "select": None,
            "commit": None,
            "dl_select": {},
        }
    )
    order = []
    seen = set()
    final_makespan = None

    def mark(vnf):
        if vnf not in seen:
            seen.add(vnf)
            order.append(vnf)

    for idx, line in enumerate(lines, 1):
        m = DHEFT_FINAL_RE.match(line)
        if m:
            final_makespan = float(m.group("val"))
            continue

        m = DHEFT_START_RE.match(line)
        if m:
            vnf = int(m.group("vnf"))
            mark(vnf)
            if m.group("type") is not None:
                data[vnf]["type"] = int(m.group("type"))
            data[vnf]["start_events"].append(
                {
                    "line": idx,
                    "raw": line.strip(),
                    "candidate_count": int(m.group("count")),
                }
            )
            continue

        m = DHEFT_CAND_RE.match(line)
        if m:
            vnf = int(m.group("vnf"))
            mark(vnf)
            if m.group("type") is not None:
                data[vnf]["type"] = int(m.group("type"))
            data[vnf]["cands"].append(
                {
                    "line": idx,
                    "raw": line.strip(),
                    "vcpu": m.group("vcpu"),
                    "est": float(m.group("est")),
                    "dl": float(m.group("dl")) if m.group("dl") is not None else None,
                    "exec": float(m.group("exec")),
                    "finish": float(m.group("finish")),
                }
            )
            continue

        m = DHEFT_SELECT_RE.match(line)
        if m:
            vnf = int(m.group("vnf"))
            mark(vnf)
            if m.group("type") is not None:
                data[vnf]["type"] = int(m.group("type"))
            data[vnf]["select"] = {
                "line": idx,
                "raw": line.strip(),
                "vcpu": m.group("vcpu"),
                "start": float(m.group("start")),
                "finish": float(m.group("finish")),
            }
            continue

        m = DHEFT_COMMIT_RE.match(line)
        if m:
            vnf = int(m.group("vnf"))
            mark(vnf)
            data[vnf]["commit"] = {
                "line": idx,
                "raw": line.strip(),
                "target": m.group("target"),
                "dlStart": float(m.group("dlStart")),
                "dlFinish": float(m.group("dlFinish")),
                "fromRepo": m.group("fromRepo") == "true",
                "sourceVM": m.group("sourceVM"),
            }
            continue

        m = DHEFT_DL_SELECT_RE.match(line)
        if m:
            vnf = int(m.group("vnf"))
            target = m.group("target")
            data[vnf]["dl_select"][target] = {
                "line": idx,
                "raw": line.strip(),
                "target": target,
                "dlStart": float(m.group("dlStart")),
                "dlFinish": float(m.group("dlFinish")),
                "fromRepo": m.group("fromRepo") == "true",
                "sourceVM": m.group("sourceVM"),
            }

    return data, ordered_vnfs(order, data), final_makespan, lines


def parse_nheft(log_path: Path):
    lines = log_path.read_text(encoding="utf-8", errors="ignore").splitlines()

    data = defaultdict(
        lambda: {
            "type": None,
            "start_events": [],
            "cands": [],
            "select": None,
            "debug": [],
            "commit": None,
        }
    )
    order = []
    seen = set()
    final_makespan = None

    def mark(vnf):
        if vnf not in seen:
            seen.add(vnf)
            order.append(vnf)

    for idx, line in enumerate(lines, 1):
        m = NHEFT_FINAL_RE.match(line)
        if m:
            final_makespan = float(m.group("val"))
            continue

        m = NHEFT_START_RE.match(line)
        if m:
            vnf = int(m.group("vnf"))
            mark(vnf)
            if m.group("type") is not None:
                data[vnf]["type"] = int(m.group("type"))
            data[vnf]["start_events"].append(
                {
                    "line": idx,
                    "raw": line.strip(),
                    "candidate_count": int(m.group("count")),
                }
            )
            continue

        m = NHEFT_CAND_RE.match(line)
        if m:
            vnf = int(m.group("vnf"))
            mark(vnf)
            if m.group("type") is not None:
                data[vnf]["type"] = int(m.group("type"))
            data[vnf]["cands"].append(
                {
                    "line": idx,
                    "raw": line.strip(),
                    "vcpu": m.group("vcpu"),
                    "est": float(m.group("est")),
                    "dl": float(m.group("dl")) if m.group("dl") is not None else None,
                    "exec": float(m.group("exec")),
                    "finish": float(m.group("finish")),
                }
            )
            continue

        m = NHEFT_SELECT_RE.match(line)
        if m:
            vnf = int(m.group("vnf"))
            mark(vnf)
            if m.group("type") is not None:
                data[vnf]["type"] = int(m.group("type"))
            data[vnf]["select"] = {
                "line": idx,
                "raw": line.strip(),
                "vcpu": m.group("vcpu"),
                "start": float(m.group("start")),
                "finish": float(m.group("finish")),
            }
            continue

        m = NHEFT_DEBUG_RE.match(line)
        if m:
            vnf = int(m.group("vnf"))
            mark(vnf)
            data[vnf]["debug"].append(
                {
                    "line": idx,
                    "raw": line.strip(),
                    "target": m.group("target"),
                    "planStart": float(m.group("planStart")),
                    "planFinish": float(m.group("planFinish")),
                    "fromRepo": m.group("fromRepo") == "true",
                }
            )
            continue

        m = NHEFT_COMMIT_RE.match(line)
        if m:
            vnf = int(m.group("vnf"))
            mark(vnf)
            data[vnf]["commit"] = {
                "line": idx,
                "raw": line.strip(),
                "target": m.group("target"),
                "dlStart": float(m.group("dlStart")),
                "dlFinish": float(m.group("dlFinish")),
                "fromRepo": m.group("fromRepo") == "true",
                "dynamic": m.group("dynamic") == "true",
                "sourceVM": m.group("sourceVM"),
            }

    return data, ordered_vnfs(order, data), final_makespan, lines


def render_dheft(report_title: str, log_name: str, lines, final_makespan, data, vnfs):
    out = []
    out.append(f"# {report_title}")
    out.append("")
    out.append(f"- 输入日志: `{log_name}`")
    out.append(f"- 总行数: **{len(lines)}**")
    if final_makespan is not None:
        out.append(f"- 最终 makespan: **{final_makespan:.4f} s**")
    out.append(f"- 共梳理 VNF 数: **{len(vnfs)}**")
    out.append("- VNF 顺序: **按日志首次出现顺序（执行顺序）**")
    out.append("")

    for vnf in vnfs:
        info = data[vnf]
        sel = info["select"]
        cands = info["cands"]
        starts = info["start_events"]
        commit = resolve_commit("DHEFT", info)

        out.append(vnf_heading(vnf, info.get("type")))
        if starts:
            out.append(f"- 进入调度时候选数: **{starts[0]['candidate_count']}**")
        if sel:
            out.append(f"- 选择结果: **{sel['vcpu']}**")
            out.append(f"- start: **{sel['start']:.4f}**")
            out.append(f"- finish: **{sel['finish']:.4f}**")
        else:
            out.append("- 选择结果: **未解析到 SELECT 记录**")

        if commit:
            out.append(f"- 下载开始: **{commit['dlStart']:.4f}**")
            out.append(f"- 下载完成: **{commit['dlFinish']:.4f}**")
            out.append(f"- fromRepo: **{str(commit['fromRepo']).lower()}**")

        if cands:
            out.append("")
            out.append("| 候选vCPU | EST | 下载时间DL | 执行时间Exec | 完成时间Finish |")
            out.append("|---|---:|---:|---:|---:|")
            for c in cands:
                dl = "-" if c["dl"] is None else f"{c['dl']:.4f}"
                out.append(f"| {c['vcpu']} | {c['est']:.4f} | {dl} | {c['exec']:.4f} | {c['finish']:.4f} |")

        if starts:
            out.append("")
            out.append("### 原始触发行")
            out.append(f"- `{starts[0]['raw']}`")

        if sel:
            out.append("")
            out.append("### 原始选择行")
            out.append(f"- `{sel['raw']}`")

        if commit:
            out.append("")
            out.append("### 原始提交行")
            out.append(f"- `{commit['raw']}`")

        out.append("")

    return "\n".join(out)


def render_nheft(report_title: str, log_name: str, lines, final_makespan, data, vnfs):
    out = []
    out.append(f"# {report_title}")
    out.append("")
    out.append(f"- 输入日志: `{log_name}`")
    out.append(f"- 总行数: **{len(lines)}**")
    if final_makespan is not None:
        out.append(f"- 最终 makespan: **{final_makespan:.4f} s**")
    out.append(f"- 共梳理 VNF 数: **{len(vnfs)}**")
    out.append("- VNF 顺序: **按日志首次出现顺序（执行顺序）**")
    out.append("")

    for vnf in vnfs:
        info = data[vnf]
        out.append(vnf_heading(vnf, info.get("type")))

        if info["start_events"]:
            out.append(f"- 进入调度时候选数: **{info['start_events'][0]['candidate_count']}**")

        if info["select"]:
            sel = info["select"]
            out.append(f"- 选择结果: **{sel['vcpu']}**")
            out.append(f"- start: **{sel['start']:.4f}**")
            out.append(f"- finish: **{sel['finish']:.4f}**")
        else:
            out.append("- 选择结果: **未解析到 SELECT 记录**")

        if info["commit"]:
            c = info["commit"]
            out.append(f"- 下载开始: **{c['dlStart']:.4f}**")
            out.append(f"- 下载完成: **{c['dlFinish']:.4f}**")
            out.append(f"- fromRepo: **{str(c['fromRepo']).lower()}**")
            out.append(f"- dynamic: **{str(c['dynamic']).lower()}**")
            out.append(f"- sourceVM: **{c['sourceVM']}**")

        if info["debug"]:
            d = info["debug"][0]
            out.append(f"- planStart: **{d['planStart']:.4f}**")
            out.append(f"- planFinish: **{d['planFinish']:.4f}**")
            out.append(f"- fromRepo(plan): **{str(d['fromRepo']).lower()}**")

        if info["cands"]:
            out.append("")
            out.append("| 候选vCPU | EST | 下载时间DL | 执行时间Exec | 完成时间Finish |")
            out.append("|---|---:|---:|---:|---:|")
            for c in info["cands"]:
                dl = "-" if c["dl"] is None else f"{c['dl']:.4f}"
                out.append(f"| {c['vcpu']} | {c['est']:.4f} | {dl} | {c['exec']:.4f} | {c['finish']:.4f} |")

        if info["start_events"]:
            out.append("")
            out.append("### 原始触发行")
            out.append(f"- `{info['start_events'][0]['raw']}`")

        if info["select"]:
            out.append("")
            out.append("### 原始选择行")
            out.append(f"- `{info['select']['raw']}`")

        if info["commit"]:
            out.append("")
            out.append("### 原始提交行")
            out.append(f"- `{info['commit']['raw']}`")

        out.append("")

    return "\n".join(out)


def parse_dheft_nheft(log_path: Path):
    lines = log_path.read_text(encoding="utf-8", errors="ignore").splitlines()

    data = {
        "DHEFT": defaultdict(
            lambda: {
                "type": None,
                "select": None,
                "cands": {},
                "debug": {},
                "commit": None,
                "dl_select": {},
            }
        ),
        "NHEFT": defaultdict(
            lambda: {
                "type": None,
                "select": None,
                "cands": {},
                "debug": {},
                "commit": None,
            }
        ),
    }
    makespans = {}
    critical_paths = {
        "DHEFT": {"size": None, "steps": [], "summary": None},
        "NHEFT": {"size": None, "steps": [], "summary": None},
    }
    vnf_order = []
    seen = set()

    def mark(vnf):
        if vnf not in seen:
            seen.add(vnf)
            vnf_order.append(vnf)

    for idx, line in enumerate(lines, 1):
        m = CP_BEGIN_RE.match(line)
        if m:
            algo = m.group("algo")
            critical_paths[algo]["size"] = int(m.group("size"))
            continue

        m = CP_STEP_RE.match(line)
        if m:
            algo = m.group("algo")
            critical_paths[algo]["steps"].append(
                {
                    "idx": int(m.group("idx")),
                    "vnf": int(m.group("vnf")),
                    "type": int(m.group("type")),
                    "pred": int(m.group("pred")),
                    "edge": int(m.group("edge")),
                    "com": float(m.group("com")),
                    "arrival": float(m.group("arrival")),
                    "dlFinish": float(m.group("dlFinish")),
                    "start": float(m.group("start")),
                    "finish": float(m.group("finish")),
                    "wait": float(m.group("wait")),
                    "vcpu": m.group("vcpu"),
                    "line": idx,
                }
            )
            continue

        m = CP_SUMMARY_RE.match(line)
        if m:
            algo = m.group("algo")
            critical_paths[algo]["summary"] = {
                "makespan": float(m.group("makespan")),
                "totalExec": float(m.group("totalExec")),
                "totalCom": float(m.group("totalCom")),
                "totalWait": float(m.group("totalWait")),
                "line": idx,
            }
            continue

        m = DHEFT_FINAL_RE.match(line)
        if m:
            makespans["DHEFT"] = float(m.group("val"))
            continue
        m = NHEFT_FINAL_RE.match(line)
        if m:
            makespans["NHEFT"] = float(m.group("val"))
            continue

        m = DHEFT_SELECT_RE.match(line)
        if m:
            vnf = int(m.group("vnf"))
            mark(vnf)
            if m.group("type") is not None:
                data["DHEFT"][vnf]["type"] = int(m.group("type"))
            data["DHEFT"][vnf]["select"] = {
                "line": idx,
                "raw": line.strip(),
                "vcpu": m.group("vcpu"),
                "start": float(m.group("start")),
                "finish": float(m.group("finish")),
            }
            continue

        m = NHEFT_SELECT_RE.match(line)
        if m:
            vnf = int(m.group("vnf"))
            mark(vnf)
            if m.group("type") is not None:
                data["NHEFT"][vnf]["type"] = int(m.group("type"))
            data["NHEFT"][vnf]["select"] = {
                "line": idx,
                "raw": line.strip(),
                "vcpu": m.group("vcpu"),
                "start": float(m.group("start")),
                "finish": float(m.group("finish")),
            }
            continue

        m = DHEFT_CAND_RE.match(line)
        if m:
            vnf = int(m.group("vnf"))
            vcpu = m.group("vcpu")
            if m.group("type") is not None:
                data["DHEFT"][vnf]["type"] = int(m.group("type"))
            data["DHEFT"][vnf]["cands"][vcpu] = {
                "line": idx,
                "raw": line.strip(),
                "vcpu": vcpu,
                "est": float(m.group("est")),
                "dl": float(m.group("dl")) if m.group("dl") is not None else None,
                "exec": float(m.group("exec")),
                "finish": float(m.group("finish")),
            }
            continue

        m = DHEFT_COMMIT_RE.match(line)
        if m:
            vnf = int(m.group("vnf"))
            data["DHEFT"][vnf]["commit"] = {
                "line": idx,
                "raw": line.strip(),
                "target": m.group("target"),
                "dlStart": float(m.group("dlStart")),
                "dlFinish": float(m.group("dlFinish")),
                "fromRepo": m.group("fromRepo") == "true",
                "sourceVM": m.group("sourceVM"),
            }
            continue

        m = DHEFT_DL_SELECT_RE.match(line)
        if m:
            vnf = int(m.group("vnf"))
            target = m.group("target")
            data["DHEFT"][vnf]["dl_select"][target] = {
                "line": idx,
                "raw": line.strip(),
                "target": target,
                "dlStart": float(m.group("dlStart")),
                "dlFinish": float(m.group("dlFinish")),
                "fromRepo": m.group("fromRepo") == "true",
                "sourceVM": m.group("sourceVM"),
            }
            continue

        m = NHEFT_CAND_RE.match(line)
        if m:
            vnf = int(m.group("vnf"))
            vcpu = m.group("vcpu")
            if m.group("type") is not None:
                data["NHEFT"][vnf]["type"] = int(m.group("type"))
            data["NHEFT"][vnf]["cands"][vcpu] = {
                "line": idx,
                "raw": line.strip(),
                "vcpu": vcpu,
                "est": float(m.group("est")),
                "dl": float(m.group("dl")) if m.group("dl") is not None else None,
                "exec": float(m.group("exec")),
                "finish": float(m.group("finish")),
            }
            continue

        m = NHEFT_DEBUG_RE.match(line)
        if m:
            vnf = int(m.group("vnf"))
            target = m.group("target")
            data["NHEFT"][vnf]["debug"][target] = {
                "line": idx,
                "raw": line.strip(),
                "target": target,
                "planStart": float(m.group("planStart")),
                "planFinish": float(m.group("planFinish")),
                "fromRepo": m.group("fromRepo") == "true",
            }
            continue

        m = NHEFT_COMMIT_RE.match(line)
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

    return data, makespans, vnf_order, lines, critical_paths


def fmt_time(v):
    return "-" if v is None else f"{v:.4f}"


def resolve_commit(algo, info):
    commit = info.get("commit")
    if commit is not None:
        return commit

    if algo == "DHEFT":
        sel = info.get("select")
        dl_select = info.get("dl_select", {})
        if sel is not None:
            target = sel["vcpu"]
            if target in dl_select:
                return dl_select[target]
    return None


def describe_download_source(algo, cand, commit):
    if algo == "NHEFT":
        if commit is None:
            if cand is not None and cand.get("dl") == 0.0:
                return "无下载/已复用(推断)", "-"
            return "未知", "-"
        from_repo = str(commit["fromRepo"]).lower()
        if commit["fromRepo"]:
            return "repo", from_repo
        source_vm = commit["sourceVM"]
        if source_vm and source_vm.lower() != "null":
            return f"vm:{source_vm}", from_repo
        return "vm(未知)", from_repo

    if commit is not None:
        from_repo = str(commit["fromRepo"]).lower()
        if commit["fromRepo"]:
            return "repo", from_repo
        source_vm = commit.get("sourceVM")
        if source_vm and source_vm.lower() != "null":
            return f"vm:{source_vm}", from_repo
        return "vm(未知)", from_repo

    # 旧 DHEFT 日志没有 commit/source 字段，只能基于 dlTime 做弱推断。
    if cand is not None and cand.get("dl") == 0.0:
        return "无下载/已复用(推断)", "-"
    return "日志未区分(repo或VM)", "-"


def vnf_heading(vnf, vnf_type):
    if vnf_type is None:
        return f"## VNF {vnf}"
    return f"## VNF {vnf} (type={vnf_type})"


def merged_vnf_type(dheft_info, nheft_info):
    t_d = None if dheft_info is None else dheft_info.get("type")
    t_n = None if nheft_info is None else nheft_info.get("type")
    if t_d is not None and t_n is not None:
        if t_d == t_n:
            return t_d
        return f"dheft={t_d},nheft={t_n}"
    if t_d is not None:
        return t_d
    return t_n


def render_merged_vnf_section(vnf, dheft_info, nheft_info):
    out = []
    out.append(vnf_heading(vnf, merged_vnf_type(dheft_info, nheft_info)))
    out.append("")
    out.append("| 算法 | vCPU | est | 下载时长 | 下载来源 | fromRepo | execTime | 开始时间 | 结束时间 | planStart | planFinish | dlStart | dlFinish |")
    out.append("|---|---|---:|---:|---|---|---:|---:|---:|---:|---:|---:|---:|")

    for algo, info in (("DHEFT", dheft_info), ("NHEFT", nheft_info)):
        if info is None or info["select"] is None:
            out.append(f"| {algo} | - | - | - | - | - | - | - | - | - | - | - | - |")
            continue

        sel = info["select"]
        cand = info["cands"].get(sel["vcpu"])
        debug = info["debug"].get(sel["vcpu"]) if info["debug"] else None
        commit = resolve_commit(algo, info)
        source_desc, from_repo_text = describe_download_source(algo, cand, commit)

        if commit is not None:
            download_time = commit["dlFinish"] - commit["dlStart"]
        else:
            download_time = cand["dl"] if cand is not None else None

        out.append(
            "| {algo} | {vcpu} | {est} | {download_time} | {source_desc} | {from_repo} | {exec} | {start} | {finish} | {plan_start} | {plan_finish} | {dl_start} | {dl_finish} |".format(
                algo=algo,
                vcpu=sel["vcpu"],
                est=fmt_time(cand["est"]) if cand is not None else "-",
                download_time=fmt_time(download_time),
                source_desc=source_desc,
                from_repo=from_repo_text,
                exec=fmt_time(cand["exec"]) if cand is not None else "-",
                start=fmt_time(sel["start"]),
                finish=fmt_time(sel["finish"]),
                plan_start=fmt_time(debug["planStart"]) if debug is not None else "-",
                plan_finish=fmt_time(debug["planFinish"]) if debug is not None else "-",
                dl_start=fmt_time(commit["dlStart"]) if commit is not None else "-",
                dl_finish=fmt_time(commit["dlFinish"]) if commit is not None else "-",
            )
        )
    out.append("")
    return "\n".join(out)


def render_critical_path_section(critical_paths):
    out = []
    out.append("## 关键路径摘要（Actual Critical Path）")
    out.append("")

    for algo in ("DHEFT", "NHEFT"):
        cp = critical_paths.get(algo, {})
        steps = cp.get("steps", [])
        summary = cp.get("summary")

        out.append(f"### {algo}")
        if not steps:
            out.append(f"- 未解析到 `{algo}-CP` 行（请用最新代码重跑该日志）。")
            out.append("")
            continue

        if summary is not None:
            out.append(
                "Summary: makespan={makespan:.4f}, totalExec={totalExec:.4f}, totalCom={totalCom:.4f}, totalWait={totalWait:.4f}".format(
                    makespan=summary["makespan"],
                    totalExec=summary["totalExec"],
                    totalCom=summary["totalCom"],
                    totalWait=summary["totalWait"],
                )
            )
        out.append("")
        out.append("| # | VNF(type) | pred | edgeData | com | arrival | dlFinish | start | finish | wait | vCPU |")
        out.append("|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|---|")
        for s in steps:
            out.append(
                "| {idx} | {vnf}({type}) | {pred} | {edge} | {com:.4f} | {arrival:.4f} | {dlFinish:.4f} | {start:.4f} | {finish:.4f} | {wait:.4f} | {vcpu} |".format(
                    idx=s["idx"],
                    vnf=s["vnf"],
                    type=s["type"],
                    pred=s["pred"],
                    edge=s["edge"],
                    com=s["com"],
                    arrival=s["arrival"],
                    dlFinish=s["dlFinish"],
                    start=s["start"],
                    finish=s["finish"],
                    wait=s["wait"],
                    vcpu=s["vcpu"],
                )
            )
        out.append("")

    return "\n".join(out)


def render_dheft_nheft_merged(report_title: str, log_name: str, lines, makespans, data, vnf_order, critical_paths):
    dheft_data = data["DHEFT"]
    nheft_data = data["NHEFT"]

    out = []
    out.append(f"# {report_title}")
    out.append("")
    out.append(f"- 输入日志: `{log_name}`")
    out.append(f"- 总行数: **{len(lines)}**")
    out.append(f"- DHEFT VNF 数: **{len(dheft_data)}**")
    out.append(f"- NHEFT VNF 数: **{len(nheft_data)}**")
    out.append(f"- 合并后 VNF 数: **{len(vnf_order)}**")
    out.append("- VNF 顺序: **按日志中首次 SELECT 出现顺序（执行顺序）**")
    out.append("- 表中仅保留每个 VNF 的关键选择结果与下载相关时间。")
    if "DHEFT" in makespans:
        out.append(f"- DHEFT makespan: **{makespans['DHEFT']:.4f} s**")
    if "NHEFT" in makespans:
        out.append(f"- NHEFT makespan: **{makespans['NHEFT']:.4f} s**")
    out.append("")
    out.append(render_critical_path_section(critical_paths))
    out.append("")

    for vnf in vnf_order:
        out.append(
            render_merged_vnf_section(
                vnf,
                dheft_data.get(vnf),
                nheft_data.get(vnf),
            )
        )

    return "\n".join(out)


def main():
    if len(sys.argv) < 2:
        print("用法: python3 pretty_single_seed_report.py <target_folder> [algorithm]")
        print("示例: python3 pretty_single_seed_report.py debug_6347")
        print('示例: python3 pretty_single_seed_report.py debug_6347 ""')
        print("示例: python3 pretty_single_seed_report.py debug_6347 dheft")
        print("示例: python3 pretty_single_seed_report.py debug_6347 nheft")
        sys.exit(1)

    this_dir = Path(__file__).resolve().parent
    target_folder = sys.argv[1]
    algo = sys.argv[2].strip().lower() if len(sys.argv) >= 3 else ""
    is_merged = algo in {"", "both", "merged", "all"}

    if (not is_merged) and (algo not in {"dheft", "nheft"}):
        print("algorithm 仅支持: dheft / nheft / 空(合并)")
        sys.exit(1)

    target_dir = this_dir / target_folder
    if not target_dir.exists() or not target_dir.is_dir():
        print(f"目标文件夹不存在: {target_dir}")
        sys.exit(1)

    log_path = find_latest_log(target_dir)
    if is_merged:
        out_path = target_dir / f"{log_path.stem}.dheft_nheft.ordered.pretty.md"
        data, makespans, vnf_order, lines, critical_paths = parse_dheft_nheft(log_path)
        report = render_dheft_nheft_merged(
            "E22(B2) DHEFT / NHEFT 单种子保序简化报告",
            log_path.name,
            lines,
            makespans,
            data,
            vnf_order,
            critical_paths,
        )
    elif algo == "dheft":
        out_path = target_dir / f"{log_path.stem}.{algo}.ordered.pretty.md"
        data, vnfs, final_makespan, lines = parse_dheft(log_path)
        report = render_dheft(
            "E22(B2) DHEFT 单种子调度梳理报告（按执行顺序）",
            log_path.name,
            lines,
            final_makespan,
            data,
            vnfs,
        )
    else:
        out_path = target_dir / f"{log_path.stem}.{algo}.ordered.pretty.md"
        data, vnfs, final_makespan, lines = parse_nheft(log_path)
        report = render_nheft(
            "E22(B2) NHEFT 单种子调度梳理报告（按执行顺序）",
            log_path.name,
            lines,
            final_makespan,
            data,
            vnfs,
        )

    out_path.write_text(report, encoding="utf-8")
    print(f"目标目录: {target_dir}")
    print(f"使用日志: {log_path}")
    print(f"已生成: {out_path}")


if __name__ == "__main__":
    main()
