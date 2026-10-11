#!/usr/bin/env python3
"""Summarize raw JSONL cold-start trials."""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
import statistics
from typing import Any


ROOT = Path(__file__).resolve().parents[1]


def percentile(values: list[float], probability: float) -> float:
    ordered = sorted(values)
    if not ordered:
        raise ValueError("no values")
    position = (len(ordered) - 1) * probability
    lower = math.floor(position)
    upper = math.ceil(position)
    if lower == upper:
        return ordered[lower]
    return ordered[lower] + (ordered[upper] - ordered[lower]) * (position - lower)


def describe(values: list[float]) -> dict[str, float] | None:
    if not values:
        return None
    return {
        "count": len(values),
        "median": statistics.median(values),
        "p90": percentile(values, 0.90),
        "min": min(values),
        "max": max(values),
    }


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows = []
    with path.open(encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, 1):
            if line.strip():
                try:
                    rows.append(json.loads(line))
                except json.JSONDecodeError as error:
                    raise ValueError(f"{path}:{line_number}: {error}") from error
    return rows


def summarize(rows: list[dict[str, Any]]) -> dict[str, Any]:
    if not rows:
        raise ValueError("input contains no trials")
    experiments = {row.get("experiment") for row in rows}
    run_ids = {row.get("run_id") for row in rows}
    if len(experiments) != 1:
        raise ValueError(f"input mixes experiments: {sorted(str(value) for value in experiments)}")
    if len(run_ids) != 1 or None in run_ids:
        raise ValueError("input must contain exactly one non-empty run_id")
    successful = [row for row in rows if row.get("status") == "ok"]
    metric_names = [
        "launch_command_ms",
        "launch_to_health_ms",
        "launch_to_first_correct_ms",
        "first_request_ms",
        "second_request_ms",
    ]
    metrics = {
        metric: describe([float(row[metric]) for row in successful if row.get(metric) is not None])
        for metric in metric_names
    }
    observed_metrics = {
        metric: describe([float(row[metric]) for row in rows if row.get(metric) is not None])
        for metric in metric_names
    }
    steady = [float(value) for row in successful for value in row.get("steady_request_ms", [])]
    memory = [float(row["resources"]["approx_peak_memory_bytes"]) for row in successful if row.get("resources", {}).get("approx_peak_memory_bytes") is not None]
    cpu = [float(row["resources"]["max_sampled_cpu_percent"]) for row in successful if row.get("resources", {}).get("max_sampled_cpu_percent") is not None]
    throughput = [float(row["throughput"]["requests_per_second"]) for row in successful if row.get("throughput", {}).get("requests_per_second") is not None]
    return {
        "schema_version": 1,
        "experiment": rows[0].get("experiment"),
        "run_id": rows[0].get("run_id"),
        "trials": len(rows),
        "successes": len(successful),
        "failures": len(rows) - len(successful),
        "failure_messages": [row.get("error") for row in rows if row.get("status") != "ok"],
        "metrics_ms": metrics,
        "all_observed_metrics_ms_diagnostic_only": observed_metrics,
        "steady_request_ms": {
            "count": len(steady),
            "p50": percentile(steady, 0.50) if steady else None,
            "p95": percentile(steady, 0.95) if steady else None,
        },
        "resources": {
            "approx_peak_memory_bytes": describe(memory),
            "max_sampled_cpu_percent": describe(cpu),
        },
        "throughput_requests_per_second": describe(throughput),
        "host_fingerprints": sorted({json.dumps(row.get("host", {}), sort_keys=True) for row in rows}),
    }


def markdown(summary: dict[str, Any]) -> str:
    lines = [
        f"# {summary['experiment']} summary",
        "",
        f"Trials: {summary['trials']} ({summary['successes']} successful, {summary['failures']} failed)",
        "",
        "Only trials passing the complete correctness suite contribute to the primary metrics.",
        "",
        "| Metric (ms) | n | Median | p90 | Min | Max |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for name, values in summary["metrics_ms"].items():
        if values:
            lines.append(f"| {name} | {values['count']} | {values['median']:.2f} | {values['p90']:.2f} | {values['min']:.2f} | {values['max']:.2f} |")
    steady = summary["steady_request_ms"]
    lines.extend([
        "",
        f"Steady-state request latency: p50={steady['p50']:.2f} ms, p95={steady['p95']:.2f} ms ({steady['count']} requests)" if steady["p50"] is not None else "Steady-state request latency: unavailable",
        "",
        "Resource figures are approximate samples, not kernel-level maxima.",
        "",
    ])
    throughput = summary["throughput_requests_per_second"]
    if throughput:
        lines.extend([
            f"Throughput: median={throughput['median']:.2f} requests/s, p90={throughput['p90']:.2f} requests/s ({throughput['count']} trials)",
            "",
        ])
    if summary["failure_messages"]:
        lines.extend(["## Failures", ""] + [f"- {message}" for message in summary["failure_messages"]] + [""])
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path)
    parser.add_argument("--json-output", type=Path)
    parser.add_argument("--markdown-output", type=Path)
    args = parser.parse_args()
    rows = read_jsonl(args.input)
    summary = summarize(rows)
    stem = summary["experiment"]
    json_output = args.json_output or ROOT / "results" / "summary" / f"{stem}.json"
    markdown_output = args.markdown_output or ROOT / "results" / "summary" / f"{stem}.md"
    json_output.parent.mkdir(parents=True, exist_ok=True)
    markdown_output.parent.mkdir(parents=True, exist_ok=True)
    json_output.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    markdown_output.write_text(markdown(summary), encoding="utf-8")
    print(markdown(summary))
    print(f"JSON: {json_output}\nMarkdown: {markdown_output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
