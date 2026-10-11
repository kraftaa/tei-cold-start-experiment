# tei-warmup-pr-64-native-smoke summary

Trials: 20 (20 successful, 0 failed)

Only trials passing the complete correctness suite contribute to the primary metrics.

| Metric (ms) | n | Median | p90 | Min | Max |
|---|---:|---:|---:|---:|---:|
| launch_command_ms | 20 | 2.62 | 2.91 | 2.28 | 3.03 |
| launch_to_health_ms | 20 | 1884.01 | 1971.57 | 1781.19 | 2157.14 |
| launch_to_first_correct_ms | 20 | 1927.97 | 2039.16 | 1826.42 | 2204.78 |
| first_request_ms | 20 | 48.38 | 68.24 | 38.15 | 82.81 |
| second_request_ms | 20 | 53.70 | 76.34 | 40.31 | 96.95 |

Steady-state request latency: p50=42.86 ms, p95=67.62 ms (100 requests)

Resource figures are approximate samples, not kernel-level maxima.

Throughput: median=24.15 requests/s, p90=25.85 requests/s (20 trials)
