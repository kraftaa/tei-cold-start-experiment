# TEI cold-start experiment

This repository measures the time from launching an embedding server to receiving the **first correct embedding**. It was motivated by [TEI issue #819](https://github.com/huggingface/text-embeddings-inference/issues/819), where a CPU Spot deployment needed to become useful within 14 seconds.

The experiment is intentionally benchmark-first. It does not assume that a new server will outperform Hugging Face Text Embeddings Inference (TEI), and it does not count an early `/health` response as success when the first inference remains slow.

## Current status

Phase 1 infrastructure is implemented:

- fresh-process or fresh-container trials;
- monotonic launch, health, first-request, second-request, and steady-state timings;
- finite-value, dimension, norm, and cosine-reference checks;
- run-isolated raw JSONL results and per-trial server logs;
- correctness-gated median, p90, range, failure, and throughput summaries;
- immutable TEI image and model revisions in the supplied configuration;
- sampled container memory and CPU observations.

No comparable performance result is claimed yet. The development host is Apple Silicon, while the official TEI 1.8 CPU image is `linux/amd64`. Measurements under emulation do not reproduce the reported CPU environment.

A manual GitHub Actions workflow is included for an exploratory native-AMD64 comparison. It compiles the baseline and candidate as native processes on one `ubuntu-24.04` runner, executes correctness-gated trials, and uploads raw results and server logs even when an arm fails. Native execution avoids an expired Intel OneAPI repository certificate in TEI 1.8's historical Dockerfile. GitHub-hosted runner hardware varies, so those numbers should be confirmed in containers on a fixed CPU Spot instance before making a performance claim.

Preliminary integration findings are nevertheless useful:

- the pinned TEI 1.8 image loaded the model under x86 emulation, entered its 1,024-token warmup, and did not reach `/health` within the ten-minute smoke-test limit;
- the pinned warmup-control PR built natively and produced a finite, normalized, 1,024-dimensional first embedding;
- after the correctness fixes, zero warmup passed 20/20 complete trials with a 1.714s median and 1.789s p90 on this ARM host; a 64-token warmup also passed 20/20, with a 1.928s median and 2.039s p90;
- neither number is comparable to the x86 baseline;
- direct ONNX Runtime testing proved that the model artifact is not batch-independent: a padded two-item inference has cosine similarities around 0.941 and 0.964 against independent inference, even for the unpadded row;
- TEI also replaced a stricter `--max-batch-requests 1` with the ORT backend maximum of 8. The recorded patch makes the backend limit a ceiling, allowing this model to run safely with serialized inference;
- reference capture now constructs every batch oracle from independent single-item requests, preventing a broken batch from defining its own correctness reference.

The correctness workaround costs batching throughput: the corrected zero-warmup arm measured a 23.08 requests/s median at four-request concurrency. The model should be re-exported correctly before this workaround is considered production-ready.

A native ARM TEI 1.8 build required three explicit compatibility changes: honoring the stricter batch cap, providing the model's required `position_ids`, and updating `metrics` from 0.23.0 to 0.23.1 for current compiler compatibility. It reached health in 5.303s, but its first embedding had only 0.9906 cosine similarity to the shared reference, likely due to its older ONNX Runtime. That result is rejected rather than treated as a comparable baseline.

## Pinned baseline

The issue reporter identified:

- TEI 1.8 CPU/ONNX;
- `Svenni551/Qwen3-Embedding-0.6B-ONNX-INT8`;
- mean pooling, as specified by that model repository;
- automatic truncation, required by TEI when the 32k model limit exceeds the configured batch-token limit;
- `--max-batch-tokens 1024`.

The baseline config pins:

- TEI tag commit `2bff275313a7b93e9a5d4dc1dbfdce8e72c7d820`;
- CPU image manifest `sha256:c466c97680cc9c2968108c4b1b44ca7729a091a44b61c840d9487f07d42e9099` (`linux/amd64`);
- model revision `5a8767404281704b871d7c0c081ab90807e91738`.

The model repository currently contains duplicate Qwen/GPT-style configuration aliases that TEI may reject. The benchmark fails visibly if that incompatibility is encountered; `repro/prepare_model.py` creates a pinned local copy with only the documented alias keys removed and records the transformation. Model weights are never committed.

## Quick harness check

This exercises the complete process lifecycle without downloading a model:

```bash
python3 -m unittest discover -s tests -v
python3 bench/run.py \
  --config repro/configs/fake-process.json \
  --trials 3 \
  --capture-reference
python3 bench/summarize.py <raw-results-path-printed-by-the-runner>
```

## Real TEI baseline

Requirements: Linux x86-64, Docker, enough RAM for the model, and Python 3.11+. Do not use Rosetta/QEMU results as the headline comparison.

For the hosted AMD64 experiment, open **Actions → AMD64 cold-start benchmark → Run workflow**. The default is 20 trials per arm. The four arms are patched TEI 1.8, the warmup PR with its default warmup, the same PR with a 64-token warmup, and the same PR with zero warmup. The same-binary default arm isolates the effect of the warmup setting from unrelated changes between TEI versions. The workflow uses a locally built native TEI 1.8 correctness baseline because the official image overrides `--max-batch-requests 1`; the exact queue-cap, `position_ids`, and build-lock patches are pinned in the baseline config. Download the workflow artifact for raw JSONL, environment metadata, summaries, and logs.

First prepare the warm local model cache. Network time is deliberately excluded from the main experiment:

```bash
python3 repro/prepare_model.py \
  --model-id Svenni551/Qwen3-Embedding-0.6B-ONNX-INT8 \
  --revision 5a8767404281704b871d7c0c081ab90807e91738 \
  --output .cache/models/qwen3-embedding-0.6b-onnx-int8
```

Pull the pinned image, then capture the reference from the baseline and run the required trials:

```bash
docker pull \
  ghcr.io/huggingface/text-embeddings-inference@sha256:c466c97680cc9c2968108c4b1b44ca7729a091a44b61c840d9487f07d42e9099

python3 bench/run.py \
  --config repro/configs/tei-v1.8.0-cpu-int8.json \
  --trials 1 \
  --capture-reference

python3 bench/run.py \
  --config repro/configs/tei-v1.8.0-cpu-int8.json \
  --trials 20

python3 bench/summarize.py <raw-results-path-printed-by-the-runner>
```

Capture the host metadata alongside the raw trials and extract coarse internal phases from a TEI log:

```bash
python3 repro/capture_environment.py --output results/environment.json
python3 bench/extract_phases.py results/logs/tei-v1.8.0-cpu-int8/trial-001.log
```

Build the exact warmup-control PR and compare both a minimal warmup and no explicit warmup:

```bash
./repro/build_warmup_pr.sh

python3 bench/run.py --config repro/configs/tei-warmup-pr-default.json --trials 20
python3 bench/run.py --config repro/configs/tei-warmup-pr-64.json --trials 20
python3 bench/run.py --config repro/configs/tei-warmup-pr-zero.json --trials 20

python3 bench/summarize.py <default-arm-raw-results-path>
python3 bench/summarize.py <64-token-arm-raw-results-path>
python3 bench/summarize.py <zero-token-arm-raw-results-path>
```

All PR configurations compare against the baseline reference. The default arm is the control for the 64- and zero-token arms because it uses the identical binary. The runner also records the locally built image ID in every raw trial so a mutable tag cannot silently change the tested binary. Because the pinned ONNX export is batch-incorrect, every candidate configuration uses `--max-batch-requests 1` with the recorded TEI cap-handling patch. The unmodified official baseline is expected to fail that batch check until an equivalent patched image is built.

On a non-x86 development host, a native build can validate the integration without producing a comparison result:

```bash
./repro/build_warmup_pr_native.sh
python3 bench/run.py \
  --config repro/configs/tei-warmup-pr-zero-native-smoke.json \
  --trials 1 \
  --capture-reference
```

This native smoke configuration is explicitly labeled non-comparable and must not be included in the headline benchmark.

`--capture-reference` is explicit and is accepted only by configurations that authorize reference creation. Every consumer also declares and verifies the expected reference experiment, so a candidate cannot silently redefine correctness. Commit the reference only if redistribution is appropriate; otherwise preserve it with the experiment artifacts.

Every invocation receives a unique run ID. Raw results and logs are stored under that ID, existing output files are never appended to, and the summarizer rejects files containing mixed run IDs.

## Metrics

The primary metric is `launch_to_first_correct_ms`. Other measurements include:

- `launch_command_ms`: time for the launcher itself to return;
- `launch_to_health_ms`: first successful health response;
- `first_request_ms` and `second_request_ms`;
- steady-state request p50/p95;
- modest-concurrency throughput in requests per second;
- approximate peak container RSS and maximum sampled CPU percentage;
- correctness-suite cosine similarity to the pinned reference.

Filesystem pages are allowed to remain cached in the main experiment, matching a warm local model cache. Every timed trial uses a new process/container, so application memory is not reused. Page-cache-cleared measurements must be run and labeled separately.

## Decision rule

Proceed to an optimization only when profiling identifies a specific avoidable cost. A useful win requires at least 25% lower median launch-to-first-correct-embedding, no material p90 regression, matching outputs, and no major steady-state regression. Only trials that pass the complete correctness suite contribute to primary performance statistics. Any reproducible correctness failure makes that candidate ineligible regardless of speed. Otherwise the result is NO-GO.

See [docs/decision.md](docs/decision.md) for the live decision record.
