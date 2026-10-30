# tei-warmup-pr-zero-amd64-ci summary

Trials: 20 (20 successful, 0 failed)

Only trials passing the complete correctness suite contribute to the primary metrics.

| Metric (ms) | n | Median | p90 | Min | Max |
|---|---:|---:|---:|---:|---:|
| launch_command_ms | 20 | 0.50 | 0.53 | 0.46 | 0.63 |
| launch_to_health_ms | 20 | 2068.79 | 2376.47 | 1966.89 | 2477.25 |
| launch_to_first_correct_ms | 20 | 2104.37 | 2413.90 | 2002.58 | 2515.42 |
| first_request_ms | 20 | 35.81 | 37.20 | 35.03 | 37.87 |
| second_request_ms | 20 | 34.49 | 36.85 | 32.60 | 44.77 |

Steady-state request latency: p50=33.79 ms, p95=36.50 ms (400 requests)

Resource figures are approximate samples, not kernel-level maxima.

Throughput: median=29.97 requests/s, p90=30.89 requests/s (20 trials)
