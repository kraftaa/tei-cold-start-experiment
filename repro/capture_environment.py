#!/usr/bin/env python3
"""Capture non-secret host and Docker metadata for a benchmark run."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import platform
import subprocess
import time


def command(*args: str) -> str | None:
    completed = subprocess.run(args, capture_output=True, text=True)
    return completed.stdout.strip() if completed.returncode == 0 else None


def linux_cpu_model() -> str | None:
    path = Path("/proc/cpuinfo")
    if not path.exists():
        return None
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.startswith("model name") and ":" in line:
            return line.split(":", 1)[1].strip()
    return None


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    data = {
        "captured_at_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "platform": platform.platform(),
        "machine": platform.machine(),
        "processor": platform.processor(),
        "logical_cpu_count": os.cpu_count(),
        "kernel": {
            "system": platform.system(),
            "release": platform.release(),
            "version": platform.version(),
        },
        "cpu_model_linux": linux_cpu_model(),
        "cpu_model_macos": command("sysctl", "-n", "machdep.cpu.brand_string"),
        "memory_bytes_macos": command("sysctl", "-n", "hw.memsize"),
        "docker_info": None,
        "thread_environment": {
            key: os.environ.get(key)
            for key in ("OMP_NUM_THREADS", "MKL_NUM_THREADS", "RAYON_NUM_THREADS")
        },
    }
    docker = command(
        "docker", "info", "--format",
        '{"server_version":"{{.ServerVersion}}","architecture":"{{.Architecture}}","cpus":{{.NCPU}},"memory_bytes":{{.MemTotal}},"operating_system":"{{.OperatingSystem}}"}',
    )
    if docker:
        data["docker_info"] = json.loads(docker)
    rendered = json.dumps(data, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered, encoding="utf-8")
    else:
        print(rendered, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
