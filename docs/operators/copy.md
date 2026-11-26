# Copy performance

## `ubuntu-24.04-x64-op`

Baseline [`sync-2026-11-25-v1`](https://github.com/tapstate/tapstate-performance/blob/f33a9f5a80625fa85baba7880b2d12bbb8a95b1f/baselines/ubuntu-24.04-x64-op/sync-2026-11-25-v1/baseline.json).

Comparison rules `1`.

### `copy.backlog.fixed-iud.standard@1`

backlog-throughput · formal · 10,000 configured rows · 30,000 backlog events · INTEL(R) XEON(R) PLATINUM 8573C · ubuntu24 20261116.376.1 · JDK 21.0.13+9-LTS.

Measured 2026-11-25 in run 45544961925, attempt 1, at `e861698ed7dd419b9c16c7fd3012bf7c72e03765`.

| Arm / metric | Median or evidence gap | Range and repeats | Change from first | Evidence |
|---|---|---|---|---|
| `single` / `completion_ms` | insufficient-source-end-evidence | | | |
| `single` / `op.rss_peak_bytes` | No qualified OP phase RSS sampling | | | |

### `copy.live.basic.standard@1`

`failed` · io.tapstate.e2e.BenchmarkRunIT$Unverified: Live source window was incomplete

Measured 2026-11-25 in run 45544961925, attempt 1, at `e861698ed7dd419b9c16c7fd3012bf7c72e03765`.

[Evidence 1](https://github.com/tapstate/tapstate-performance/blob/f33a9f5a80625fa85baba7880b2d12bbb8a95b1f/baselines/ubuntu-24.04-x64-op/sync-2026-11-25-v1/evidence/copy.live.basic.standard/status.json)

### `copy.live.handoff.standard@1`

`not-run` · Maven Central returned HTTP 429 during dependency resolution before measurement.

Measured 2026-11-25 in run 45544961925, attempt 1, at `e861698ed7dd419b9c16c7fd3012bf7c72e03765`.

[Evidence 1](https://github.com/tapstate/tapstate-performance/blob/f33a9f5a80625fa85baba7880b2d12bbb8a95b1f/baselines/ubuntu-24.04-x64-op/sync-2026-11-25-v1/evidence/copy.live.handoff.standard/status.json)

### `copy.live.slow-target.large@2`

`failed` · io.tapstate.e2e.BenchmarkRunIT$Unverified: unlimited at live Live source window was incomplete
limited at live Live source window was incomplete

Measured 2026-11-25 in run 45544961925, attempt 1, at `e861698ed7dd419b9c16c7fd3012bf7c72e03765`.

[Evidence 1](https://github.com/tapstate/tapstate-performance/blob/f33a9f5a80625fa85baba7880b2d12bbb8a95b1f/baselines/ubuntu-24.04-x64-op/sync-2026-11-25-v1/evidence/copy.live.slow-target.large/status.json)

### `copy.snapshot.basic.large@2`

snapshot · formal · 10,000 configured rows · Intel(R) Xeon(R) 6975P-C · ubuntu24 20261116.133.1 · JDK 21.0.13+9-LTS.

Measured 2026-11-25 in run 45544961925, attempt 1, at `e861698ed7dd419b9c16c7fd3012bf7c72e03765`.

| Arm / metric | Median or evidence gap | Range and repeats | Change from first | Evidence |
|---|---|---|---|---|
| `single` / `completion_ms` | monotonic observed upper bound including telemetry publication and polling | | | |
| `single` / `idle.rss_peak_bytes`<br>OP process, idle, procfs process status, records 10,000 | 1156513792 B | 1150136320 to 1159843840 B · 3 repeats | Same reference | [Repeat 1](https://github.com/tapstate/tapstate-performance/blob/f33a9f5a80625fa85baba7880b2d12bbb8a95b1f/baselines/ubuntu-24.04-x64-op/sync-2026-11-25-v1/evidence/copy.snapshot.basic.large/1.json), [Repeat 2](https://github.com/tapstate/tapstate-performance/blob/f33a9f5a80625fa85baba7880b2d12bbb8a95b1f/baselines/ubuntu-24.04-x64-op/sync-2026-11-25-v1/evidence/copy.snapshot.basic.large/2.json), [Repeat 3](https://github.com/tapstate/tapstate-performance/blob/f33a9f5a80625fa85baba7880b2d12bbb8a95b1f/baselines/ubuntu-24.04-x64-op/sync-2026-11-25-v1/evidence/copy.snapshot.basic.large/3.json) |
| `single` / `readback.rss_peak_bytes`<br>OP process, readback, procfs process status, records 10,000 | 1152782336 B | 1149575168 to 1155989504 B · 2 repeats | Same reference | [Repeat 1](https://github.com/tapstate/tapstate-performance/blob/f33a9f5a80625fa85baba7880b2d12bbb8a95b1f/baselines/ubuntu-24.04-x64-op/sync-2026-11-25-v1/evidence/copy.snapshot.basic.large/2.json), [Repeat 2](https://github.com/tapstate/tapstate-performance/blob/f33a9f5a80625fa85baba7880b2d12bbb8a95b1f/baselines/ubuntu-24.04-x64-op/sync-2026-11-25-v1/evidence/copy.snapshot.basic.large/3.json) |
| `single` / `snapshot.rss_peak_bytes`<br>OP process, snapshot, procfs process status, records 10,000 | 1155399680 B | 1148788736 to 1160032256 B · 3 repeats | Same reference | [Repeat 1](https://github.com/tapstate/tapstate-performance/blob/f33a9f5a80625fa85baba7880b2d12bbb8a95b1f/baselines/ubuntu-24.04-x64-op/sync-2026-11-25-v1/evidence/copy.snapshot.basic.large/1.json), [Repeat 2](https://github.com/tapstate/tapstate-performance/blob/f33a9f5a80625fa85baba7880b2d12bbb8a95b1f/baselines/ubuntu-24.04-x64-op/sync-2026-11-25-v1/evidence/copy.snapshot.basic.large/2.json), [Repeat 3](https://github.com/tapstate/tapstate-performance/blob/f33a9f5a80625fa85baba7880b2d12bbb8a95b1f/baselines/ubuntu-24.04-x64-op/sync-2026-11-25-v1/evidence/copy.snapshot.basic.large/3.json) |
| `single` / `startup.rss_peak_bytes`<br>OP process, startup, procfs process status, records 10,000 | 490008576 B | 479334400 to 567910400 B · 3 repeats | Same reference | [Repeat 1](https://github.com/tapstate/tapstate-performance/blob/f33a9f5a80625fa85baba7880b2d12bbb8a95b1f/baselines/ubuntu-24.04-x64-op/sync-2026-11-25-v1/evidence/copy.snapshot.basic.large/1.json), [Repeat 2](https://github.com/tapstate/tapstate-performance/blob/f33a9f5a80625fa85baba7880b2d12bbb8a95b1f/baselines/ubuntu-24.04-x64-op/sync-2026-11-25-v1/evidence/copy.snapshot.basic.large/2.json), [Repeat 3](https://github.com/tapstate/tapstate-performance/blob/f33a9f5a80625fa85baba7880b2d12bbb8a95b1f/baselines/ubuntu-24.04-x64-op/sync-2026-11-25-v1/evidence/copy.snapshot.basic.large/3.json) |

### `copy.snapshot.basic.small@1`

snapshot · formal · 100,000 configured rows · Intel(R) Xeon(R) 6975P-C · ubuntu24 20261116.133.1 · JDK 21.0.13+9-LTS.

Measured 2026-11-25 in run 45544961925, attempt 1, at `e861698ed7dd419b9c16c7fd3012bf7c72e03765`.

| Arm / metric | Median or evidence gap | Range and repeats | Change from first | Evidence |
|---|---|---|---|---|
| `single` / `completion_ms` | monotonic observed upper bound including telemetry publication and polling | | | |
| `single` / `op.rss_peak_bytes` | No qualified OP phase RSS sampling | | | |

### `copy.snapshot.basic.standard@1`

snapshot · formal · 10,000 configured rows · Intel(R) Xeon(R) 6975P-C · ubuntu24 20261116.133.1 · JDK 21.0.13+9-LTS.

Measured 2026-11-25 in run 45544961925, attempt 1, at `e861698ed7dd419b9c16c7fd3012bf7c72e03765`.

| Arm / metric | Median or evidence gap | Range and repeats | Change from first | Evidence |
|---|---|---|---|---|
| `single` / `completion_ms` | monotonic observed upper bound including telemetry publication and polling | | | |
| `single` / `op.rss_peak_bytes` | No qualified OP phase RSS sampling | | | |

### `copy.snapshot.basic.wide@2`

snapshot · formal · 25,000 configured rows · Intel(R) Xeon(R) 6975P-C · ubuntu24 20261116.133.1 · JDK 21.0.13+9-LTS.

Measured 2026-11-25 in run 45544961925, attempt 1, at `e861698ed7dd419b9c16c7fd3012bf7c72e03765`.

| Arm / metric | Median or evidence gap | Range and repeats | Change from first | Evidence |
|---|---|---|---|---|
| `single` / `completion_ms` | monotonic observed upper bound including telemetry publication and polling | | | |
| `single` / `idle.rss_peak_bytes`<br>OP process, idle, procfs process status, records 25,000 | 1146580992 B | 1125183488 to 1161089024 B · 3 repeats | Same reference | [Repeat 1](https://github.com/tapstate/tapstate-performance/blob/f33a9f5a80625fa85baba7880b2d12bbb8a95b1f/baselines/ubuntu-24.04-x64-op/sync-2026-11-25-v1/evidence/copy.snapshot.basic.wide/1.json), [Repeat 2](https://github.com/tapstate/tapstate-performance/blob/f33a9f5a80625fa85baba7880b2d12bbb8a95b1f/baselines/ubuntu-24.04-x64-op/sync-2026-11-25-v1/evidence/copy.snapshot.basic.wide/2.json), [Repeat 3](https://github.com/tapstate/tapstate-performance/blob/f33a9f5a80625fa85baba7880b2d12bbb8a95b1f/baselines/ubuntu-24.04-x64-op/sync-2026-11-25-v1/evidence/copy.snapshot.basic.wide/3.json) |
| `single` / `readback.rss_peak_bytes`<br>OP process, readback, procfs process status, records 25,000 | 1150013440 B | 1133760512 to 1160581120 B · 3 repeats | Same reference | [Repeat 1](https://github.com/tapstate/tapstate-performance/blob/f33a9f5a80625fa85baba7880b2d12bbb8a95b1f/baselines/ubuntu-24.04-x64-op/sync-2026-11-25-v1/evidence/copy.snapshot.basic.wide/1.json), [Repeat 2](https://github.com/tapstate/tapstate-performance/blob/f33a9f5a80625fa85baba7880b2d12bbb8a95b1f/baselines/ubuntu-24.04-x64-op/sync-2026-11-25-v1/evidence/copy.snapshot.basic.wide/2.json), [Repeat 3](https://github.com/tapstate/tapstate-performance/blob/f33a9f5a80625fa85baba7880b2d12bbb8a95b1f/baselines/ubuntu-24.04-x64-op/sync-2026-11-25-v1/evidence/copy.snapshot.basic.wide/3.json) |
| `single` / `snapshot.rss_peak_bytes`<br>OP process, snapshot, procfs process status, records 25,000 | 1148751872 B | 1133006848 to 1160105984 B · 3 repeats | Same reference | [Repeat 1](https://github.com/tapstate/tapstate-performance/blob/f33a9f5a80625fa85baba7880b2d12bbb8a95b1f/baselines/ubuntu-24.04-x64-op/sync-2026-11-25-v1/evidence/copy.snapshot.basic.wide/1.json), [Repeat 2](https://github.com/tapstate/tapstate-performance/blob/f33a9f5a80625fa85baba7880b2d12bbb8a95b1f/baselines/ubuntu-24.04-x64-op/sync-2026-11-25-v1/evidence/copy.snapshot.basic.wide/2.json), [Repeat 3](https://github.com/tapstate/tapstate-performance/blob/f33a9f5a80625fa85baba7880b2d12bbb8a95b1f/baselines/ubuntu-24.04-x64-op/sync-2026-11-25-v1/evidence/copy.snapshot.basic.wide/3.json) |
| `single` / `startup.rss_peak_bytes`<br>OP process, startup, procfs process status, records 25,000 | 483323904 B | 462233600 to 502554624 B · 3 repeats | Same reference | [Repeat 1](https://github.com/tapstate/tapstate-performance/blob/f33a9f5a80625fa85baba7880b2d12bbb8a95b1f/baselines/ubuntu-24.04-x64-op/sync-2026-11-25-v1/evidence/copy.snapshot.basic.wide/1.json), [Repeat 2](https://github.com/tapstate/tapstate-performance/blob/f33a9f5a80625fa85baba7880b2d12bbb8a95b1f/baselines/ubuntu-24.04-x64-op/sync-2026-11-25-v1/evidence/copy.snapshot.basic.wide/2.json), [Repeat 3](https://github.com/tapstate/tapstate-performance/blob/f33a9f5a80625fa85baba7880b2d12bbb8a95b1f/baselines/ubuntu-24.04-x64-op/sync-2026-11-25-v1/evidence/copy.snapshot.basic.wide/3.json) |

### `copy.snapshot.dummy-baseline.standard@1`

snapshot · formal · 100,000 configured rows · INTEL(R) XEON(R) PLATINUM 8573C · ubuntu24 20261116.376.1 · JDK 21.0.13+9-LTS.

Measured 2026-11-25 in run 45544961925, attempt 1, at `e861698ed7dd419b9c16c7fd3012bf7c72e03765`.

| Arm / metric | Median or evidence gap | Range and repeats | Change from first | Evidence |
|---|---|---|---|---|
| `single` / `completion_ms` | monotonic observed upper bound including telemetry publication and polling | | | |
| `single` / `op.rss_peak_bytes` | No qualified OP phase RSS sampling | | | |
