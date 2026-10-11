#!/usr/bin/env python3
"""Extract coarse internal startup phases from a TEI text log."""

from __future__ import annotations

import argparse
from datetime import datetime
import json
from pathlib import Path
import re


ANSI = re.compile(r"\x1b\[[0-9;]*m")
TIMESTAMP = re.compile(r"^(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?Z)")
MARKERS = {
    "log_start": "Args {",
    "backend_start": "Starting model backend",
    "warmup_start": "Warming up model",
    "http_start": "Starting HTTP server",
}


def parse_timestamp(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def extract(text: str) -> dict[str, object]:
    events: dict[str, datetime] = {}
    for raw_line in text.splitlines():
        line = ANSI.sub("", raw_line)
        match = TIMESTAMP.match(line)
        if not match:
            continue
        for event, marker in MARKERS.items():
            if event not in events and marker in line:
                events[event] = parse_timestamp(match.group(1))
    first = events.get("log_start")

    def elapsed(start: str, end: str) -> float | None:
        if start not in events or end not in events:
            return None
        return (events[end] - events[start]).total_seconds() * 1000

    return {
        "events_utc": {key: value.isoformat().replace("+00:00", "Z") for key, value in events.items()},
        "phases_ms": {
            "logged_preamble_to_backend": elapsed("log_start", "backend_start"),
            "backend_initialization": elapsed("backend_start", "warmup_start"),
            "explicit_warmup_to_http_start": elapsed("warmup_start", "http_start"),
            "logged_start_to_http_start": elapsed("log_start", "http_start"),
        },
        "complete": all(name in events for name in MARKERS),
        "note": "Log spans are internal coarse phases; external launch-to-health remains authoritative.",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("log", type=Path)
    args = parser.parse_args()
    print(json.dumps(extract(args.log.read_text(encoding="utf-8")), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
