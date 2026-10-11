# tei-warmup-pr-zero-native-smoke summary

Trials: 20 (13 successful, 7 failed)

| Metric (ms) | Median | p90 | Min | Max |
|---|---:|---:|---:|---:|
| launch_command_ms | 2.52 | 2.69 | 2.19 | 3.15 |
| launch_to_health_ms | 1479.11 | 1540.68 | 1406.88 | 1622.03 |
| launch_to_first_correct_ms | 1506.03 | 1623.71 | 1425.72 | 1670.02 |
| first_request_ms | 24.50 | 48.43 | 18.65 | 91.38 |
| second_request_ms | 23.90 | 42.92 | 16.68 | 71.76 |

Steady-state request latency: p50=24.88 ms, p95=38.06 ms (100 requests)

Resource figures are approximate samples, not kernel-level maxima.

## Failures

- cosine similarity below 0.9999: [0.9414490686584128, 0.9650385014218809]
- cosine similarity below 0.9999: [0.9414490686584128, 0.9650385014218809]
- cosine similarity below 0.9999: [0.9414490686584128, 0.9650385014218809]
- cosine similarity below 0.9999: [0.9414490686584128, 0.9650385014218809]
- cosine similarity below 0.9999: [0.9414490686584128, 0.9650385014218809]
- cosine similarity below 0.9999: [0.9414490686584128, 0.9650385014218809]
- cosine similarity below 0.9999: [0.9414490686584128, 0.9650385014218809]
