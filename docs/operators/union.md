# Union performance

## `ubuntu-24.04-x64-op`

Baseline [`sync-2026-11-25-v1`](https://github.com/tapstate/tapstate-performance/blob/f33a9f5a80625fa85baba7880b2d12bbb8a95b1f/baselines/ubuntu-24.04-x64-op/sync-2026-11-25-v1/baseline.json).

Comparison rules `1`.

### `union.backlog.basic.standard@1`

backlog-throughput · formal · 10,000 configured rows · 30,000 backlog events · Intel(R) Xeon(R) 6975P-C · ubuntu24 20261116.133.1 · JDK 21.0.13+9-LTS.

Measured 2026-11-25 in run 45544961925, attempt 1, at `e861698ed7dd419b9c16c7fd3012bf7c72e03765`.

| Arm / metric | Median or evidence gap | Range and repeats | Change from first | Evidence |
|---|---|---|---|---|
| `single` / `completion_ms` | insufficient-source-end-evidence | | | |
| `single` / `op.rss_peak_bytes` | No qualified OP phase RSS sampling | | | |

### `union.live.basic.standard@1`

`failed` · io.tapstate.e2e.BenchmarkRunIT$Unverified: The operator live source window was incomplete

Measured 2026-11-25 in run 45544961925, attempt 1, at `e861698ed7dd419b9c16c7fd3012bf7c72e03765`.

[Evidence 1](https://github.com/tapstate/tapstate-performance/blob/f33a9f5a80625fa85baba7880b2d12bbb8a95b1f/baselines/ubuntu-24.04-x64-op/sync-2026-11-25-v1/evidence/union.live.basic.standard/status.json)

### `union.snapshot.basic.large@1`

snapshot · formal · 10,000 configured rows · Intel(R) Xeon(R) 6975P-C · ubuntu24 20261116.133.1 · JDK 21.0.13+9-LTS.

Measured 2026-11-25 in run 45544961925, attempt 1, at `e861698ed7dd419b9c16c7fd3012bf7c72e03765`.

| Arm / metric | Median or evidence gap | Range and repeats | Change from first | Evidence |
|---|---|---|---|---|
| `single` / `completion_ms` | monotonic observed upper bound including telemetry publication and polling | | | |
| `single` / `op.rss_peak_bytes` | No qualified OP phase RSS sampling | | | |

### `union.snapshot.basic.small@1`

snapshot · formal · 100,000 configured rows · Intel(R) Xeon(R) 6975P-C · ubuntu24 20261116.133.1 · JDK 21.0.13+9-LTS.

Measured 2026-11-25 in run 45544961925, attempt 1, at `e861698ed7dd419b9c16c7fd3012bf7c72e03765`.

| Arm / metric | Median or evidence gap | Range and repeats | Change from first | Evidence |
|---|---|---|---|---|
| `single` / `completion_ms` | monotonic observed upper bound including telemetry publication and polling | | | |
| `single` / `op.rss_peak_bytes` | No qualified OP phase RSS sampling | | | |

### `union.snapshot.basic.standard@1`

snapshot · formal · 100,000 configured rows · Intel(R) Xeon(R) 6975P-C · ubuntu24 20261116.133.1 · JDK 21.0.13+9-LTS.

Measured 2026-11-25 in run 45544961925, attempt 1, at `e861698ed7dd419b9c16c7fd3012bf7c72e03765`.

| Arm / metric | Median or evidence gap | Range and repeats | Change from first | Evidence |
|---|---|---|---|---|
| `single` / `completion_ms` | monotonic observed upper bound including telemetry publication and polling | | | |
| `single` / `op.rss_peak_bytes` | No qualified OP phase RSS sampling | | | |

### `union.snapshot.basic.wide@1`

snapshot · formal · 25,000 configured rows · Intel(R) Xeon(R) 6975P-C · ubuntu24 20261116.133.1 · JDK 21.0.13+9-LTS.

Measured 2026-11-25 in run 45544961925, attempt 1, at `e861698ed7dd419b9c16c7fd3012bf7c72e03765`.

| Arm / metric | Median or evidence gap | Range and repeats | Change from first | Evidence |
|---|---|---|---|---|
| `single` / `completion_ms` | monotonic observed upper bound including telemetry publication and polling | | | |
| `single` / `op.rss_peak_bytes` | No qualified OP phase RSS sampling | | | |
