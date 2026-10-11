# tei-warmup-pr-zero-native-smoke summary

Trials: 20 (20 successful, 0 failed)

Only trials passing the complete correctness suite contribute to the primary metrics.

| Metric (ms) | n | Median | p90 | Min | Max |
|---|---:|---:|---:|---:|---:|
| launch_command_ms | 20 | 2.63 | 3.09 | 2.37 | 3.44 |
| launch_to_health_ms | 20 | 1662.18 | 1730.45 | 1453.05 | 2006.69 |
| launch_to_first_correct_ms | 20 | 1714.31 | 1788.93 | 1495.80 | 2092.03 |
| first_request_ms | 20 | 48.45 | 67.07 | 33.51 | 87.91 |
| second_request_ms | 20 | 44.70 | 61.86 | 32.70 | 65.44 |

Steady-state request latency: p50=41.88 ms, p95=63.03 ms (100 requests)

Resource figures are approximate samples, not kernel-level maxima.

Throughput: median=23.08 requests/s, p90=25.75 requests/s (20 trials)
