#!/usr/bin/env python3
"""Format WinRM vs PSRP benchmark JSON into a human-readable text report."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Sequence

WIDTH = 78
BAR = "=" * WIDTH
THIN = "-" * WIDTH

KINIT_MODES = ("manual", "managed")
PLUGINS = ("winrm", "psrp")


def fmt_seconds(value: Any) -> str:
    try:
        return f"{float(value):.3f}"
    except (TypeError, ValueError):
        return "n/a"


def fmt_delta(winrm: Any, psrp: Any) -> str:
    try:
        delta = float(psrp) - float(winrm)
        return f"{delta:+.3f}"
    except (TypeError, ValueError):
        return "n/a"


def faster_plugin(winrm: Any, psrp: Any) -> str:
    try:
        w, p = float(winrm), float(psrp)
    except (TypeError, ValueError):
        return "n/a"
    if p < w:
        return "PSRP"
    if w < p:
        return "WinRM"
    return "tie"


def pad(text: str, width: int, align: str = "left") -> str:
    text = str(text)
    if len(text) >= width:
        return text[:width]
    if align == "right":
        return text.rjust(width)
    if align == "center":
        return text.center(width)
    return text.ljust(width)


def render_table(headers: Sequence[str], rows: Sequence[Sequence[str]], widths: Sequence[int]) -> List[str]:
    lines = [
        "  ".join(pad(h, w) for h, w in zip(headers, widths)),
        "  ".join(pad("-" * w, w) for w in widths),
    ]
    for row in rows:
        cells = []
        for idx, (cell, width) in enumerate(zip(row, widths)):
            align = "right" if idx > 0 else "left"
            cells.append(pad(cell, width, align))
        lines.append("  ".join(cells))
    return lines


def plugin_result(mode_results: Dict[str, Any], plugin: str) -> Dict[str, Any]:
    return mode_results.get(plugin) or {}


def section_mode(mode: str, mode_results: Dict[str, Any]) -> List[str]:
    winrm = plugin_result(mode_results, "winrm")
    psrp = plugin_result(mode_results, "psrp")
    if not winrm and not psrp:
        return [f"  (no results for {mode} kinit mode)", ""]

    lines = [
        THIN,
        f"  {mode.upper()} KINIT",
        THIN,
    ]

    task = winrm.get("task") or psrp.get("task") or "unknown"
    iterations = int(winrm.get("iterations") or psrp.get("iterations") or 0)
    lines.append(f"  Task .......... {task}")
    lines.append(f"  Iterations .... {iterations}")
    lines.append("")

    winrm_iters = winrm.get("iteration_seconds") or []
    psrp_iters = psrp.get("iteration_seconds") or []
    count = max(len(winrm_iters), len(psrp_iters), iterations)

    iter_rows: List[List[str]] = []
    for idx in range(count):
        w = winrm_iters[idx] if idx < len(winrm_iters) else None
        p = psrp_iters[idx] if idx < len(psrp_iters) else None
        label = str(idx + 1)
        if idx == 0:
            note = "cold"
        else:
            note = "warm"
        iter_rows.append([f"{label} ({note})", fmt_seconds(w), fmt_seconds(p), fmt_delta(w, p)])

    lines.append("  Per-iteration timings (seconds)")
    lines.extend(render_table(
        ["Iter", "WinRM", "PSRP", "Delta (PSRP-WinRM)"],
        iter_rows,
        [14, 10, 10, 18],
    ))
    lines.append("")

    summary_rows = [
        ["Total", fmt_seconds(winrm.get("total_seconds")), fmt_seconds(psrp.get("total_seconds")),
         fmt_delta(winrm.get("total_seconds"), psrp.get("total_seconds")),
         faster_plugin(winrm.get("total_seconds"), psrp.get("total_seconds"))],
        ["Cold (iter 1)", fmt_seconds(winrm.get("cold_seconds")), fmt_seconds(psrp.get("cold_seconds")),
         fmt_delta(winrm.get("cold_seconds"), psrp.get("cold_seconds")),
         faster_plugin(winrm.get("cold_seconds"), psrp.get("cold_seconds"))],
        ["Warm avg", fmt_seconds(winrm.get("warm_avg_seconds")), fmt_seconds(psrp.get("warm_avg_seconds")),
         fmt_delta(winrm.get("warm_avg_seconds"), psrp.get("warm_avg_seconds")),
         faster_plugin(winrm.get("warm_avg_seconds"), psrp.get("warm_avg_seconds"))],
    ]
    lines.append("  Summary")
    lines.extend(render_table(
        ["Metric", "WinRM", "PSRP", "Delta", "Faster"],
        summary_rows,
        [14, 10, 10, 10, 8],
    ))
    lines.append("")
    return lines


def section_final_matrix(host_entry: Dict[str, Any]) -> List[str]:
    results = host_entry.get("results") or {}
    lines = [
        THIN,
        "  FINAL MATRIX — total seconds",
        THIN,
    ]

    rows: List[List[str]] = []
    for mode in KINIT_MODES:
        mode_results = results.get(mode) or {}
        winrm = plugin_result(mode_results, "winrm")
        psrp = plugin_result(mode_results, "psrp")
        rows.append([
            mode.capitalize(),
            fmt_seconds(winrm.get("total_seconds")),
            fmt_seconds(psrp.get("total_seconds")),
            faster_plugin(winrm.get("total_seconds"), psrp.get("total_seconds")),
        ])

    lines.extend(render_table(
        ["Kinit mode", "WinRM", "PSRP", "Faster"],
        rows,
        [14, 10, 10, 8],
    ))
    lines.append("")
    return lines


def format_host(host_entry: Dict[str, Any]) -> List[str]:
    host = host_entry.get("host") or "unknown"
    ansible_host = host_entry.get("ansible_host") or host
    results = host_entry.get("results") or {}

    sample = {}
    for mode in KINIT_MODES:
        for plugin in PLUGINS:
            data = plugin_result(results.get(mode) or {}, plugin)
            if data:
                sample = data
                break
        if sample:
            break

    lines = [
        BAR,
        "  WinRM vs PSRP Connection Benchmark",
        BAR,
        f"  Host .......... {host}",
        f"  Target ........ {ansible_host}",
        f"  Auth .......... {sample.get('auth', 'kerberos')}",
        f"  Port .......... {sample.get('port', '5985')}",
        f"  Generated ..... {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}",
        "",
    ]

    for mode in KINIT_MODES:
        lines.extend(section_mode(mode, results.get(mode) or {}))

    lines.extend(section_final_matrix(host_entry))
    return lines


def format_report(payload: Dict[str, Any]) -> str:
    hosts = payload.get("hosts") or []
    if not hosts:
        return "\n".join([
            BAR,
            "  WinRM vs PSRP Connection Benchmark",
            BAR,
            "  No benchmark results found.",
            "",
        ])

    sections: List[str] = []
    for idx, host_entry in enumerate(hosts):
        if idx:
            sections.append("")
        sections.extend(format_host(host_entry))
    return "\n".join(sections)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "input",
        nargs="?",
        help="JSON input file (default: stdin)",
    )
    args = parser.parse_args()

    if args.input:
        with open(args.input, encoding="utf-8") as handle:
            payload = json.load(handle)
    else:
        payload = json.load(sys.stdin)

    sys.stdout.write(format_report(payload))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
