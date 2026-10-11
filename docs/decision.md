# Decision record

## Current decision: correctness fixed locally; no performance GO yet

Do not build a replacement server yet.

The motivating issue now has a proposed TEI change, [PR #884](https://github.com/huggingface/text-embeddings-inference/pull/884), that makes startup warmup configurable. Its published timing uses launch-to-`/health`; it does not yet establish launch-to-first-correct-embedding across repeated trials or whether skipped initialization moves into the first user request.

The first comparison should therefore be:

1. pinned TEI 1.8.0 with `--max-batch-tokens 1024`;
2. PR #884 with warmup unset, providing a same-binary control;
3. that identical PR binary with 64-token and zero-token warmup.

Only a profile showing a remaining avoidable bottleneck justifies implementation work.

## Preliminary findings on the development host

These are diagnostic results from Apple Silicon, not the required comparable x86 benchmark:

- The official TEI 1.8 CPU image is AMD64-only. Under emulation, model-backend creation completed and TEI entered its 1,024-token explicit warmup, but `/health` was still unavailable at the ten-minute timeout.
- PR #884 at commit `5806bdc99f11ad490cd7e38c1f4dd757034c0adb` built natively with the ORT/HTTP feature set.
- With `--warmup-tokens 0`, launch-to-first-correct single embedding was 1.506s median and 1.624s p90 across 20 native smoke trials.
- With `--warmup-tokens 64`, the corresponding measurements were 1.712s median and 1.787s p90.
- These timings demonstrate that the experiment is runnable and that warmup control reaches useful readiness; they do not establish a speedup over TEI on the reported hardware.

### Correctness finding

Direct ONNX Runtime inference isolated the problem to the pinned model export: its padded two-item output has cosine similarities of approximately 0.941 and 0.964 against independent single-item inference. TEI compounded this by replacing `--max-batch-requests 1` with the ORT backend maximum of 8.

The local TEI patch now treats the backend maximum as a ceiling and honors stricter user limits. Reference capture also constructs batch references from independent single-item inference. With serialized inference enabled:

- zero-token warmup: 20/20 passed, useful-ready median 1.714s and p90 1.789s;
- 64-token warmup: 20/20 passed, useful-ready median 1.928s and p90 2.039s;
- zero-token improvement over 64 tokens: approximately 11%, below the 25% GO threshold;
- zero-token four-request-concurrency throughput: median 23.08 requests/s.

These are valid native ARM candidate measurements, but not a baseline comparison. A compatibility-patched TEI 1.8 ARM build reached health in 5.303s but its first embedding had only 0.9906 cosine similarity to the shared reference, so it was rejected. The pinned official image remains AMD64-only.

## Known constraints

- The original issue gives a 14-second requirement, not a 14-second measured baseline.
- The reporter later described approximately two-minute startup.
- The referenced model config is not directly accepted by current TEI without removing three duplicate alias fields.
- The local development machine is ARM64. The pinned official TEI 1.8 CPU image is AMD64-only, so local emulated timings are unsuitable for the primary result.
- ARM is a valid separate deployment target, but requires a native, output-equivalent baseline. The current TEI 1.8 backport is not output-equivalent enough to qualify.

## GO / NO-GO rule

GO only if a change improves median launch-to-first-correct-embedding by at least 25%, does not materially regress p90, preserves the pinned correctness checks, and has no major steady-state regression. Primary timing statistics exclude any trial that fails the complete correctness suite. Otherwise publish NO-GO with the measurements.
