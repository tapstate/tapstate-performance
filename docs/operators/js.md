# Js performance

## `ubuntu-24.04-x64-op`

Baseline [`sync-2026-11-25-v1`](https://github.com/tapstate/tapstate-performance/blob/f33a9f5a80625fa85baba7880b2d12bbb8a95b1f/baselines/ubuntu-24.04-x64-op/sync-2026-11-25-v1/baseline.json).

Comparison rules `1`.

### `js.backlog.basic.standard@1`

backlog-throughput · formal · 10,000 configured rows · 30,000 backlog events · Intel(R) Xeon(R) 6975P-C · ubuntu24 20261116.133.1 · JDK 21.0.13+9-LTS.

Measured 2026-11-25 in run 45544961925, attempt 1, at `e861698ed7dd419b9c16c7fd3012bf7c72e03765`.

| Arm / metric | Median or evidence gap | Range and repeats | Change from first | Evidence |
|---|---|---|---|---|
| `single` / `completion_ms` | insufficient-source-end-evidence | | | |
| `single` / `op.rss_peak_bytes` | No qualified OP phase RSS sampling | | | |

### `js.live.basic.standard@1`

`not-run` · Maven Central returned HTTP 429 during dependency resolution before measurement.

Measured 2026-11-25 in run 45544961925, attempt 1, at `e861698ed7dd419b9c16c7fd3012bf7c72e03765`.

[Evidence 1](https://github.com/tapstate/tapstate-performance/blob/f33a9f5a80625fa85baba7880b2d12bbb8a95b1f/baselines/ubuntu-24.04-x64-op/sync-2026-11-25-v1/evidence/js.live.basic.standard/status.json)

### `js.snapshot.basic.large@1`

`not-run` · Maven Central returned HTTP 429 during dependency resolution before measurement.

Measured 2026-11-25 in run 45544961925, attempt 1, at `e861698ed7dd419b9c16c7fd3012bf7c72e03765`.

[Evidence 1](https://github.com/tapstate/tapstate-performance/blob/f33a9f5a80625fa85baba7880b2d12bbb8a95b1f/baselines/ubuntu-24.04-x64-op/sync-2026-11-25-v1/evidence/js.snapshot.basic.large/status.json)

### `js.snapshot.basic.small@1`

snapshot · formal · 100,000 configured rows · Intel(R) Xeon(R) 6975P-C · ubuntu24 20261116.133.1 · JDK 21.0.13+9-LTS.

Measured 2026-11-25 in run 45544961925, attempt 1, at `e861698ed7dd419b9c16c7fd3012bf7c72e03765`.

| Arm / metric | Median or evidence gap | Range and repeats | Change from first | Evidence |
|---|---|---|---|---|
| `single` / `completion_ms` | monotonic observed upper bound including telemetry publication and polling | | | |
| `single` / `op.rss_peak_bytes` | No qualified OP phase RSS sampling | | | |

### `js.snapshot.basic.standard@1`

snapshot · formal · 100,000 configured rows · Intel(R) Xeon(R) 6975P-C · ubuntu24 20261116.133.1 · JDK 21.0.13+9-LTS.

Measured 2026-11-25 in run 45544961925, attempt 1, at `e861698ed7dd419b9c16c7fd3012bf7c72e03765`.

| Arm / metric | Median or evidence gap | Range and repeats | Change from first | Evidence |
|---|---|---|---|---|
| `single` / `completion_ms` | monotonic observed upper bound including telemetry publication and polling | | | |
| `single` / `op.rss_peak_bytes` | No qualified OP phase RSS sampling | | | |

### `js.snapshot.basic.wide@1`

snapshot · formal · 25,000 configured rows · Intel(R) Xeon(R) 6975P-C · ubuntu24 20261116.133.1 · JDK 21.0.13+9-LTS.

Measured 2026-11-25 in run 45544961925, attempt 1, at `e861698ed7dd419b9c16c7fd3012bf7c72e03765`.

| Arm / metric | Median or evidence gap | Range and repeats | Change from first | Evidence |
|---|---|---|---|---|
| `single` / `completion_ms` | monotonic observed upper bound including telemetry publication and polling | | | |
| `single` / `op.rss_peak_bytes` | No qualified OP phase RSS sampling | | | |

### `mixed.snapshot.double-map.standard@1`

snapshot · formal · 100,000 configured rows · Intel(R) Xeon(R) 6975P-C · ubuntu24 20261116.133.1 · JDK 21.0.13+9-LTS.

Measured 2026-11-25 in run 45544961925, attempt 1, at `e861698ed7dd419b9c16c7fd3012bf7c72e03765`.

| Arm / metric | Median or evidence gap | Range and repeats | Change from first | Evidence |
|---|---|---|---|---|
| `single` / `completion_ms` | monotonic observed upper bound including telemetry publication and polling | | | |
| `single` / `op.rss_peak_bytes` | No qualified OP phase RSS sampling | | | |
