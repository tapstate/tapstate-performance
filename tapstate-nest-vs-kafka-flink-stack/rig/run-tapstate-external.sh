#!/bin/sh
# run-tapstate-external.sh LABEL API_PORT CREDS STATE_CACHE_DB
# The external-MongoDB variant on the 34k fixture: the engine's storage, the bench source and the target
# all live on the MongoDB host set up by external-mongo-setup.sh. Snapshot, then CDC 600/s for 120 s,
# then 1000/s only if 600 held and 1500/s only if 1000 held; stops at the first step that does not hold.
# Uses EXT_IP, EXTCREDS (default ./extmongo-creds.json) and, for remote CPU sampling, EXT_SSH / SSH_KEY.
# The engine user's password is redacted from the run's log and meta.json.
set -eu
L=$1; PORT=$2; CREDS=$3; CACHE=$4
: "${EXT_IP:?set EXT_IP}"; EXTCREDS=${EXTCREDS:-./extmongo-creds.json}
H=$(cd "$(dirname "$0")/../harness" && pwd); R=$(cd "$(dirname "$0")" && pwd)
OUT=${OUT:-$HOME/nestbench/runs}/$L; mkdir -p "$OUT"
EP=$(python3 -c "import json;print(json.load(open('$EXTCREDS'))['engine']['password'])")
BASE="mongodb://nbengine:$EP@$EXT_IP:27017"
rm -f "$OUT.done"
if [ -n "${EXT_SSH:-}" ]; then sh "$R/remote-mongod-cpu.sh" "$OUT/remote-mongod-cpu.txt" "$OUT.done" & fi
taskset -c 0,4 python3 "$H/nest_bench.py" --api "http://127.0.0.1:$PORT" --credentials "$CREDS" \
  --mongo-container nestbench-mongo --driver-container nestbench-driver \
  --driver-mongo-uri "$BASE/?replicaSet=rs0&authSource=admin" \
  --engine-mongo-uri "$BASE/{database}?replicaSet=rs0&authSource=admin" \
  --state-cache-db "$CACHE" --nest-execution '{"parallelism": 2}' \
  --fixture 942 --scenarios snapshot,cdc --cdc-rates 600 --cdc-extra-if-held 1000,1500 \
  --cdc-step-seconds 120 --cdc-continue --cdc-stop-after-failures 1 \
  --label "$L" --output "$OUT" > "$OUT.log" 2>&1 || RC=$?
touch "$OUT.done"; wait
sed -i "s/$EP/***/g" "$OUT.log"
if grep -rqF -- "$EP" "$OUT" "$OUT.log"; then echo "warning: the engine password appears in $OUT; do not publish it" >&2; fi
echo "EXIT=${RC:-0}" | tee -a "$OUT.log"
