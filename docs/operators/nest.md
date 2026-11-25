# Nest performance

## `ubuntu-24.04-x64-op`

Baseline [`sync-2026-11-25-v1`](https://github.com/tapstate/tapstate-performance/blob/f33a9f5a80625fa85baba7880b2d12bbb8a95b1f/baselines/ubuntu-24.04-x64-op/sync-2026-11-25-v1/baseline.json).

Comparison rules `1`.

### `nest.backlog.basic.standard@1`

`not-run` · Maven Central returned HTTP 429 during dependency resolution before measurement.

Measured 2026-11-25 in run 45544961925, attempt 1, at `e861698ed7dd419b9c16c7fd3012bf7c72e03765`.

[Evidence 1](https://github.com/tapstate/tapstate-performance/blob/f33a9f5a80625fa85baba7880b2d12bbb8a95b1f/baselines/ubuntu-24.04-x64-op/sync-2026-11-25-v1/evidence/nest.backlog.basic.standard/status.json)

### `nest.live.basic.standard@1`

`failed` · io.tapstate.e2e.BenchmarkRunIT$Unverified: The operator live source window was incomplete

Measured 2026-11-25 in run 45544961925, attempt 1, at `e861698ed7dd419b9c16c7fd3012bf7c72e03765`.

[Evidence 1](https://github.com/tapstate/tapstate-performance/blob/f33a9f5a80625fa85baba7880b2d12bbb8a95b1f/baselines/ubuntu-24.04-x64-op/sync-2026-11-25-v1/evidence/nest.live.basic.standard/status.json)

### `nest.live.child-update.standard@1`

live-latency · formal · 25,000 configured rows · 25 events/s for 300 s · Intel(R) Xeon(R) 6975P-C · ubuntu24 20261116.133.1 · JDK 21.0.13+9-LTS.

Measured 2026-11-25 in run 45544961925, attempt 1, at `e861698ed7dd419b9c16c7fd3012bf7c72e03765`.

| Arm / metric | Median or evidence gap | Range and repeats | Change from first | Evidence |
|---|---|---|---|---|
| `hot` / `endpoint_p95_ms` | insufficient-event-correlation | | | |
| `hot` / `op.rss_peak_bytes` | No qualified OP phase RSS sampling | | | |
| `uniform` / `endpoint_p95_ms` | insufficient-event-correlation | | | |
| `uniform` / `op.rss_peak_bytes` | No qualified OP phase RSS sampling | | | |

### `nest.snapshot.basic.large@1`

snapshot · formal · 10,000 configured rows · INTEL(R) XEON(R) PLATINUM 8573C · ubuntu24 20261116.376.1 · JDK 21.0.13+9-LTS.

Measured 2026-11-25 in run 45544961925, attempt 1, at `e861698ed7dd419b9c16c7fd3012bf7c72e03765`.

| Arm / metric | Median or evidence gap | Range and repeats | Change from first | Evidence |
|---|---|---|---|---|
| `single` / `completion_ms` | monotonic observed upper bound including telemetry publication and polling | | | |
| `single` / `op.rss_peak_bytes` | No qualified OP phase RSS sampling | | | |

### `nest.snapshot.basic.small@1`

snapshot · formal · 100,000 configured rows · INTEL(R) XEON(R) PLATINUM 8573C · ubuntu24 20261116.376.1 · JDK 21.0.13+9-LTS.

Measured 2026-11-25 in run 45544961925, attempt 1, at `e861698ed7dd419b9c16c7fd3012bf7c72e03765`.

| Arm / metric | Median or evidence gap | Range and repeats | Change from first | Evidence |
|---|---|---|---|---|
| `single` / `completion_ms` | monotonic observed upper bound including telemetry publication and polling | | | |
| `single` / `op.rss_peak_bytes` | No qualified OP phase RSS sampling | | | |

### `nest.snapshot.basic.standard@1`

snapshot · formal · 100,000 configured rows · Intel(R) Xeon(R) 6975P-C · ubuntu24 20261116.133.1 · JDK 21.0.13+9-LTS.

Measured 2026-11-25 in run 45544961925, attempt 1, at `e861698ed7dd419b9c16c7fd3012bf7c72e03765`.

| Arm / metric | Median or evidence gap | Range and repeats | Change from first | Evidence |
|---|---|---|---|---|
| `single` / `completion_ms` | monotonic observed upper bound including telemetry publication and polling | | | |
| `single` / `op.rss_peak_bytes` | No qualified OP phase RSS sampling | | | |

### `nest.snapshot.basic.wide@1`

snapshot · formal · 25,000 configured rows · Intel(R) Xeon(R) 6975P-C · ubuntu24 20261116.133.1 · JDK 21.0.13+9-LTS.

Measured 2026-11-25 in run 45544961925, attempt 1, at `e861698ed7dd419b9c16c7fd3012bf7c72e03765`.

| Arm / metric | Median or evidence gap | Range and repeats | Change from first | Evidence |
|---|---|---|---|---|
| `single` / `completion_ms` | monotonic observed upper bound including telemetry publication and polling | | | |
| `single` / `op.rss_peak_bytes` | No qualified OP phase RSS sampling | | | |

### `nest.snapshot.fanout.wide@2`

snapshot · formal · 10,000 configured rows · Intel(R) Xeon(R) 6975P-C · ubuntu24 20261116.133.1 · JDK 21.0.13+9-LTS.

Measured 2026-11-25 in run 45544961925, attempt 1, at `e861698ed7dd419b9c16c7fd3012bf7c72e03765`.

| Arm / metric | Median or evidence gap | Range and repeats | Change from first | Evidence |
|---|---|---|---|---|
| `high-fanout` / `completion_ms` | monotonic observed upper bound including telemetry publication and polling | | | |
| `high-fanout` / `idle.rss_peak_bytes`<br>OP process, idle, procfs process status, children 40,000, roots 2,500 | 1185894400 B | 1178935296 to 1187332096 B · 3 repeats | Same reference | [Repeat 1](https://github.com/tapstate/tapstate-performance/blob/f33a9f5a80625fa85baba7880b2d12bbb8a95b1f/baselines/ubuntu-24.04-x64-op/sync-2026-11-25-v1/evidence/nest.snapshot.fanout.wide/1.json), [Repeat 2](https://github.com/tapstate/tapstate-performance/blob/f33a9f5a80625fa85baba7880b2d12bbb8a95b1f/baselines/ubuntu-24.04-x64-op/sync-2026-11-25-v1/evidence/nest.snapshot.fanout.wide/2.json), [Repeat 3](https://github.com/tapstate/tapstate-performance/blob/f33a9f5a80625fa85baba7880b2d12bbb8a95b1f/baselines/ubuntu-24.04-x64-op/sync-2026-11-25-v1/evidence/nest.snapshot.fanout.wide/3.json) |
| `high-fanout` / `readback.rss_peak_bytes`<br>OP process, readback, procfs process status, children 40,000, roots 2,500 | 1185681408 B | 1178533888 to 1187262464 B · 3 repeats | Same reference | [Repeat 1](https://github.com/tapstate/tapstate-performance/blob/f33a9f5a80625fa85baba7880b2d12bbb8a95b1f/baselines/ubuntu-24.04-x64-op/sync-2026-11-25-v1/evidence/nest.snapshot.fanout.wide/1.json), [Repeat 2](https://github.com/tapstate/tapstate-performance/blob/f33a9f5a80625fa85baba7880b2d12bbb8a95b1f/baselines/ubuntu-24.04-x64-op/sync-2026-11-25-v1/evidence/nest.snapshot.fanout.wide/2.json), [Repeat 3](https://github.com/tapstate/tapstate-performance/blob/f33a9f5a80625fa85baba7880b2d12bbb8a95b1f/baselines/ubuntu-24.04-x64-op/sync-2026-11-25-v1/evidence/nest.snapshot.fanout.wide/3.json) |
| `high-fanout` / `snapshot.rss_peak_bytes`<br>OP process, snapshot, procfs process status, children 40,000, roots 2,500 | 1185787904 B | 1178656768 to 1187647488 B · 3 repeats | Same reference | [Repeat 1](https://github.com/tapstate/tapstate-performance/blob/f33a9f5a80625fa85baba7880b2d12bbb8a95b1f/baselines/ubuntu-24.04-x64-op/sync-2026-11-25-v1/evidence/nest.snapshot.fanout.wide/1.json), [Repeat 2](https://github.com/tapstate/tapstate-performance/blob/f33a9f5a80625fa85baba7880b2d12bbb8a95b1f/baselines/ubuntu-24.04-x64-op/sync-2026-11-25-v1/evidence/nest.snapshot.fanout.wide/2.json), [Repeat 3](https://github.com/tapstate/tapstate-performance/blob/f33a9f5a80625fa85baba7880b2d12bbb8a95b1f/baselines/ubuntu-24.04-x64-op/sync-2026-11-25-v1/evidence/nest.snapshot.fanout.wide/3.json) |
| `high-fanout` / `startup.rss_peak_bytes`<br>OP process, startup, procfs process status, children 40,000, roots 2,500 | 463003648 B | 447340544 to 514850816 B · 3 repeats | Same reference | [Repeat 1](https://github.com/tapstate/tapstate-performance/blob/f33a9f5a80625fa85baba7880b2d12bbb8a95b1f/baselines/ubuntu-24.04-x64-op/sync-2026-11-25-v1/evidence/nest.snapshot.fanout.wide/1.json), [Repeat 2](https://github.com/tapstate/tapstate-performance/blob/f33a9f5a80625fa85baba7880b2d12bbb8a95b1f/baselines/ubuntu-24.04-x64-op/sync-2026-11-25-v1/evidence/nest.snapshot.fanout.wide/2.json), [Repeat 3](https://github.com/tapstate/tapstate-performance/blob/f33a9f5a80625fa85baba7880b2d12bbb8a95b1f/baselines/ubuntu-24.04-x64-op/sync-2026-11-25-v1/evidence/nest.snapshot.fanout.wide/3.json) |
| `ordinary` / `completion_ms` | monotonic observed upper bound including telemetry publication and polling | | | |
| `ordinary` / `idle.rss_peak_bytes`<br>OP process, idle, procfs process status, children 10,000, roots 2,500 | 905932800 B | 901042176 to 946454528 B · 3 repeats | Same reference | [Repeat 1](https://github.com/tapstate/tapstate-performance/blob/f33a9f5a80625fa85baba7880b2d12bbb8a95b1f/baselines/ubuntu-24.04-x64-op/sync-2026-11-25-v1/evidence/nest.snapshot.fanout.wide/1.json), [Repeat 2](https://github.com/tapstate/tapstate-performance/blob/f33a9f5a80625fa85baba7880b2d12bbb8a95b1f/baselines/ubuntu-24.04-x64-op/sync-2026-11-25-v1/evidence/nest.snapshot.fanout.wide/2.json), [Repeat 3](https://github.com/tapstate/tapstate-performance/blob/f33a9f5a80625fa85baba7880b2d12bbb8a95b1f/baselines/ubuntu-24.04-x64-op/sync-2026-11-25-v1/evidence/nest.snapshot.fanout.wide/3.json) |
| `ordinary` / `snapshot.rss_peak_bytes`<br>OP process, snapshot, procfs process status, children 10,000, roots 2,500 | 911511552 B | 900870144 to 943144960 B · 3 repeats | Same reference | [Repeat 1](https://github.com/tapstate/tapstate-performance/blob/f33a9f5a80625fa85baba7880b2d12bbb8a95b1f/baselines/ubuntu-24.04-x64-op/sync-2026-11-25-v1/evidence/nest.snapshot.fanout.wide/1.json), [Repeat 2](https://github.com/tapstate/tapstate-performance/blob/f33a9f5a80625fa85baba7880b2d12bbb8a95b1f/baselines/ubuntu-24.04-x64-op/sync-2026-11-25-v1/evidence/nest.snapshot.fanout.wide/2.json), [Repeat 3](https://github.com/tapstate/tapstate-performance/blob/f33a9f5a80625fa85baba7880b2d12bbb8a95b1f/baselines/ubuntu-24.04-x64-op/sync-2026-11-25-v1/evidence/nest.snapshot.fanout.wide/3.json) |
| `ordinary` / `startup.rss_peak_bytes`<br>OP process, startup, procfs process status, children 10,000, roots 2,500 | 540786688 B | 459268096 to 548126720 B · 3 repeats | Same reference | [Repeat 1](https://github.com/tapstate/tapstate-performance/blob/f33a9f5a80625fa85baba7880b2d12bbb8a95b1f/baselines/ubuntu-24.04-x64-op/sync-2026-11-25-v1/evidence/nest.snapshot.fanout.wide/1.json), [Repeat 2](https://github.com/tapstate/tapstate-performance/blob/f33a9f5a80625fa85baba7880b2d12bbb8a95b1f/baselines/ubuntu-24.04-x64-op/sync-2026-11-25-v1/evidence/nest.snapshot.fanout.wide/2.json), [Repeat 3](https://github.com/tapstate/tapstate-performance/blob/f33a9f5a80625fa85baba7880b2d12bbb8a95b1f/baselines/ubuntu-24.04-x64-op/sync-2026-11-25-v1/evidence/nest.snapshot.fanout.wide/3.json) |
