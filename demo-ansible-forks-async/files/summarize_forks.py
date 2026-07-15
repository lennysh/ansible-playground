#!/usr/bin/env python3
"""Summarize fork monitor samples and inline snapshots into a readable report."""

from __future__ import annotations

import json
import sys
from collections import defaultdict
from pathlib import Path


def load_json(path: Path):
    if not path.is_file():
        return []
    data = json.loads(path.read_text())
    return data if isinstance(data, list) else []


def max_metric_for_phase(samples: list[dict], key: str) -> dict[str, int]:
    by_phase: dict[str, int] = defaultdict(int)
    for row in samples:
        phase = row.get("phase") or "unknown"
        by_phase[phase] = max(by_phase[phase], int(row.get(key, 0)))
    return dict(by_phase)


def main() -> int:
    samples_path = Path(sys.argv[1] if len(sys.argv) > 1 else "fork-samples.json")
    snapshots_path = Path(sys.argv[2] if len(sys.argv) > 2 else "fork-snapshots.json")
    report_path = Path(sys.argv[3] if len(sys.argv) > 3 else "fork-report.txt")

    samples = load_json(samples_path)
    snapshots = load_json(snapshots_path)

    configured = (samples[0] if samples else snapshots[0] if snapshots else {}).get(
        "configured_forks", "unknown"
    )
    worker_peaks = max_metric_for_phase(samples, "worker_forks")
    slot_peaks = max_metric_for_phase(samples, "blocking_slots")

    lines = [
        "Ansible fork demo report",
        "========================",
        "",
        f"Configured forks (ansible.cfg): {configured}",
        "",
        "Continuous monitor peaks by phase (worker_forks):",
    ]

    if worker_peaks:
        for phase, peak in sorted(worker_peaks.items()):
            slots = slot_peaks.get(phase, 0)
            lines.append(f"  - {phase}: max worker_forks={peak}, max blocking_slots={slots}")
    else:
        lines.append("  (no monitor samples captured)")

    lines.extend(["", "Inline snapshots (explicit task checkpoints):"])
    if snapshots:
        for row in snapshots:
            lines.append(
                "  - {label}: worker_forks={worker_forks} blocking_slots={blocking_slots} "
                "(phase={phase})".format(
                    label=row.get("label", "?"),
                    worker_forks=row.get("worker_forks", "?"),
                    blocking_slots=row.get("blocking_slots", "?"),
                    phase=row.get("phase", "?"),
                )
            )
    else:
        lines.append("  (no inline snapshots recorded)")

    lines.extend(
        [
            "",
            "How to read this:",
            "  * worker_forks counts ansible-playbook worker processes for this run.",
            "  * blocking_slots counts hosts currently inside a synchronous sleep wrapper.",
            "  * During sync_blocking, both should peak near configured forks.",
            "  * After async jobs are fired (async_running), worker_forks drops while remote work continues.",
            "",
        ]
    )

    report = "\n".join(lines)
    report_path.write_text(report)
    print(report)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
