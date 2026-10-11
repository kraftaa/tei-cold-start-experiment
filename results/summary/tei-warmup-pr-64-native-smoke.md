# tei-warmup-pr-64-native-smoke summary

Trials: 20 (14 successful, 6 failed)

| Metric (ms) | Median | p90 | Min | Max |
|---|---:|---:|---:|---:|
| launch_command_ms | 2.40 | 2.88 | 2.20 | 3.12 |
| launch_to_health_ms | 1670.34 | 1745.61 | 1563.28 | 2231.97 |
| launch_to_first_correct_ms | 1712.18 | 1787.05 | 1602.97 | 2263.01 |
| first_request_ms | 31.43 | 44.72 | 20.22 | 54.16 |
| second_request_ms | 25.04 | 34.97 | 17.81 | 40.93 |

Steady-state request latency: p50=24.77 ms, p95=35.41 ms (100 requests)

Resource figures are approximate samples, not kernel-level maxima.

## Failures

- cosine similarity below 0.9999: [0.9414490686584128, 0.9650385014218809]
- cosine similarity below 0.9999: [0.9414490686584128, 0.9650385014218809]
- cosine similarity below 0.9999: [0.9414490686584128, 0.9650385014218809]
- cosine similarity below 0.9999: [0.9414490686584128, 0.9650385014218809]
- cosine similarity below 0.9999: [0.9414490686584128, 0.9650385014218809]
- cosine similarity below 0.9999: [0.9414490686584128, 0.9650385014218809]
