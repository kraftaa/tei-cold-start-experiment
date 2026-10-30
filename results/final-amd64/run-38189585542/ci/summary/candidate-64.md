# tei-warmup-pr-64-amd64-ci summary

Trials: 20 (20 successful, 0 failed)

Only trials passing the complete correctness suite contribute to the primary metrics.

| Metric (ms) | n | Median | p90 | Min | Max |
|---|---:|---:|---:|---:|---:|
| launch_command_ms | 20 | 0.50 | 0.56 | 0.46 | 0.73 |
| launch_to_health_ms | 20 | 2373.42 | 2630.09 | 2269.29 | 2632.31 |
| launch_to_first_correct_ms | 20 | 2409.57 | 2667.13 | 2305.09 | 2669.15 |
| first_request_ms | 20 | 36.11 | 37.16 | 35.08 | 38.53 |
| second_request_ms | 20 | 34.88 | 37.38 | 32.97 | 40.87 |

Steady-state request latency: p50=33.72 ms, p95=36.54 ms (400 requests)

Resource figures are approximate samples, not kernel-level maxima.

Throughput: median=29.75 requests/s, p90=30.56 requests/s (20 trials)
