# TEI cold-start experiment

This project tests a practical question raised in [Hugging Face TEI issue #819](https://github.com/huggingface/text-embeddings-inference/issues/819): can a CPU embedding server become useful within 14 seconds?

The answer from this experiment is **yes on the tested native AMD64 runner**. The main delay was TEI's startup warmup. Making that warmup small—or skipping it—reduced time to the first correct embedding by about 68–72%, without changing the returned embeddings or materially hurting steady-state performance.

## Result

All four configurations used the same model, host, settings, and correctness reference. Each arm started a fresh server 20 times.

| Configuration | First correct embedding, median | p90 | Correct trials | Steady p50 | Throughput |
|---|---:|---:|---:|---:|---:|
| Patched TEI 1.8 baseline | 7.99 s | 8.26 s | 20/20 | 33.92 ms | 29.76 req/s |
| Candidate, default warmup | 7.62 s | 7.95 s | 20/20 | 33.95 ms | 29.68 req/s |
| Same candidate, 64-token warmup | 2.41 s | 2.67 s | 20/20 | 33.72 ms | 29.75 req/s |
| Same candidate, no warmup | **2.10 s** | **2.41 s** | 20/20 | 33.79 ms | 29.97 req/s |

No-warmup was **72.37% faster** than the identical candidate binary using its default warmup. The 64-token option was **68.36% faster**. All 80 measured trials passed the full correctness suite.

This passes the project's 25% improvement threshold, so the decision is **GO for validation on the intended production Spot instance**. It does not justify building a replacement embedding server: the useful change is a focused TEI warmup option.

## What was measured

The primary metric is `launch_to_first_correct_ms`: time from launching TEI until the first embedding is returned and verified. A fast `/health` response alone does not count.

Every timed trial checked that the embedding:

- contained only finite numbers;
- had the expected 1,024 dimensions and norm;
- matched a pinned TEI reference by cosine similarity;
- remained correct for a suite of individual and batch-shaped inputs.

Only correct trials were included in the performance statistics. The harness also measured health time, first and second request latency, steady-state latency, and concurrent throughput.

## Why four configurations?

The patched TEI 1.8 arm represents the older baseline. The other three arms use the **same candidate binary**, changing only warmup size. Its default-warmup arm is the control: comparing it with 64 and zero tokens isolates warmup from unrelated version or build changes.

The tested candidate is [TEI PR #884](https://github.com/huggingface/text-embeddings-inference/pull/884) at commit `5806bdc99f11ad490cd7e38c1f4dd757034c0adb`.

## Evidence

- [Saved final AMD64 artifact](results/final-amd64/run-38189585542/README.md)
- [GitHub Actions run #38189585542](https://github.com/kraftaa/tei-cold-start-experiment/actions/runs/38189585542)
- [Decision record](docs/decision.md)

The artifact contains raw JSONL trials, summaries, environment metadata, the correctness reference, and logs. The workflow can be rerun from **Actions → AMD64 cold-start benchmark → Run workflow**; the default is 20 trials per arm.

For a quick harness check that does not download the model:

```bash
python3 -m unittest discover -s tests -v
python3 bench/run.py \
  --config repro/configs/fake-process.json \
  --trials 3 \
  --capture-reference
```

## Important limits

- The result came from one native `x86_64` GitHub-hosted Ubuntu runner (AMD EPYC 7763, 4 logical CPUs), not a fixed CPU Spot instance or the final production container. The next production step is to repeat the comparison there.
- The pinned ONNX model export is not batch-independent. The benchmark safely serialized inference with `--max-batch-requests 1`; the model should be re-exported and batching revalidated before production use.
- Model files were cached before timing, so network download time is excluded. Every trial still launched a new server process.
- These AMD64 results should not be mixed with earlier Apple Silicon diagnostic runs or x86 emulation measurements.

## Reproducibility pins

- Model: `Svenni551/Qwen3-Embedding-0.6B-ONNX-INT8`
- Model revision: `5a8767404281704b871d7c0c081ab90807e91738`
- TEI 1.8 commit: `2bff275313a7b93e9a5d4dc1dbfdce8e72c7d820`
- Candidate commit: `5806bdc99f11ad490cd7e38c1f4dd757034c0adb`
- Final experiment commit: `7131f3c7daf880f969bab1dc8f310c718f811385`

See the configuration files under [`repro/configs`](repro/configs) and the workflow at [`.github/workflows/amd64-cold-start.yml`](.github/workflows/amd64-cold-start.yml) for the exact commands and settings.
