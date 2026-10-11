#!/usr/bin/env python3
"""Measure launch-to-first-correct-embedding for an HTTP embedding server."""

from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
import json
import math
import os
from pathlib import Path
import platform
import re
import secrets
import signal
import socket
import subprocess
import threading
import time
from typing import Any
import urllib.error
import urllib.request
import uuid


ROOT = Path(__file__).resolve().parents[1]


def public_command(command: list[str]) -> list[str]:
    """Keep raw results reproducible without publishing a local home path."""
    root = str(ROOT)
    return [part.replace(root, "$REPO") for part in command]


def load_json(path: Path) -> Any:
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def atomic_write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    temporary.replace(path)


def append_jsonl(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(value, sort_keys=True, separators=(",", ":")) + "\n")
        handle.flush()
        os.fsync(handle.fileno())


def monotonic_ms(start_ns: int) -> float:
    return (time.monotonic_ns() - start_ns) / 1_000_000


def choose_port(preferred: int | None = None) -> int:
    if preferred is not None:
        candidates = [preferred]
    else:
        # Binding port 0 commonly returns a port from the OS ephemeral-client
        # range. TEI can spend seconds loading before it binds, during which
        # health probes may reuse that same number as a client source port.
        # Select from the non-ephemeral user range instead.
        candidates = [15000 + secrets.randbelow(15000) for _ in range(100)]
    for candidate in candidates:
        try:
            with socket.socket() as sock:
                sock.bind(("127.0.0.1", candidate))
                return candidate
        except OSError:
            continue
    raise RuntimeError("could not find an available non-ephemeral server port")


def request_json(method: str, url: str, payload: Any | None, timeout: float) -> tuple[int, Any, dict[str, str]]:
    body = None if payload is None else json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(url, data=body, method=method)
    request.add_header("Content-Type", "application/json")
    try:
        response = urllib.request.urlopen(request, timeout=timeout)
    except urllib.error.HTTPError as error:
        with error:
            raw = error.read()
            value = json.loads(raw) if raw else None
            return error.code, value, {key.lower(): val for key, val in error.headers.items()}
    with response:
        raw = response.read()
        value = json.loads(raw) if raw else None
        return response.status, value, {key.lower(): val for key, val in response.headers.items()}


def wait_for_health(
    url: str,
    deadline: float,
    interval: float,
    start_ns: int,
    is_running,
) -> tuple[float, int]:
    attempts = 0
    last_running_check = 0.0
    while time.monotonic() < deadline:
        attempts += 1
        try:
            status, _, _ = request_json("GET", url, None, min(1.0, max(0.1, deadline - time.monotonic())))
            if 200 <= status < 300:
                return monotonic_ms(start_ns), attempts
        except (OSError, ValueError, urllib.error.URLError):
            pass
        now = time.monotonic()
        # `docker inspect` is comparatively expensive. Checking after a failed
        # request and at a bounded cadence detects exits without spawning a
        # Docker CLI process for every health poll.
        if now - last_running_check >= 0.25:
            if not is_running():
                raise RuntimeError("server exited before the health endpoint became ready")
            last_running_check = now
        time.sleep(interval)
    raise TimeoutError(f"health endpoint did not become ready: {url}")


def embeddings_from_response(response: Any) -> list[list[float]]:
    if not isinstance(response, list) or not response:
        raise ValueError("/embed response must be a non-empty JSON array")
    if all(isinstance(value, (int, float)) for value in response):
        response = [response]
    if not all(isinstance(row, list) and row for row in response):
        raise ValueError("/embed response must contain non-empty embedding arrays")
    result: list[list[float]] = []
    for row in response:
        converted = [float(value) for value in row]
        if not all(math.isfinite(value) for value in converted):
            raise ValueError("embedding contains a non-finite value")
        result.append(converted)
    return result


def cosine(left: list[float], right: list[float]) -> float:
    if len(left) != len(right):
        raise ValueError(f"embedding dimensions differ: {len(left)} != {len(right)}")
    left_norm = math.sqrt(sum(value * value for value in left))
    right_norm = math.sqrt(sum(value * value for value in right))
    if left_norm == 0 or right_norm == 0:
        raise ValueError("cannot compare a zero-norm embedding")
    return sum(a * b for a, b in zip(left, right)) / (left_norm * right_norm)


def validate_embeddings(
    response: Any,
    payload: dict[str, Any],
    rules: dict[str, Any],
    reference: list[list[float]] | None,
) -> tuple[list[list[float]], dict[str, Any]]:
    embeddings = embeddings_from_response(response)
    expected_count = len(payload["inputs"]) if isinstance(payload.get("inputs"), list) else 1
    if len(embeddings) != expected_count:
        raise ValueError(f"expected {expected_count} embeddings, received {len(embeddings)}")
    expected_dimension = rules.get("expected_dimension")
    dimensions = [len(row) for row in embeddings]
    if expected_dimension is not None and any(value != expected_dimension for value in dimensions):
        raise ValueError(f"expected dimension {expected_dimension}, received {dimensions}")
    norms = [math.sqrt(sum(value * value for value in row)) for row in embeddings]
    if payload.get("normalize") and rules.get("require_unit_norm", True):
        tolerance = float(rules.get("norm_tolerance", 1e-3))
        if any(abs(value - 1.0) > tolerance for value in norms):
            raise ValueError(f"normalized embedding norms outside tolerance {tolerance}: {norms}")
    similarities = None
    if reference is not None:
        if len(reference) != len(embeddings):
            raise ValueError("reference embedding count differs")
        similarities = [cosine(actual, expected) for actual, expected in zip(embeddings, reference)]
        threshold = float(rules.get("cosine_threshold", 0.9999))
        if any(value < threshold for value in similarities):
            raise ValueError(f"cosine similarity below {threshold}: {similarities}")
    return embeddings, {
        "count": len(embeddings),
        "dimensions": dimensions,
        "norms": norms,
        "cosine_similarities": similarities,
    }


def parse_bytes(value: str) -> int:
    match = re.fullmatch(r"\s*([0-9.]+)\s*([KMGT]?i?B)\s*", value)
    if not match:
        raise ValueError(value)
    amount = float(match.group(1))
    unit = match.group(2)
    factors = {"B": 1, "KB": 1000, "MB": 1000**2, "GB": 1000**3,
               "KiB": 1024, "MiB": 1024**2, "GiB": 1024**3, "TiB": 1024**4,
               "TB": 1000**4}
    return int(amount * factors[unit])


class ResourceSampler:
    def __init__(self, container_name: str, interval: float = 0.2):
        self.container_name = container_name
        self.interval = interval
        self.stop_event = threading.Event()
        self.samples: list[dict[str, Any]] = []
        self.thread = threading.Thread(target=self._sample, daemon=True)

    def start(self) -> None:
        self.thread.start()

    def stop(self) -> dict[str, Any]:
        self.stop_event.set()
        self.thread.join(timeout=2)
        memory = [sample["memory_bytes"] for sample in self.samples if sample.get("memory_bytes") is not None]
        cpu = [sample["cpu_percent"] for sample in self.samples if sample.get("cpu_percent") is not None]
        return {
            "sample_interval_ms": self.interval * 1000,
            "sample_count": len(self.samples),
            "approx_peak_memory_bytes": max(memory) if memory else None,
            "max_sampled_cpu_percent": max(cpu) if cpu else None,
        }

    def _sample(self) -> None:
        while not self.stop_event.is_set():
            completed = subprocess.run(
                ["docker", "stats", "--no-stream", "--format", "{{json .}}", self.container_name],
                capture_output=True,
                text=True,
            )
            if completed.returncode == 0 and completed.stdout.strip():
                try:
                    data = json.loads(completed.stdout.splitlines()[-1])
                    used = data.get("MemUsage", "").split("/")[0].strip()
                    cpu = data.get("CPUPerc", "").strip().removesuffix("%")
                    self.samples.append({
                        "memory_bytes": parse_bytes(used) if used else None,
                        "cpu_percent": float(cpu) if cpu else None,
                    })
                except (ValueError, json.JSONDecodeError):
                    pass
            self.stop_event.wait(self.interval)


class Launcher:
    def __init__(self, config: dict[str, Any], trial: int, port: int, log_path: Path):
        self.config = config
        self.trial = trial
        self.port = port
        self.log_path = log_path
        self.process: subprocess.Popen[str] | None = None
        self.container_name: str | None = None
        self.sampler: ResourceSampler | None = None
        self.image_metadata: dict[str, Any] | None = None

    def prepare(self) -> None:
        """Resolve static launch metadata before the benchmark clock starts."""
        launcher = self.config["launcher"]
        if launcher["type"] != "docker":
            return
        model_path = (ROOT / launcher["model_path"]).resolve()
        if not model_path.exists():
            raise FileNotFoundError(f"prepared model path does not exist: {model_path}")
        image_details = subprocess.run(
            ["docker", "image", "inspect", "--format", "{{json .}}", launcher["image"]],
            capture_output=True,
            text=True,
        )
        if image_details.returncode != 0:
            raise RuntimeError(f"docker image inspect failed: {image_details.stderr.strip()}")
        try:
            inspected_image = json.loads(image_details.stdout)
        except json.JSONDecodeError as error:
            raise RuntimeError("docker image inspect returned invalid JSON") from error
        self.image_metadata = {
            "id": inspected_image.get("Id"),
            "repo_digests": inspected_image.get("RepoDigests"),
            "architecture": inspected_image.get("Architecture"),
            "os": inspected_image.get("Os"),
        }

    def start(self) -> dict[str, Any]:
        launcher = self.config["launcher"]
        kind = launcher["type"]
        if kind == "process":
            command = [
                part.format(port=self.port, trial=self.trial, root=str(ROOT))
                for part in launcher["command"]
            ]
            environment = os.environ.copy()
            environment.update({key: str(value).format(port=self.port) for key, value in launcher.get("environment", {}).items()})
            self.log_path.parent.mkdir(parents=True, exist_ok=True)
            log_handle = self.log_path.open("w", encoding="utf-8")
            command_started_ns = time.monotonic_ns()
            self.process = subprocess.Popen(
                command,
                cwd=str((ROOT / launcher.get("cwd", ".")).resolve()),
                env=environment,
                stdout=log_handle,
                stderr=subprocess.STDOUT,
                text=True,
                start_new_session=True,
            )
            log_handle.close()
            command_ms = monotonic_ms(command_started_ns)
            return {"kind": kind, "command": public_command(command), "pid": self.process.pid,
                    "launch_command_ms": command_ms}
        if kind == "docker":
            self.container_name = f"tei-cold-start-{os.getpid()}-{self.trial}-{uuid.uuid4().hex[:8]}"
            model_path = (ROOT / launcher["model_path"]).resolve()
            command = [
                "docker", "run", "--detach", "--name", self.container_name,
                "--platform", launcher["platform"],
                "--publish", f"127.0.0.1:{self.port}:{launcher.get('container_port', 80)}",
                "--volume", f"{model_path}:/model:ro",
            ]
            for key, value in launcher.get("environment", {}).items():
                command.extend(["--env", f"{key}={value}"])
            command.append(launcher["image"])
            command.extend(["--model-id", "/model"])
            command.extend(str(value) for value in launcher.get("server_args", []))
            command_started_ns = time.monotonic_ns()
            completed = subprocess.run(command, capture_output=True, text=True)
            command_ms = monotonic_ms(command_started_ns)
            if completed.returncode != 0:
                raise RuntimeError(f"docker launch failed: {completed.stderr.strip()}")
            self.sampler = ResourceSampler(
                self.container_name,
                float(launcher.get("resource_sample_interval_ms", 1000)) / 1000,
            )
            self.sampler.start()
            return {
                "kind": kind,
                "command": public_command(command),
                "container_id": completed.stdout.strip(),
                "container_name": self.container_name,
                "image": self.image_metadata,
                "launch_command_ms": command_ms,
            }
        raise ValueError(f"unsupported launcher type: {kind}")

    def still_running(self) -> bool:
        if self.process is not None:
            return self.process.poll() is None
        if self.container_name:
            result = subprocess.run(
                ["docker", "inspect", "--format", "{{.State.Running}}", self.container_name],
                capture_output=True,
                text=True,
            )
            return result.returncode == 0 and result.stdout.strip() == "true"
        return False

    def stop(self) -> dict[str, Any]:
        resources = self.sampler.stop() if self.sampler else {}
        if self.container_name:
            inspected = subprocess.run(
                ["docker", "inspect", "--format", "{{json .State}}", self.container_name],
                capture_output=True,
                text=True,
            )
            if inspected.returncode == 0 and inspected.stdout.strip():
                try:
                    resources["container_state"] = json.loads(inspected.stdout)
                except json.JSONDecodeError:
                    resources["container_state_raw"] = inspected.stdout.strip()
            logs = subprocess.run(["docker", "logs", self.container_name], capture_output=True, text=True)
            self.log_path.parent.mkdir(parents=True, exist_ok=True)
            self.log_path.write_text(logs.stdout + logs.stderr, encoding="utf-8")
            subprocess.run(["docker", "stop", "--time", "10", self.container_name], capture_output=True, text=True)
            subprocess.run(["docker", "rm", "--force", self.container_name], capture_output=True, text=True)
        if self.process is not None and self.process.poll() is None:
            os.killpg(self.process.pid, signal.SIGTERM)
            try:
                self.process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                os.killpg(self.process.pid, signal.SIGKILL)
                self.process.wait(timeout=5)
        return resources


def timed_embed(base_url: str, request_config: dict[str, Any], payload: dict[str, Any], timeout: float) -> tuple[float, Any, dict[str, str]]:
    start = time.monotonic_ns()
    status, response, headers = request_json("POST", base_url + request_config["path"], payload, timeout)
    elapsed = monotonic_ms(start)
    if not 200 <= status < 300:
        raise RuntimeError(f"embed request returned HTTP {status}")
    return elapsed, response, headers


def run_trial(
    config: dict[str, Any],
    workload: dict[str, Any],
    reference: dict[str, Any] | None,
    trial: int,
    capture_reference: bool,
    run_id: str,
) -> tuple[dict[str, Any], dict[str, Any] | None]:
    timeout = float(config.get("timeout_seconds", 600))
    port = choose_port(config.get("host_port"))
    base_url = f"http://127.0.0.1:{port}"
    log_path = ROOT / "results" / "logs" / config["name"] / run_id / f"trial-{trial:03d}.log"
    launcher = Launcher(config, trial, port, log_path)
    launcher.prepare()
    started_ns = time.monotonic_ns()
    record: dict[str, Any] = {
        "schema_version": 1,
        "run_id": run_id,
        "experiment": config["name"],
        "trial": trial,
        "started_at_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "status": "failed",
        "host": {"system": platform.system(), "release": platform.release(), "machine": platform.machine(), "python": platform.python_version()},
        "pins": config.get("pins", {}),
        "log_path": str(log_path.relative_to(ROOT)),
    }
    captured: dict[str, Any] | None = None
    try:
        launch_metadata = launcher.start()
        record["launch_command_ms"] = launch_metadata.pop("launch_command_ms")
        record["launch"] = launch_metadata
        health_ms, health_attempts = wait_for_health(
            base_url + config["health_path"],
            time.monotonic() + timeout,
            float(config.get("health_poll_interval_ms", 50)) / 1000,
            started_ns,
            launcher.still_running,
        )
        record["launch_to_health_ms"] = health_ms
        record["health_attempts"] = health_attempts

        startup_payload = workload["startup"]
        first_ms, first_response, first_headers = timed_embed(base_url, config["request"], startup_payload, timeout)
        startup_reference = reference.get("startup") if reference else None
        first_embeddings, first_validation = validate_embeddings(
            first_response, startup_payload, config["correctness"], startup_reference
        )
        record["first_request_ms"] = first_ms
        record["launch_to_first_correct_ms"] = monotonic_ms(started_ns)
        record["first_validation"] = first_validation
        record["first_response_headers"] = first_headers

        second_ms, second_response, _ = timed_embed(base_url, config["request"], startup_payload, timeout)
        validate_embeddings(second_response, startup_payload, config["correctness"], startup_reference or first_embeddings)
        record["second_request_ms"] = second_ms

        steady_latencies = []
        for _ in range(int(config.get("steady_requests", 20))):
            elapsed, response, _ = timed_embed(base_url, config["request"], startup_payload, timeout)
            validate_embeddings(response, startup_payload, config["correctness"], startup_reference or first_embeddings)
            steady_latencies.append(elapsed)
        record["steady_request_ms"] = steady_latencies

        concurrency = int(config.get("throughput_concurrency", 0))
        throughput_requests = int(config.get("throughput_requests", 0))
        if concurrency > 0 and throughput_requests > 0:
            throughput_started_ns = time.monotonic_ns()
            throughput_latencies: list[float] = []
            with ThreadPoolExecutor(max_workers=concurrency) as pool:
                futures = [
                    pool.submit(timed_embed, base_url, config["request"], startup_payload, timeout)
                    for _ in range(throughput_requests)
                ]
                for future in as_completed(futures):
                    elapsed, response, _ = future.result()
                    validate_embeddings(
                        response, startup_payload, config["correctness"], startup_reference or first_embeddings
                    )
                    throughput_latencies.append(elapsed)
            throughput_elapsed_ms = monotonic_ms(throughput_started_ns)
            record["throughput"] = {
                "concurrency": concurrency,
                "requests": throughput_requests,
                "elapsed_ms": throughput_elapsed_ms,
                "requests_per_second": throughput_requests / (throughput_elapsed_ms / 1000),
                "request_ms": throughput_latencies,
            }

        correctness_results = {}
        captured = {
            "schema_version": 1,
            "experiment": config["name"],
            "pins": config.get("pins", {}),
            "startup": first_embeddings,
            "cases": {},
        }
        for case in workload.get("correctness", []):
            case_id = case["id"]
            expected_status = case.get("expect_status")
            payload = {key: value for key, value in case.items() if key not in {"id", "expect_status"}}
            if expected_status is not None:
                request_started = time.monotonic_ns()
                status, response, _ = request_json(
                    "POST", base_url + config["request"]["path"], payload, timeout
                )
                elapsed = monotonic_ms(request_started)
                if status != expected_status:
                    raise ValueError(
                        f"correctness case {case_id!r} expected HTTP {expected_status}, received {status}"
                    )
                correctness_results[case_id] = {
                    "request_ms": elapsed,
                    "expected_status": expected_status,
                    "actual_status": status,
                    "response": response,
                }
                continue
            case_reference = reference.get("cases", {}).get(case_id) if reference else None
            # Never establish batch correctness from a batch response. Broken
            # model exports can be internally consistent while mixing rows.
            # Build the oracle from independent single-item inference, then
            # require the batch response to match it before saving anything.
            if capture_reference and isinstance(payload.get("inputs"), list):
                case_reference = []
                for item in payload["inputs"]:
                    single_payload = {**payload, "inputs": item}
                    _, single_response, _ = timed_embed(
                        base_url, config["request"], single_payload, timeout
                    )
                    single_embeddings, _ = validate_embeddings(
                        single_response, single_payload, config["correctness"], None
                    )
                    case_reference.append(single_embeddings[0])
            elapsed, response, _ = timed_embed(base_url, config["request"], payload, timeout)
            embeddings, validation = validate_embeddings(response, payload, config["correctness"], case_reference)
            correctness_results[case_id] = {"request_ms": elapsed, **validation}
            captured["cases"][case_id] = case_reference or embeddings
        record["correctness_cases"] = correctness_results
        record["status"] = "ok"
        if not capture_reference:
            captured = None
    except Exception as error:  # preserve every failed trial as benchmark evidence
        record["error_type"] = type(error).__name__
        record["error"] = str(error)
        record["server_still_running_at_failure"] = launcher.still_running()
    finally:
        record["resources"] = launcher.stop()
        record["trial_total_ms"] = monotonic_ms(started_ns)
    return record, captured


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--trials", type=int, default=20)
    parser.add_argument("--capture-reference", action="store_true")
    parser.add_argument("--output", type=Path)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.trials < 1:
        raise SystemExit("--trials must be positive")
    config_path = args.config.resolve()
    config = load_json(config_path)
    workload = load_json((ROOT / config["workload"]).resolve())
    run_id = str(uuid.uuid4())
    run_kind = "reference" if args.capture_reference else "benchmark"
    default_name = ROOT / "results" / "raw" / config["name"] / f"{run_kind}-{run_id}.jsonl"
    output = args.output or default_name
    if output.exists():
        raise SystemExit(f"refusing to append to existing output: {output}")
    reference_path = (ROOT / config["correctness"]["reference_path"]).resolve()
    reference = load_json(reference_path) if reference_path.exists() and not args.capture_reference else None
    if not reference and not args.capture_reference:
        raise SystemExit(f"reference does not exist: {reference_path}; run once with --capture-reference")
    if args.capture_reference and args.trials != 1:
        raise SystemExit("reference capture requires --trials 1")
    if args.capture_reference and not config["correctness"].get("allow_reference_capture", False):
        raise SystemExit(f"reference capture is not authorized by config: {config_path}")
    if reference:
        expected_experiment = config["correctness"].get("reference_experiment")
        if not expected_experiment:
            raise SystemExit("config must declare correctness.reference_experiment")
        if reference.get("experiment") != expected_experiment:
            raise SystemExit(
                f"reference provenance mismatch: expected {expected_experiment!r}, "
                f"found {reference.get('experiment')!r}"
            )

    failures = 0
    for trial in range(1, args.trials + 1):
        record, captured = run_trial(config, workload, reference, trial, args.capture_reference, run_id)
        append_jsonl(output, record)
        if captured is not None and record["status"] == "ok":
            atomic_write_json(reference_path, captured)
            print(f"captured reference: {reference_path}")
        if record["status"] != "ok":
            failures += 1
        useful = record.get("launch_to_first_correct_ms")
        detail = f", useful-ready={useful:.1f} ms" if record["status"] == "ok" and useful else f", {record.get('error', '')}"
        print(f"trial {trial}/{args.trials}: {record['status']}{detail}")
    print(f"raw results: {output}")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
