# tei-v1.8.0-cpu-int8-correctness summary

Trials: 20 (20 successful, 0 failed)

Only trials passing the complete correctness suite contribute to the primary metrics.

| Metric (ms) | n | Median | p90 | Min | Max |
|---|---:|---:|---:|---:|---:|
| launch_command_ms | 20 | 0.48 | 0.51 | 0.46 | 0.53 |
| launch_to_health_ms | 20 | 7955.81 | 8218.63 | 7853.04 | 8368.16 |
| launch_to_first_correct_ms | 20 | 7992.83 | 8255.31 | 7889.79 | 8404.88 |
| first_request_ms | 20 | 36.24 | 38.42 | 34.81 | 42.28 |
| second_request_ms | 20 | 35.08 | 35.87 | 33.26 | 52.21 |

Steady-state request latency: p50=33.92 ms, p95=36.33 ms (400 requests)

Resource figures are approximate samples, not kernel-level maxima.

Throughput: median=29.76 requests/s, p90=30.55 requests/s (20 trials)
