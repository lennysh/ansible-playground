#!/usr/bin/env python3
"""Background sampler for ansible-playbook worker fork counts."""

from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from count_forks import snapshot  # noqa: E402


def main() -> int:
    output = Path(os.environ.get("DEMO_SAMPLES_FILE", "fork-samples.json"))
    stop_file = Path(os.environ.get("DEMO_MONITOR_STOP_FILE", "fork-monitor-stop"))
    interval = float(os.environ.get("DEMO_SAMPLE_INTERVAL", "0.5"))
    max_duration = float(os.environ.get("DEMO_SAMPLE_DURATION", "300"))
    deadline = time.time() + max_duration
    samples: list[dict] = []

    while time.time() < deadline and not stop_file.is_file():
        sample = snapshot()
        sample["timestamp"] = time.time()
        samples.append(sample)
        output.write_text(json.dumps(samples, indent=2, sort_keys=True))
        time.sleep(interval)

    output.write_text(json.dumps(samples, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
