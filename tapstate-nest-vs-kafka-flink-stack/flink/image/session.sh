#!/bin/bash
# One container = one Flink session cluster: a JobManager and one TaskManager sharing a single
# CPU/memory cap. The stock entrypoint applies FLINK_PROPERTIES to the config for each role.
set -euo pipefail
export JOB_MANAGER_RPC_ADDRESS=localhost
/docker-entrypoint.sh jobmanager &
JM=$!
for _ in $(seq 60); do
  if wget -q -O /dev/null http://localhost:8081/overview; then break; fi
  sleep 1
done
/docker-entrypoint.sh taskmanager &
TM=$!
trap 'kill -TERM $TM $JM 2>/dev/null; wait' TERM INT
wait -n $JM $TM
