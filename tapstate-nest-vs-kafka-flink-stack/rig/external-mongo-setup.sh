#!/bin/sh
# external-mongo-setup.sh: MongoDB 7.0 on a separate host, for the external-MongoDB variant.
# Run from the engine host. Needs SSH to the MongoDB host as a sudo user.
#   EXT_SSH   SSH target, e.g. ubuntu@10.0.1.20                      (required)
#   EXT_IP    the MongoDB host's private address the engine reaches  (required)
#   SSH_KEY   private key for EXT_SSH                                 (default: ssh's own default)
#   DATA_DEV  blank block device for the data volume                  (default /dev/nvme1n1)
#   CACHE_GB  WiredTiger cache size                                   (default 16)
#   CREDS     where to keep the generated passwords, mode 600         (default ./extmongo-creds.json)
# What it does on the MongoDB host: formats DATA_DEV as XFS (refuses unless it is blank or already
# mounted at /data), mounts it at /data with noatime, installs mongodb-org 7.0 from repo.mongodb.org,
# configures replica set rs0 with authorization and a keyFile (mongod 7.0 requires a keyFile whenever
# authorization is on for a replica set, even a single member), raises nofile to 64000, and creates an
# admin user (root) and an engine user (readWriteAnyDatabase, dbAdminAnyDatabase, clusterMonitor).
# Passwords are generated locally and sent over SSH stdin; they are never printed.
# The benchmark used Ubuntu 26.04 and the 7.0 "jammy" packages (there is no newer 7.0 suite; the
# host's libssl3t64 provides libssl3). The host's security group must allow TCP 27017 from the engine host.
set -eu
: "${EXT_SSH:?set EXT_SSH}" "${EXT_IP:?set EXT_IP}"
DATA_DEV=${DATA_DEV:-/dev/nvme1n1}; CACHE_GB=${CACHE_GB:-16}; CREDS=${CREDS:-./extmongo-creds.json}
SSH="ssh ${SSH_KEY:+-i $SSH_KEY} -o BatchMode=yes $EXT_SSH"
[ -f "$CREDS" ] || (umask 077; python3 -c "import json,secrets;json.dump({'admin':{'user':'nbadmin','password':secrets.token_urlsafe(24)},'engine':{'user':'nbengine','password':secrets.token_urlsafe(24)}},open('$CREDS','w'))")
chmod 600 "$CREDS"

# 1. Data volume.
$SSH "set -e; if ! mountpoint -q /data; then [ -z \"\$(sudo blkid $DATA_DEV)\" ] || { echo '$DATA_DEV is not blank'; exit 1; }
  sudo mkfs.xfs -q $DATA_DEV; U=\$(sudo blkid -s UUID -o value $DATA_DEV); sudo mkdir -p /data
  echo \"UUID=\$U /data xfs defaults,noatime,nofail 0 2\" | sudo tee -a /etc/fstab >/dev/null; sudo systemctl daemon-reload; sudo mount /data; fi
  findmnt /data -o TARGET,SOURCE,FSTYPE,OPTIONS"

# 2. MongoDB Community 7.0.
$SSH 'set -e; sudo apt-get -qq update; sudo apt-get -qq install -y gnupg curl
  curl -fsSL https://www.mongodb.org/static/pgp/server-7.0.asc | sudo gpg --dearmor -o /usr/share/keyrings/mongodb-server-7.0.gpg --yes
  echo "deb [ arch=amd64,arm64 signed-by=/usr/share/keyrings/mongodb-server-7.0.gpg ] https://repo.mongodb.org/apt/ubuntu jammy/mongodb-org/7.0 multiverse" | sudo tee /etc/apt/sources.list.d/mongodb-org-7.0.list >/dev/null
  sudo apt-get -qq update; sudo apt-get -qq install -y mongodb-org; mongod --version | head -1'

# 3. Configuration: data and journal on /data, rs0, private bind address, cache, nofile 64000.
$SSH "set -e; sudo mkdir -p /data/db; sudo chown -R mongodb:mongodb /data/db
  printf 'storage:\n  dbPath: /data/db\n  wiredTiger:\n    engineConfig:\n      cacheSizeGB: $CACHE_GB\nsystemLog:\n  destination: file\n  logAppend: true\n  path: /var/log/mongodb/mongod.log\nnet:\n  port: 27017\n  bindIp: 127.0.0.1,$EXT_IP\nreplication:\n  replSetName: rs0\nprocessManagement:\n  timeZoneInfo: /usr/share/zoneinfo\n' | sudo tee /etc/mongod.conf >/dev/null
  sudo mkdir -p /etc/systemd/system/mongod.service.d
  printf '[Service]\nLimitNOFILE=64000\n' | sudo tee /etc/systemd/system/mongod.service.d/limits.conf >/dev/null
  sudo systemctl daemon-reload; sudo systemctl enable --now mongod; sleep 3; systemctl is-active mongod"

# 4. Replica set and users (localhost exception before auth), then authorization + keyFile and restart.
python3 -c "import json;d=json.load(open('$CREDS'));print(d['admin']['password']);print(d['engine']['password'])" | $SSH "set -e; read AP; read EP
  mongosh --quiet --eval 'rs.initiate({_id:\"rs0\",members:[{_id:0,host:\"$EXT_IP:27017\"}]})' >/dev/null
  for i in \$(seq 30); do mongosh --quiet --eval 'db.hello().isWritablePrimary' | grep -q true && break; sleep 1; done
  mongosh --quiet admin --eval \"db.createUser({user:'nbadmin',pwd:'\$AP',roles:['root']})\" >/dev/null
  mongosh --quiet admin -u nbadmin -p \"\$AP\" --eval \"db.createUser({user:'nbengine',pwd:'\$EP',roles:['readWriteAnyDatabase','dbAdminAnyDatabase','clusterMonitor']})\" >/dev/null
  sudo test -f /etc/mongod.keyfile || sudo sh -c 'openssl rand -base64 756 > /etc/mongod.keyfile'
  sudo chown mongodb:mongodb /etc/mongod.keyfile; sudo chmod 400 /etc/mongod.keyfile
  grep -q '^security:' /etc/mongod.conf || printf 'security:\n  authorization: enabled\n  keyFile: /etc/mongod.keyfile\n' | sudo tee -a /etc/mongod.conf >/dev/null
  sudo systemctl restart mongod; sleep 3; systemctl is-active mongod
  mongosh --quiet admin -u nbadmin -p \"\$AP\" --eval 'db.setProfilingLevel(0,{slowms:100}); print(rs.status().members.map(m=>m.name+\" \"+m.stateStr).join(\",\"))'"
echo "MongoDB on $EXT_IP is up. Check the round trip from the engine host before a run:"
echo "  docker exec nestbench-driver mongosh --quiet \"mongodb://nbengine:<password>@$EXT_IP:27017/?replicaSet=rs0&authSource=admin\" --eval 'for(let i=0;i<5;i++){const t=Date.now();db.runCommand({ping:1});print(Date.now()-t)}'"
