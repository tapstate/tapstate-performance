#!/bin/sh
# run-tapstate.sh FIXTURE LABEL API_PORT CREDS STATE_CACHE_DB [SOURCE_DB]
# The Tapstate protocol of the published runs. FIXTURE is 942 (34k rows) or tierb (3.4M rows).
#   942:   snapshot, then CDC 10/25/50/150/300 events/s for 120 s each, plus 600/s if 300 held
#   tierb: snapshot, then CDC 150/300/600/1000 events/s for 600 s each, stop after two failed steps
# Pass SOURCE_DB to reuse an already seeded, unmutated Tier B source (seeding takes ~35 s; the
# plain copy is not needed for the comparison).
set -eu
FX=$1; L=$2; PORT=$3; CREDS=$4; CACHE=$5; SRC=${6:-}
H=$(cd "$(dirname "$0")/../harness" && pwd)
OUT=${OUT:-$HOME/nestbench/runs}/$L
case "$FX" in
  942)   STEPS="--cdc-rates 10,25,50,150,300 --cdc-step-seconds 120 --cdc-extra-if-held 600" ;;
  tierb) STEPS="--cdc-rates 150,300,600,1000,1500 --cdc-step-seconds 600 --cdc-stop-after-failures 2 --snapshot-timeout 14400" ;;
esac
mkdir -p "$OUT"
taskset -c 0,4 python3 "$H/nest_bench.py" --api "http://127.0.0.1:$PORT" --credentials "$CREDS" \
  --mongo-container nestbench-mongo --driver-container nestbench-driver \
  --engine-mongo-uri 'mongodb://nestbench-mongo:27017/{database}?replicaSet=nbrs' \
  --state-cache-db "$CACHE" --nest-execution '{"parallelism": 2}' \
  --fixture "$FX" ${SRC:+--source-db "$SRC"} --scenarios snapshot,cdc $STEPS --cdc-continue \
  --label "$L" --output "$OUT" > "$OUT.log" 2>&1 || RC=$?
echo "EXIT=${RC:-0}" | tee -a "$OUT.log"
