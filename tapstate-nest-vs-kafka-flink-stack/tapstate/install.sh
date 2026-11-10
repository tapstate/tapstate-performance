#!/bin/sh
# install.sh NAME IMAGE PORT SUFFIX CREDS [extra JAVA_TOOL_OPTIONS]
# Installs one Tapstate server the documented on-prem way and leaves it running:
#   initialize an installation directory, start the server, test and commit three-layer MongoDB
#   storage on the management channel, restart, authorize until FIRST_ADMIN, create the first
#   administrator (random password, written to CREDS with mode 600), and check a login.
# The engine container is pinned like the Flink TaskManager: vCPUs 1,5, 2 CPUs, 8 GB.
# Storage databases are tapstate_config$SUFFIX, tapstate_cache$SUFFIX and tapstate_views$SUFFIX on
# nestbench-mongo, so several installs can share one mongod (run only one engine at a time).
# Example: install.sh nestbench-tapstate nestbench/tapstate:tierb 38183 _tierb ./creds-tierb.json \
#            -Dtapstate.nest.store=direct
set -eu
N=$1; IMG=$2; PORT=$3; SFX=$4; CREDS=$5; EXTRA=${6:-}
VOL=$N-install
D=/var/lib/tapstate/inst/installation
J="java -jar /opt/tapstate/tapstate.jar"
CONNECTORS=${CONNECTORS:-$(cd "$(dirname "$0")" && pwd)/connectors}
test -f "$CONNECTORS/mongodb-connector.jar" || { echo "missing $CONNECTORS/mongodb-connector.jar (see README)" >&2; exit 1; }
docker volume create "$VOL" >/dev/null
docker run --rm -u 0 -v "$VOL":/var/lib/tapstate/inst --entrypoint sh "$IMG" -c 'chown 10001:10001 /var/lib/tapstate/inst && chmod 700 /var/lib/tapstate/inst'
docker run --rm --network nestbench-net -v "$VOL":/var/lib/tapstate/inst --entrypoint sh "$IMG" -c "$J installation --initialize --tapstate.installation.directory=$D" | tail -2
docker run -d --name "$N" --network nestbench-net --hostname "$N" --cpus=2 --cpuset-cpus=1,5 --memory=8g --stop-timeout 60 \
  -p 127.0.0.1:$PORT:$PORT -v "$VOL":/var/lib/tapstate/inst -v "$CONNECTORS":/opt/tapstate/connectors:ro \
  -e JAVA_TOOL_OPTIONS="-XX:MaxRAMPercentage=65.0 $EXTRA" \
  --entrypoint java "$IMG" -jar /opt/tapstate/tapstate.jar --role=all \
  --tapstate.installation.directory=$D --tapstate.connectors.seed-dir=/opt/tapstate/connectors \
  --server.port=$PORT --server.address=0.0.0.0 >/dev/null
ready() { for i in $(seq 120); do docker logs --since "$1" "$N" 2>&1 | grep -q "application is ready" && return 0; sleep 2; done; return 1; }
ready 10m
# Management-channel call from inside the container: the port and setup capability are read there,
# so the capability token never leaves the container.
mg() { docker exec -i "$N" sh -c '
PORT=$(sed -n "s/.*\"managementUrl\":\"http:\/\/127.0.0.1:\([0-9]*\)\".*/\1/p" '$D'/stage.json)
TOK=$(sed -n "s/.*\"token\":\"\([^\"]*\)\".*/\1/p" '$D'/capability.json 2>/dev/null)
curl -sS --max-time 120 -X POST -H "Host: 127.0.0.1:$PORT" -H "Content-Type: application/json" -H "X-Tapstate-Setup-Capability: $TOK" --data-binary @- "http://127.0.0.1:$PORT$0"' "$1"; }
st() { echo '{}' | mg /api/storage/status; }
js() { python3 -c "import sys,json;print(json.load(sys.stdin)['$1'])"; }
S=$(st); OP=$(echo "$S" | js operationId); GEN=$(echo "$S" | js setupGeneration)
CAND=$(python3 -c "
import json;b='mongodb://nestbench-mongo:27017'
c=lambda d:{'kind':'MONGODB','uri':f'{b}/{d}?replicaSet=nbrs','database':d}
print(json.dumps({'configuration':c('tapstate_config$SFX'),'cache':c('tapstate_cache$SFX'),'master':c('tapstate_views$SFX')}))")
STAMP=$(echo "{\"operationId\":\"$OP\",\"generation\":$GEN,\"candidate\":$CAND,\"layer\":\"CACHE\"}" | mg /api/storage/test | js testStamp)
echo "{\"operationId\":\"$OP\",\"generation\":$GEN,\"candidate\":$CAND,\"testStamps\":{\"CACHE\":\"$STAMP\"}}" | mg /api/storage/setup/commit; echo
for i in $(seq 60); do st | grep -q '"setupPhase":"COMPLETE"' && break; sleep 3; done
docker stop -t 60 "$N" >/dev/null; RS=$(date -u +%FT%TZ); docker start "$N" >/dev/null; ready "$RS"
for i in 1 2 3 4; do
  docker exec "$N" sh -c "$J installation --authorize --tapstate.installation.directory=$D --server.port=0" >/dev/null 2>&1 || true
  P=$(docker exec "$N" sh -c "sed -n 's/.*\"purpose\":\"\([A-Z_]*\)\".*/\1/p' $D/capability.json"); echo "authorize -> $P"
  [ "$P" = FIRST_ADMIN ] && break
  S=$(st); G=$(echo "$S" | js setupGeneration); BV=$(echo "$S" | js bindingVersion)
  echo "$S" | grep -q storage.setup.activate && { echo "{\"operationId\":\"$OP\",\"generation\":$G,\"bindingVersion\":$BV}" | mg /api/storage/setup/activate; echo; }
  sleep 10
done
umask 077; python3 -c "import json,secrets;json.dump({'username':'nestbench-admin','password':secrets.token_urlsafe(24)},open('$CREDS','w'))"
mg /installation/first-admin < "$CREDS"; echo
python3 - "$PORT" "$CREDS" <<'PY'
import json,sys,urllib.request
c=json.load(open(sys.argv[2])); u='http://127.0.0.1:%s'%sys.argv[1]
t=json.loads(urllib.request.urlopen(urllib.request.Request(u+'/auth/login',json.dumps({**c,'createSession':False}).encode(),{'Content-Type':'application/json'}),timeout=30).read())['token']
m=json.loads(urllib.request.urlopen(urllib.request.Request(u+'/api/cluster/members',headers={'Authorization':'Bearer '+t}),timeout=30).read())
print('login ok, members', [x['state'] for x in m['members']])
PY
