#!/bin/sh
# setup-host.sh: the shared containers both engines use.
#   nestbench-net     Docker network
#   nestbench-mongo   MongoDB 7.0 single-member replica set "nbrs" on vCPUs 2,6, no CPU/memory cap.
#                     It holds the source, the target, and Tapstate's configuration/cache databases.
#   nestbench-driver  same image, idle; the harness runs every mongosh call (seed, load driver,
#                     lag probes, content checks) here on vCPUs 0,4, so 2,6 serve only mongod.
# The benchmark used mongod 7.0.43 and mongosh 2.10.0. MONGO_IMAGE must contain both binaries.
set -eu
MI=${MONGO_IMAGE:-mongo:7.0}
docker network inspect nestbench-net >/dev/null 2>&1 || docker network create nestbench-net
docker volume create nestbench-mongo-data >/dev/null; docker volume create nestbench-mongo-config >/dev/null
docker run -d --name nestbench-mongo --network nestbench-net --hostname nestbench-mongo --cpuset-cpus 2,6 \
  --ulimit nofile=64000:64000 \
  -v nestbench-mongo-data:/data/db -v nestbench-mongo-config:/data/configdb "$MI" \
  mongod --replSet nbrs --bind_ip_all --port 27017
for i in $(seq 30); do docker exec nestbench-mongo mongosh --quiet --eval 'db.runCommand({ping:1}).ok' >/dev/null 2>&1 && break; sleep 2; done
docker exec nestbench-mongo mongosh --quiet --eval 'rs.initiate({_id:"nbrs",members:[{_id:0,host:"nestbench-mongo:27017"}]})'
docker run -d --name nestbench-driver --network nestbench-net --cpuset-cpus 0,4 --entrypoint sleep "$MI" infinity
# Keep the server-wide slow-operation threshold at its default and profiling off. A profiler left
# at slowms 0 logs every operation and measurably slows mongod (see the README caveats).
docker exec nestbench-mongo mongosh --quiet --eval 'db.setProfilingLevel(0,{slowms:100}); print(JSON.stringify(db.getProfilingStatus()))'
