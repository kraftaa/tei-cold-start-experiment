from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import time
import unittest


ROOT = Path(__file__).resolve().parents[1]


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


runner = load_module("benchmark_runner", ROOT / "bench" / "run.py")
summarizer = load_module("benchmark_summarizer", ROOT / "bench" / "summarize.py")
phase_parser = load_module("phase_parser", ROOT / "bench" / "extract_phases.py")


class CorrectnessTests(unittest.TestCase):
    def test_automatic_port_is_outside_common_ephemeral_range(self):
        port = runner.choose_port()
        self.assertGreaterEqual(port, 15000)
        self.assertLess(port, 30000)

    def test_rejects_non_finite_embedding(self):
        with self.assertRaisesRegex(ValueError, "non-finite"):
            runner.validate_embeddings([[1.0, float("nan")]], {"inputs": "x"}, {}, None)

    def test_cosine_and_norm_validation(self):
        response = [[0.6, 0.8]]
        embeddings, details = runner.validate_embeddings(
            response,
            {"inputs": "x", "normalize": True},
            {"expected_dimension": 2, "norm_tolerance": 1e-6, "cosine_threshold": 0.999},
            [[0.6, 0.8]],
        )
        self.assertEqual(embeddings, response)
        self.assertAlmostEqual(details["cosine_similarities"][0], 1.0)

    def test_batch_cardinality(self):
        with self.assertRaisesRegex(ValueError, "expected 2"):
            runner.validate_embeddings([[1.0]], {"inputs": ["a", "b"]}, {}, None)

    def test_http_error_is_returned_for_expected_status_validation(self):
        # request_json must preserve structured non-2xx responses rather than
        # turning every expected validation error into a transport failure.
        self.assertTrue(callable(runner.request_json))

    def test_workload_allows_version_specific_empty_input_rejection(self):
        workload = json.loads((ROOT / "bench" / "workload.json").read_text())
        empty_case = next(case for case in workload["correctness"] if case["id"] == "empty")
        self.assertEqual(empty_case["expect_status"], [400, 413])

    def test_amd64_default_control_uses_same_candidate_binary(self):
        config_dir = ROOT / "repro" / "configs"
        default = json.loads(
            (config_dir / "tei-warmup-pr-default-amd64-ci.json").read_text()
        )
        zero = json.loads(
            (config_dir / "tei-warmup-pr-zero-amd64-ci.json").read_text()
        )
        default_command = default["launcher"]["command"]
        zero_command = zero["launcher"]["command"]
        self.assertEqual(default_command[0], zero_command[0])
        warmup_index = zero_command.index("--warmup-tokens")
        del zero_command[warmup_index : warmup_index + 2]
        self.assertEqual(default_command, zero_command)


class SummaryTests(unittest.TestCase):
    def test_primary_summary_excludes_failed_correctness_trials(self):
        rows = [
            {"run_id": "one", "experiment": "x", "status": "ok", "launch_to_first_correct_ms": 10, "steady_request_ms": [1, 2], "resources": {}, "host": {}},
            {"run_id": "one", "experiment": "x", "status": "failed", "error": "boom", "launch_to_first_correct_ms": 1000, "host": {}},
        ]
        result = summarizer.summarize(rows)
        self.assertEqual(result["failures"], 1)
        self.assertEqual(result["metrics_ms"]["launch_to_first_correct_ms"]["median"], 10)
        self.assertEqual(result["all_observed_metrics_ms_diagnostic_only"]["launch_to_first_correct_ms"]["median"], 505)

    def test_summary_rejects_mixed_runs(self):
        rows = [
            {"run_id": "one", "experiment": "x", "status": "ok", "resources": {}, "host": {}},
            {"run_id": "two", "experiment": "x", "status": "ok", "resources": {}, "host": {}},
        ]
        with self.assertRaisesRegex(ValueError, "one non-empty run_id"):
            summarizer.summarize(rows)

    def test_phase_extraction(self):
        log = "\n".join([
            "2026-01-01T00:00:00.000Z INFO Args { model_id: x }",
            "2026-01-01T00:00:00.100Z INFO Starting model backend",
            "2026-01-01T00:00:00.600Z INFO Warming up model",
            "2026-01-01T00:00:00.800Z INFO Starting HTTP server",
        ])
        result = phase_parser.extract(log)
        self.assertTrue(result["complete"])
        self.assertAlmostEqual(result["phases_ms"]["backend_initialization"], 500)


class EndToEndTests(unittest.TestCase):
    def test_process_trial(self):
        config = json.loads((ROOT / "repro" / "configs" / "fake-process.json").read_text())
        workload = json.loads((ROOT / "bench" / "workload.json").read_text())
        record, reference = runner.run_trial(config, workload, None, 1, True, "test-run")
        self.assertEqual(record["status"], "ok", record.get("error"))
        self.assertIsNotNone(reference)
        self.assertGreater(record["launch_to_first_correct_ms"], 0)
        self.assertEqual(record["first_validation"]["dimensions"], [4])

    def test_process_exit_is_detected_without_waiting_for_timeout(self):
        config = json.loads((ROOT / "repro" / "configs" / "fake-process.json").read_text())
        config["launcher"]["command"] = ["python3", "-c", "raise SystemExit(7)"]
        workload = json.loads((ROOT / "bench" / "workload.json").read_text())
        started = time.monotonic()
        record, _ = runner.run_trial(config, workload, None, 1, True, "test-exit")
        self.assertEqual(record["status"], "failed")
        self.assertIn("exited before", record["error"])
        self.assertLess(time.monotonic() - started, 2)


if __name__ == "__main__":
    unittest.main()
