#!/bin/sh
# run-flink.sh FIXTURE LABEL
# The Debezium + Kafka + Flink protocol of the published runs (stack from ../flink, already up).
#   942:   plain copy, snapshot, then CDC 10/25/50/150/300/600 events/s for 120 s each
#   tierb: snapshot, then CDC 300/600/1000/1500/2500 events/s for 600 s each
# Mini-batch is on for the NEST job (set in sql/sources.sql) and off for the plain copy.
set -eu
FX=$1; L=$2
H=$(cd "$(dirname "$0")/../harness" && pwd)
OUT=${OUT:-$HOME/nestbench/runs}/$L
case "$FX" in
  942)   ARGS="--scenarios plain,snapshot,cdc --cdc-rates 10,25,50,150,300,600 --cdc-step-seconds 120" ;;
  tierb) ARGS="--scenarios snapshot,cdc --cdc-rates 300,600,1000,1500,2500 --cdc-step-seconds 600 --snapshot-timeout 57600" ;;
esac
mkdir -p "$OUT"
taskset -c 0,4 python3 "$H/nest_bench.py" --engine flink \
  --mongo-container nestbench-mongo --driver-container nestbench-driver \
  --fixture "$FX" $ARGS --cdc-continue --plain-flink-set table.exec.mini-batch.enabled=false \
  --label "$L" --output "$OUT" > "$OUT.log" 2>&1 || RC=$?
echo "EXIT=${RC:-0}" | tee -a "$OUT.log"
