# tei-warmup-pr-default-amd64-ci summary

Trials: 20 (20 successful, 0 failed)

Only trials passing the complete correctness suite contribute to the primary metrics.

| Metric (ms) | n | Median | p90 | Min | Max |
|---|---:|---:|---:|---:|---:|
| launch_command_ms | 20 | 0.50 | 0.55 | 0.46 | 0.90 |
| launch_to_health_ms | 20 | 7578.96 | 7914.15 | 7299.15 | 8761.63 |
| launch_to_first_correct_ms | 20 | 7615.79 | 7950.63 | 7335.39 | 8798.16 |
| first_request_ms | 20 | 36.50 | 38.79 | 35.64 | 43.14 |
| second_request_ms | 20 | 34.58 | 36.42 | 33.37 | 38.84 |

Steady-state request latency: p50=33.95 ms, p95=37.11 ms (400 requests)

Resource figures are approximate samples, not kernel-level maxima.

Throughput: median=29.68 requests/s, p90=30.53 requests/s (20 trials)
