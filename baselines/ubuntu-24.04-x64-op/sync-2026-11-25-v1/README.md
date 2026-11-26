# Synchronization baseline sync-2026-11-25-v1

Measured on November 25, 2026, on standard GitHub-hosted Linux runners with single-node Tapstate OP. The [baseline](baseline.json) holds the original formal measurements, execution gaps, and the accepted snapshot RSS rules. [Run evidence](evidence/run.json) identifies the code, runner environments, and artifacts. [Formal manifest](evidence/manifest.json) records the exact selected recipes. [Calibration evidence](evidence/calibration.json) records the independent reruns, accepted budgets, and comparisons.

| Outcome | Cases | Repeats |
| --- | ---: | ---: |
| Completed | 45 | 140 |
| Failed cases and incomplete repeats | 9 | 22 |
| Timed out | 1 | 3 |
| Did not start | 9 | 27 |

The table counts case verdicts and individual repeat statuses independently. Some failed cases contain a completed repeat. The original report and per-case evidence preserve those results. The unstarted batch encountered Maven Central HTTP 429 during the build.

The measurements bind to Tapstate commit [e861698ed7dd419b9c16c7fd3012bf7c72e03765](https://github.com/tapstate/tapstate/tree/e861698ed7dd419b9c16c7fd3012bf7c72e03765). Use the Pipeline Performance workflow and the case IDs and versions in the formal manifest to reproduce the workloads. The [original Actions attempt](https://github.com/tapstate/tapstate/actions/runs/45544961925/attempts/1) also identifies its input, batch, and report artifacts.

A measured group in the baseline lists the eligible repeat values, their units, and the receipt for each sample. Recompute the median and range from that group. For OP process RSS and GC, the repeat receipt also lists compressed raw sample files and the compressed and uncompressed SHA-256 digests. Timing observations that include telemetry publication and polling remain evidence with their original bounds. The formal run has no qualified end-to-end p95 or backlog throughput reference.
