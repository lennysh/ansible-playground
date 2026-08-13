#!/usr/bin/env python3
"""Count active ansible-playbook worker forks for the current playbook run."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path


def read_cmdline(pid: int) -> str:
    try:
        raw = Path(f"/proc/{pid}/cmdline").read_bytes()
    except OSError:
        return ""
    return raw.replace(b"\0", b" ").decode("utf-8", errors="replace").strip()


def read_ppid(pid: int) -> int | None:
    try:
        for line in Path(f"/proc/{pid}/status").read_text().splitlines():
            if line.startswith("PPid:"):
                return int(line.split()[1])
    except OSError:
        return None
    return None


def list_pids() -> list[int]:
    pids: list[int] = []
    for entry in os.listdir("/proc"):
        if entry.isdigit():
            pids.append(int(entry))
    return pids


def playbook_marker() -> str:
    return os.environ.get("DEMO_PLAYBOOK_MARKER", "playbook.yml")


def is_ansible_playbook_process(cmdline: str) -> bool:
    if not cmdline:
        return False
    if "count_forks.py" in cmdline or "fork_monitor.py" in cmdline:
        return False
    # Match the real controller/worker python processes, not shell wrappers whose
    # command line merely mentions ansible-playbook in an eval string.
    return "ansible-playbook" in cmdline and (
        "/ansible-playbook" in cmdline or cmdline.startswith("/usr/bin/python")
    )


def matching_playbook_pids() -> list[int]:
    marker = playbook_marker()
    matches: list[int] = []
    for pid in list_pids():
        cmdline = read_cmdline(pid)
        if is_ansible_playbook_process(cmdline) and marker in cmdline:
            matches.append(pid)
    return sorted(set(matches))


def find_playbook_root(candidates: list[int]) -> int | None:
    if not candidates:
        return None

    candidate_set = set(candidates)

    # Prefer the candidate that is an ancestor of the others (the top-level controller).
    for pid in candidates:
        if all(is_ancestor(pid, other) or pid == other for other in candidates):
            return pid

    return min(candidates)


def is_ancestor(ancestor: int, descendant: int) -> bool:
    pid = descendant
    seen: set[int] = set()
    while pid > 1 and pid not in seen:
        if pid == ancestor:
            return True
        seen.add(pid)
        parent = read_ppid(pid)
        if parent is None:
            break
        pid = parent
    return False


def list_children(parent_pid: int) -> list[int]:
    children: list[int] = []
    for pid in list_pids():
        if read_ppid(pid) == parent_pid:
            children.append(pid)
    return sorted(children)


def count_blocking_slots() -> int:
    slot_dir = Path(os.environ.get("DEMO_SLOT_DIR", "active-blocking-slots"))
    if not slot_dir.is_dir():
        return 0
    return sum(1 for path in slot_dir.iterdir() if path.is_file())


def snapshot() -> dict:
    configured = int(os.environ.get("DEMO_CONFIGURED_FORKS", "3"))
    matches = matching_playbook_pids()
    root = find_playbook_root(matches)
    worker_total = max(len(matches) - 1, 0) if matches else 0

    result: dict = {
        "playbook_root_pid": root,
        "configured_forks": configured,
        "worker_forks": worker_total,
        "playbook_processes": matches,
        "direct_children": len(list_children(root)) if root else 0,
        "blocking_slots": count_blocking_slots(),
        "children": [],
    }

    if root is not None:
        for child_pid in list_children(root):
            result["children"].append(
                {
                    "pid": child_pid,
                    "cmdline": read_cmdline(child_pid)[:160],
                }
            )
        result["playbook_cmdline"] = read_cmdline(root)[:200]
    else:
        result["error"] = "Could not locate ansible-playbook root process"

    phase_file = Path(os.environ.get("DEMO_PHASE_FILE", "fork-demo-phase.txt"))
    if phase_file.is_file():
        result["phase"] = phase_file.read_text().strip()

    return result


def main() -> int:
    if len(sys.argv) > 1 and sys.argv[1] == "--json":
        print(json.dumps(snapshot(), indent=2, sort_keys=True))
        return 0

    data = snapshot()
    phase = data.get("phase", "unknown")
    print(
        f"phase={phase} configured_forks={data['configured_forks']} "
        f"worker_forks={data['worker_forks']} blocking_slots={data['blocking_slots']}"
    )
    if "error" in data:
        print(data["error"], file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
