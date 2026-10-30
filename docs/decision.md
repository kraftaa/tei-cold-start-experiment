# Decision record

## Current decision: GO for production validation; do not build a replacement server

The native AMD64 experiment found a reproducible, correctness-preserving improvement that exceeds the project's threshold. Startup warmup is the avoidable cost: using the candidate TEI binary with no warmup reduced median launch-to-first-correct-embedding from 7.616 seconds to 2.104 seconds.

This is a **GO to repeat the change in the intended Spot-instance and container environment**. It is not yet a production-wide claim, and it is not a reason to create another embedding server. The focused TEI change already addresses the bottleneck.

## Final AMD64 comparison

GitHub Actions [run #38189585542](https://github.com/kraftaa/tei-cold-start-experiment/actions/runs/38189585542) ran on native `x86_64` Linux with an AMD EPYC 7763 and four logical CPUs. Each arm used 20 fresh processes and the same cached model revision, host, correctness reference, and request suite.

| Arm | Median first correct | p90 | Passed | Steady p50 | Median throughput |
|---|---:|---:|---:|---:|---:|
| Patched TEI 1.8 baseline | 7.993 s | 8.255 s | 20/20 | 33.925 ms | 29.763 req/s |
| Candidate, default warmup | 7.616 s | 7.951 s | 20/20 | 33.954 ms | 29.682 req/s |
| Candidate, 64-token warmup | 2.410 s | 2.667 s | 20/20 | 33.716 ms | 29.753 req/s |
| Candidate, zero warmup | **2.104 s** | **2.414 s** | 20/20 | 33.787 ms | 29.973 req/s |

The same-binary comparisons are the clean evidence:

- 64 tokens versus default: **68.36% lower median startup**;
- zero tokens versus default: **72.37% lower median startup**;
- all 80 trials passed correctness;
- p90 improved rather than regressed;
- steady latency and throughput were effectively unchanged.

The zero-warmup result also met the motivating 14-second target with substantial margin on this runner.

## Decision rule assessment

The predeclared GO rule required at least 25% lower median time to first correct embedding, no material p90 regression, matching outputs, and no major steady-state regression.

| Requirement | Outcome |
|---|---|
| Median improvement at least 25% | Pass: 72.37% for zero warmup |
| No material p90 regression | Pass: 7.951 s to 2.414 s |
| Correct outputs | Pass: 20/20 for every arm |
| No major steady-state regression | Pass: latency and throughput were essentially flat |

## Why the conclusion is about warmup

The candidate's default, 64-token, and zero-token configurations used the exact same binary. Only the startup warmup setting changed. The default arm therefore controls for changes in TEI version, compiler, and build. Its startup remained close to the patched TEI 1.8 baseline, while reducing or removing warmup produced the large improvement.

Skipping warmup did not merely move several seconds into the first request: the primary measurement ended only after that first response was returned and verified.

## Correctness and model limitation

Direct ONNX Runtime testing found that the pinned model export is not batch-independent. A padded two-item inference differed from independent single-item inference, and TEI could replace a requested one-item batch limit with the backend maximum of eight.

The benchmark therefore used a recorded TEI patch that treats the backend maximum as a ceiling and honored `--max-batch-requests 1`. It also built batch correctness references from independent requests. This makes the cold-start comparison valid, but serialized batching is a workaround—not the desired production configuration.

Before production use, re-export or fix the ONNX model, restore batching, and repeat both correctness and throughput tests.

## Remaining validation

The final run is strong exploratory evidence, but GitHub-hosted hardware varies and the workflow used native processes rather than the intended production container. The remaining external step is:

1. use the exact target AMD64 Spot instance type and production container;
2. warm the model cache before timing, as in this experiment;
3. run at least 20 fresh-process trials for default and the chosen reduced warmup;
4. keep the same first-correct-embedding gate and steady-state measurements;
5. report instance type, CPU, image digest, model revision, median, p90, and failures.

If that run preserves the result, use the smallest warmup that meets the deployment's operational preference. Zero tokens was fastest here; 64 tokens was only about 0.31 seconds slower and may be a conservative choice.

## Upstream status

As checked on 2026-10-30, [TEI PR #884](https://github.com/huggingface/text-embeddings-inference/pull/884) and [issue #819](https://github.com/huggingface/text-embeddings-inference/issues/819) were open. The candidate was pinned to commit `5806bdc99f11ad490cd7e38c1f4dd757034c0adb` so future upstream changes cannot silently alter this result.

The complete saved evidence and provenance are under [`results/final-amd64/run-38189585542`](../results/final-amd64/run-38189585542/README.md).
