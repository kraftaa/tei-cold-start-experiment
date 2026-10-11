# tei-warmup-pr-zero-native-smoke summary

Trials: 20 (4 successful, 16 failed)

Only trials passing the complete correctness suite contribute to the primary metrics.

| Metric (ms) | n | Median | p90 | Min | Max |
|---|---:|---:|---:|---:|---:|
| launch_command_ms | 4 | 3.00 | 3.24 | 2.79 | 3.33 |
| launch_to_health_ms | 4 | 1886.22 | 2442.56 | 1709.07 | 2663.27 |
| launch_to_first_correct_ms | 4 | 1938.27 | 2508.36 | 1787.56 | 2731.01 |
| first_request_ms | 4 | 64.26 | 75.04 | 40.86 | 78.28 |
| second_request_ms | 4 | 48.91 | 61.23 | 37.57 | 65.45 |

Steady-state request latency: p50=43.18 ms, p95=75.15 ms (20 requests)

Resource figures are approximate samples, not kernel-level maxima.

Throughput: median=28.79 requests/s, p90=30.17 requests/s (4 trials)

## Failures

- cosine similarity below 0.9999: [0.9414490686584128, 0.9650385014218809]
- cosine similarity below 0.9999: [0.9414490686584128, 0.9650385014218809]
- cosine similarity below 0.9999: [0.9414490686584128, 0.9650385014218809]
- cosine similarity below 0.9999: [0.9414490686584128, 0.9650385014218809]
- cosine similarity below 0.9999: [0.9414490686584128, 0.9650385014218809]
- cosine similarity below 0.9999: [0.9414490686584128, 0.9650385014218809]
- server exited before the health endpoint became ready
- cosine similarity below 0.9999: [0.9414490686584128, 0.9650385014218809]
- cosine similarity below 0.9999: [0.9414490686584128, 0.9650385014218809]
- cosine similarity below 0.9999: [0.9414490686584128, 0.9650385014218809]
- cosine similarity below 0.9999: [0.9414490686584128, 0.9650385014218809]
- cosine similarity below 0.9999: [0.9414490686584128, 0.9650385014218809]
- cosine similarity below 0.9999: [0.9414490686584128, 0.9650385014218809]
- cosine similarity below 0.9999: [0.9414490686584128, 0.9650385014218809]
- cosine similarity below 0.9999: [0.9414490686584128, 0.9650385014218809]
- cosine similarity below 0.9999: [0.9414490686584128, 0.9650385014218809]
