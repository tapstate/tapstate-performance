#!/usr/bin/env python3
"""NEST benchmark harness: Tapstate (on-prem server) or Debezium + Kafka + Flink, same fixtures and checks.

Scenarios (each run writes JSON evidence under --output):

  plain     plain copy of the three source collections, snapshot only; the denominator
  snapshot  NEST order document, snapshot phase: start request -> all root documents present
            and a sampled content check passes
  cdc       continues the snapshot pipeline in CDC and drives stepped fixed-rate change load;
            reports the highest rate that holds without lag building up
  join      join pipeline (lines as the fact, orders as the dimension, one wide row per line),
            snapshot phase: start request -> one row per line, each carrying its order's columns,
            and a sampled content check passes (Tapstate only)
  join-cdc  continues the join pipeline in CDC with the same stepped load and hold rule as cdc

With --driver-container set, every load and CDC result also carries the store commands it cost
(`store`): the per-phase delta of each mongod's opcounters, divided by source rows for a load and
by events sent for a CDC step.

Fixtures:
  942    1,000 customers, 10,000 orders, 23,000 lines (the "34k" fixture, 34,000 rows)
  tierb  100,000 customers, 1,000,000 orders, 2,300,000 lines, the "Tier B" fixture (3.4M rows):
         every 10th order has no lines, every 25th order references a missing customer.

Engines (--engine): `tapstate` (default) drives a running Tapstate OP through its REST API;
`flink` drives the Debezium + Kafka + Flink stack of ../flink (Kafka Connect REST for the
Debezium MongoDB source, Flink SQL client inside the Flink container, Flink REST for job state).
Seed, content check and the CDC driver are the same for both.

The harness never starts, stops or rebuilds the runtime. It talks to the engine through its REST
API and to the engine's MongoDB through `docker exec mongosh` in the Mongo container.

Example:
  python3 nest_bench.py --api http://127.0.0.1:38183 --credentials creds.json \
      --mongo-container nestbench-mongo --driver-container nestbench-driver \
      --engine-mongo-uri 'mongodb://nestbench-mongo:27017/{database}?replicaSet=nbrs' \
      --fixture tierb --scenarios snapshot,cdc --nest-execution '{"parallelism": 2}' \
      --cdc-rates 150,300,600,1000 --cdc-step-seconds 600 --cdc-continue --output runs/tierb-1
"""
import argparse
import json
import pathlib
import re
import subprocess
import threading
import time
import urllib.error
import urllib.request
import uuid

MARK = '__NESTBENCH__'
TABLES = ['BENCH_CUSTOMERS', 'BENCH_LINES', 'BENCH_ORDERS']
FIXTURES = {'942': {'customers': 1000, 'orders': 10000}, 'tierb': {'customers': 100000, 'orders': 1000000}}
PROBE_ORDER = 7  # has lines and an existing customer in both fixtures; excluded from random load
OPCOUNTERS = ('insert', 'query', 'update', 'delete', 'getmore', 'command')
# The join scenario: every line widened with its order's columns. The carrier matches every
# dimension against the fact source, so the customer (keyed by the order, not the line) is left out.
JOIN_SQL = ('SELECT l._id AS LINE_ID, l.ORDER_ID AS ORDER_ID, l.LINE_NO AS LINE_NO, l.SKU AS SKU, '
            'l.QTY AS QTY, l.PRICE AS PRICE, o.STATUS AS STATUS, o.CUSTOMER_ID AS CUSTOMER_ID '
            'FROM l JOIN o ON l.ORDER_ID = o.ORDER_ID')


class Bench:
    def __init__(self, args):
        self.args = args
        self.out = pathlib.Path(args.output)
        self.out.mkdir(parents=True, exist_ok=True)
        self.token = None
        self.mode = 'nest'
        creds = json.loads(pathlib.Path(args.credentials).read_text()) if args.credentials else {}
        self.username = args.username or creds.get('username')
        self.password = args.password or creds.get('password')

    # ---------- plumbing ----------
    def write(self, name, value):
        (self.out / name).write_text(json.dumps(value, indent=2, default=str) + '\n')

    def log(self, name, value):
        with (self.out / name).open('a') as f:
            f.write(json.dumps(value, default=str) + '\n')

    def mongo(self, program, timeout=600):
        if self.args.driver_container:
            # A separate mongosh container (pinned off the engine and Mongo cores) runs the load
            # driver, probes and checks over the network, so Mongo's cores serve only the server.
            argv = ['docker', 'exec', '-i', self.args.driver_container, 'mongosh', '--quiet', '--norc',
                    self.args.driver_mongo_uri, '--file', '/dev/stdin']
        else:
            argv = ['docker', 'exec', '-i', self.args.mongo_container, 'mongosh', '--quiet', '--norc',
                    '--port', str(self.args.mongo_port), '--file', '/dev/stdin']
        r = subprocess.run(argv, input=program, text=True, capture_output=True, timeout=timeout)
        if r.returncode:
            raise RuntimeError('mongosh failed: ' + r.stderr[-2000:])
        for line in reversed(r.stdout.splitlines()):
            if line.startswith(MARK):
                return json.loads(line[len(MARK):])
        raise RuntimeError('mongosh printed no result: ' + r.stdout[-2000:])

    def login(self):
        body = json.dumps({'username': self.username, 'password': self.password, 'createSession': False}).encode()
        req = urllib.request.Request(self.args.api + '/auth/login', body, {'Content-Type': 'application/json'})
        with urllib.request.urlopen(req, timeout=30) as r:
            self.token = json.loads(r.read())['token']

    def api(self, path, method='GET', body=None, ok=(200,)):
        for attempt in range(2):
            if not self.token:
                self.login()
            data = None if body is None else json.dumps(body).encode()
            req = urllib.request.Request(self.args.api + path, data, method=method, headers={
                'Authorization': 'Bearer ' + self.token, 'Content-Type': 'application/json'})
            try:
                with urllib.request.urlopen(req, timeout=60) as r:
                    status, text = r.status, r.read()
            except urllib.error.HTTPError as e:
                status, text = e.code, e.read()
            if status == 401 and attempt == 0:
                self.token = None
                continue
            parsed = json.loads(text) if text.strip() else {}
            if status not in ok:
                raise RuntimeError(f'{method} {path} -> {status}: {json.dumps(parsed)[:1000]}')
            return parsed

    def start_sampler(self):
        """Sample docker stats for every container every --stats-interval seconds, tagged with the
        current phase. Runs in the harness process (pin the harness off the engine cores)."""
        self.phase = 'setup'
        self.sampling = True
        t0 = time.monotonic()

        def loop():
            while self.sampling:
                tick = time.monotonic()
                try:
                    self.log('docker-stats.jsonl', {'phase': self.phase, 't': tick - t0, 'unix': time.time(),
                                                    'stats': self.docker_stats()})
                except Exception as e:  # sampling must never break a run
                    self.log('docker-stats.jsonl', {'phase': self.phase, 't': tick - t0, 'error': str(e)})
                time.sleep(max(0.0, self.args.stats_interval - (time.monotonic() - tick)))
        self.sampler = threading.Thread(target=loop, daemon=True)
        self.sampler.start()
        if self.args.driver_container:
            self.mongod_sampler = threading.Thread(target=self.mongod_loop, args=(t0,), daemon=True)
            self.mongod_sampler.start()

    def mongod_loop(self, t0):
        """Every --stats-interval s, serverStatus counters of each mongod (source/state server and,
        when set, the target server): opcounters, transactions, WiredTiger cache; during the idle
        phase also the active operations (namespace, op type, command name only)."""
        servers = {'source': self.args.driver_mongo_uri}
        if self.args.target_mongo_uri:
            servers['target'] = self.args.target_mongo_uri
        prog = r'''
const out={};
for (const [name,uri] of Object.entries(%s)) {
  const a=new Mongo(uri).getDB('admin'); const s=a.serverStatus({repl:0,locks:0});
  const c=s.wiredTiger.cache, tx=s.transactions||{};
  const mc=(s.metrics&&s.metrics.commands)||{}, ct=n=>mc[n]?Number(mc[n].total):null;
  const cmds={listIndexes:ct('listIndexes'),listCollections:ct('listCollections'),total:Object.values(mc).reduce((a,v)=>a+((v&&v.total!=null)?Number(v.total):0),0)};
  const r={opcounters:s.opcounters, commands:cmds, transactions:{started:tx.totalStarted,committed:tx.totalCommitted,aborted:tx.totalAborted},
    cache:{bytes:c['bytes currently in the cache'],dirty:c['tracked dirty bytes in the cache'],pagesRead:c['pages read into cache'],pagesWritten:c['pages written from cache']}};
  if (%s) r.ops=a.aggregate([{$currentOp:{allUsers:true,idleConnections:false}},{$match:{active:true}},{$project:{_id:0,ns:1,op:1,cmd:{$first:{$objectToArray:'$command'}}}}]).toArray().map(o=>[o.ns,o.op,o.cmd?o.cmd.k:null]);
  out[name]=r;
}
print(%s+EJSON.stringify(out,{relaxed:true}));'''
        state = ''
        if self.args.state_cache_db:
            # Per-namespace operation counts of the engine's durable cache, and the running pipeline's
            # write fence and actuation claim (state-side cost and the lease's effect on fencing).
            state = r'''
{ const a=new Mongo(%(uri)s).getDB('admin'), C=a.getSiblingDB(%(cache)s), pid=%%s, top=a.runCommand({top:1}).totals, t={};
  for (const [ns,v] of Object.entries(top)) if (ns.startsWith(%(cache)s+'.')) t[ns.slice(%(cache)s.length+1)]={total:v.total.count,read:v.readLock.count,write:v.writeLock.count,queries:v.queries.count,insert:v.insert.count,update:v.update.count,remove:v.remove.count,getmore:v.getmore.count,commands:v.commands.count};
  const ps=pid&&C.pipeline_state.findOne({_id:pid},{runtimeWriteFence:1});
  const cl=pid&&C.workload_claims.findOne({resourceType:'PIPELINE_ACTUATION',resourceId:pid});
  out.state={top:t,pipeline:pid,runtimeWriteFence:ps?ps.runtimeWriteFence:null,
    claim:cl?{ownerNodeId:cl.ownerNodeId,ownerBootId:cl.ownerBootId,claimGeneration:cl.claimGeneration,leaseUntil:cl.leaseUntil,fencedPipelineWrites:cl.fencedPipelineWrites}:null}; }
''' % {'uri': json.dumps(self.args.driver_mongo_uri), 'cache': json.dumps(self.args.state_cache_db)}
        prog = prog.replace("print(%s+EJSON.stringify(out,{relaxed:true}));", "%s\nprint(%s+EJSON.stringify(out,{relaxed:true}));")
        while self.sampling:
            tick = time.monotonic()
            try:
                st = state % json.dumps(getattr(self, 'current_pid', None)) if state else ''
                r = self.mongo(prog % (json.dumps(servers), 'true' if self.phase == 'idle' else 'false', st, json.dumps(MARK)), timeout=60)
                self.log('mongod-stats.jsonl', {'phase': self.phase, 't': tick - t0, 'unix': time.time(), **r})
            except Exception as e:
                self.log('mongod-stats.jsonl', {'phase': self.phase, 't': tick - t0, 'error': str(e)})
            time.sleep(max(0.0, self.args.stats_interval - (time.monotonic() - tick)))

    def docker_stats(self):
        r = subprocess.run(['docker', 'stats', '--no-stream', '--format', '{{json .}}'],
                           text=True, capture_output=True, timeout=60)
        return [json.loads(l) for l in r.stdout.splitlines() if l.strip()]

    # ---------- engine control ----------
    def status(self, pid):
        if self.args.engine == 'flink':
            return self.flink_status(pid)
        return self.api('/api/pipelines/%s/status' % pid, ok=(200, 404))

    def start(self, pid):
        self.current_pid = pid
        if self.args.engine == 'flink':
            return self.flink_start(pid)
        self.api('/api/pipelines/%s:start' % pid, 'POST')

    def stop(self, pid):
        if self.args.engine == 'flink':
            return self.flink_stop(pid)
        self.api('/api/pipelines/%s:stop' % pid, 'POST', {'purgeState': False}, ok=(200, 202, 404, 409))

    def engine_info(self):
        if self.args.engine == 'flink':
            return {'flink': self.http(self.args.flink_url + '/overview'),
                    'connect': self.http(self.args.connect_url + '/'),
                    'connectorPlugins': [c['class'] for c in self.http(self.args.connect_url + '/connector-plugins')
                                         if 'mongodb' in c['class'].lower()]}
        return self.api('/api/cluster/members')

    @staticmethod
    def http(url, method='GET', body=None, ok=(200,)):
        data = None if body is None else json.dumps(body).encode()
        req = urllib.request.Request(url, data, method=method, headers={'Content-Type': 'application/json'})
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                status, text = r.status, r.read()
        except urllib.error.HTTPError as e:
            status, text = e.code, e.read()
        if status not in ok:
            raise RuntimeError(f'{method} {url} -> {status}: {text[:1000]!r}')
        return json.loads(text) if text.strip() else {}

    def flink_define(self, pid, sql_name, source_db, target_db):
        """Record a Flink pipeline: its Debezium connector (one per pipeline, so each scenario
        re-reads the source from a fresh snapshot into its own topics) and its SQL script."""
        sql_dir = pathlib.Path(self.args.flink_sql_dir)
        values = {'TOPIC_PREFIX': pid, 'SOURCE_DB': source_db, 'TARGET_DB': target_db, 'JOB': pid,
                  'BOOTSTRAP': self.args.kafka_bootstrap, 'MONGO_URI': self.args.flink_mongo_uri,
                  'SINK_OPTIONS': ''.join(", '%s' = '%s'" % kv for kv in json.loads(self.args.sink_options).items())}
        extra = self.args.flink_set + (self.args.plain_flink_set if sql_name == 'plain.sql' else [])
        sets = ''.join("SET '%s' = '%s';\n" % tuple(x.split('=', 1)) for x in extra)
        # Command-line SETs come after sources.sql, so they override its defaults (e.g. mini-batch).
        script = (sql_dir / 'sources.sql').read_text() + '\n' + sets + (sql_dir / sql_name).read_text()
        for k, v in values.items():
            script = script.replace('${%s}' % k, v)
        collections = ','.join('%s\\.%s' % (source_db, n) for n in TABLES)
        connector = {'name': pid, 'config': {
            'connector.class': 'io.debezium.connector.mongodb.MongoDbConnector',
            'mongodb.connection.string': self.args.debezium_mongo_uri,
            'topic.prefix': pid,
            'collection.include.list': collections,
            'capture.mode': 'change_streams_update_full',
            'snapshot.mode': 'initial',
            'tombstones.on.delete': 'false',
            'transforms': 'unwrap,key',
            'transforms.unwrap.type': 'io.debezium.connector.mongodb.transforms.ExtractNewDocumentState',
            'transforms.unwrap.delete.tombstone.handling.mode': 'drop',
            'transforms.key.type': 'org.apache.kafka.connect.transforms.ValueToKey',
            'transforms.key.fields': '_id'}}
        connector['config'].update(json.loads(self.args.debezium_config))
        self.flink = getattr(self, 'flink', {})
        self.flink[pid] = {'connector': connector, 'sql': script, 'job': None}
        (self.out / (pid + '-flink.sql')).write_text(script)
        self.write(pid + '-debezium.json', connector)

    def flink_start(self, pid):
        spec = self.flink[pid]
        self.http(self.args.connect_url + '/connectors', 'POST', spec['connector'], ok=(201,))
        r = subprocess.run(['docker', 'exec', '-i', self.args.flink_container, 'sh', '-c',
                            'cat > /tmp/%s.sql && /opt/flink/bin/sql-client.sh -f /tmp/%s.sql' % (pid, pid)],
                           input=spec['sql'], text=True, capture_output=True, timeout=600)
        (self.out / (pid + '-sql-client.log')).write_text(r.stdout + r.stderr)
        jobs = [l.split('Job ID:')[1].strip() for l in r.stdout.splitlines() if 'Job ID:' in l]
        if r.returncode or not jobs:
            raise RuntimeError('Flink SQL submission failed: ' + (r.stdout + r.stderr)[-2000:])
        spec['job'] = jobs[-1]

    def flink_status(self, pid):
        spec = getattr(self, 'flink', {}).get(pid)
        if not spec or not spec['job']:
            return {}
        job = self.http('%s/jobs/%s' % (self.args.flink_url, spec['job']), ok=(200, 404))
        con = self.http('%s/connectors/%s/status' % (self.args.connect_url, pid), ok=(200, 404))
        # A job that keeps restarting (e.g. it cannot get its slots) never makes progress: after
        # two minutes in RESTARTING it counts as failed instead of waiting out the phase timeout.
        if job.get('state') == 'RESTARTING':
            spec.setdefault('restartingSince', time.monotonic())
        else:
            spec.pop('restartingSince', None)
        stuck = time.monotonic() - spec.get('restartingSince', time.monotonic()) > 120
        failed = stuck or job.get('state') in ('FAILED', 'FAILING') or con.get('connector', {}).get('state') == 'FAILED' \
            or any(t.get('state') == 'FAILED' for t in con.get('tasks', []))
        return {'state': 'FAILED' if failed else job.get('state'), 'flinkJob': job.get('state'),
                'connector': con.get('connector', {}).get('state'), 'tasks': [t.get('state') for t in con.get('tasks', [])]}

    def flink_stop(self, pid):
        spec = getattr(self, 'flink', {}).get(pid)
        if not spec:
            return
        if spec['job']:
            self.http('%s/jobs/%s?mode=cancel' % (self.args.flink_url, spec['job']), 'PATCH', ok=(200, 202, 404))
        self.http('%s/connectors/%s' % (self.args.connect_url, pid), 'DELETE', ok=(200, 204, 404))

    # ---------- fixture ----------
    def engine_mongo_uri(self, database):
        if self.args.engine_mongo_uri:
            return self.args.engine_mongo_uri.format(database=database)
        rs = self.mongo('const c=rs.conf();print("%s"+JSON.stringify({set:c._id,hosts:c.members.map(m=>m.host)}));' % MARK)
        return 'mongodb://%s/%s?replicaSet=%s' % (','.join(rs['hosts']), database, rs['set'])

    def seed(self, db):
        f = FIXTURES[self.args.fixture]
        program = 'const D=db.getSiblingDB(%s),C=%d,O=%d,shape=%s;' % (json.dumps(db), f['customers'], f['orders'], json.dumps(self.args.fixture))
        program += r'''
if (D.getCollectionNames().length) throw Error('source database already exists');
function flush(n,b){ if(b.length){ D.getCollection(n).insertMany(b,{ordered:false}); b.length=0; } }
const NAMES=['Customer','Kunde','Cliente','Zoe Saldana',"O'Brien"], TIERS=['gold','silver','bronze'];
let b=[];
for (let c=1;c<=C;c++){ b.push({_id:c,CUSTOMER_ID:c,NAME:NAMES[c%5]+' '+c,TIER:TIERS[c%3],CREATED:new Date(Date.UTC(2020,0,1)+c*60000)}); if(b.length>=10000) flush('BENCH_CUSTOMERS',b); }
flush('BENCH_CUSTOMERS',b);
for (let o=1;o<=O;o++){ const cust = shape==='tierb' && o%25===0 ? C+1000+o : (o%C)+1;
  b.push({_id:o,ORDER_ID:o,CUSTOMER_ID:cust,STATUS:'open',ORDER_TS:new Date(Date.UTC(2026,0,1)+o*1000)}); if(b.length>=10000) flush('BENCH_ORDERS',b); }
flush('BENCH_ORDERS',b);
// PRICE is always a BSON double: mongosh stores a whole-number value such as 1 as an int32, which
// makes the column look integral to a schema sampler and lets a typed step truncate 6286.75 to 6286.
for (let o=1;o<=O;o++){ const n = shape==='tierb' ? (o%10===0?0:(o%4)+1) : 2+(o%10<3?1:0);
  for (let l=1;l<=n;l++){ b.push({_id:o+'-'+l,ORDER_ID:o,LINE_NO:l,SKU:'SKU-'+String((o*7+l)%50).padStart(3,'0'),QTY:l,PRICE:Double((o*3+l)/4)}); if(b.length>=10000) flush('BENCH_LINES',b); } }
flush('BENCH_LINES',b);
D.BENCH_LINES.createIndex({ORDER_ID:1});
'''
        program += 'print(%s+JSON.stringify(Object.fromEntries(%s.map(n=>[n,D.getCollection(n).countDocuments()]))));' % (json.dumps(MARK), json.dumps(TABLES))
        t0 = time.monotonic()
        counts = self.mongo(program, timeout=3600)
        self.write('seed.json', {'database': db, 'fixture': self.args.fixture, 'counts': counts, 'seconds': time.monotonic() - t0})
        return counts

    def tdb(self, database):
        """mongosh expression for a database on the target server (the source server by default)."""
        if self.args.target_mongo_uri:
            return 'new Mongo(%s).getDB(%s)' % (json.dumps(self.args.target_mongo_uri), json.dumps(database))
        return 'db.getSiblingDB(%s)' % json.dumps(database)

    def count(self, db, names=None, target=False):
        prog = 'const T=%s;print(%s+JSON.stringify(Object.fromEntries(T.getCollectionNames().filter(n=>!n.startsWith("system.")).map(n=>[n,T.getCollection(n).estimatedDocumentCount()]))));' % (self.tdb(db) if target else 'db.getSiblingDB(%s)' % json.dumps(db), json.dumps(MARK))
        return self.mongo(prog, timeout=120)

    def verify_sample(self, source, target, collection, rate):
        """Rebuild sampled order documents from the source and compare them with the target."""
        if self.mode == 'join':
            return self.verify_join_sample(source, target, collection, rate)
        prog = 'const S=db.getSiblingDB(%s),T=%s.getCollection(%s),rate=%f;' % (
            json.dumps(source), self.tdb(target), json.dumps(collection), rate)
        prog += r'''
let checked=0,bad=0,examples=[];
const sample=S.BENCH_ORDERS.aggregate([{$sample:{size:Math.max(200,Math.round(S.BENCH_ORDERS.estimatedDocumentCount()*rate))}}]).toArray();
for (const o of sample){ checked++;
  const d=T.findOne({ORDER_ID:o.ORDER_ID});
  const c=S.BENCH_CUSTOMERS.findOne({_id:o.CUSTOMER_ID});
  const ls=S.BENCH_LINES.find({ORDER_ID:o.ORDER_ID}).toArray().map(l=>l.LINE_NO+':'+l.QTY+':'+l.SKU).sort().join(',');
  let why=null;
  if(!d) why='absent';
  else if(d.STATUS!==o.STATUS||Number(d.CUSTOMER_ID)!==Number(o.CUSTOMER_ID)) why='root';
  else if(c ? (!d.customer||d.customer.NAME!==c.NAME) : (d.customer&&Object.keys(d.customer).length)) why='customer';
  else if(((d.lines||[]).map(l=>l.LINE_NO+':'+l.QTY+':'+l.SKU).sort().join(','))!==ls) why='lines';
  if(why){bad++; if(examples.length<5) examples.push({order:o.ORDER_ID,why});}
}
'''
        prog += 'print(%s+JSON.stringify({checked,bad,examples}));' % json.dumps(MARK)
        return self.mongo(prog, timeout=1800)

    def verify_join_sample(self, source, target, collection, rate):
        """Rebuild sampled wide rows (a line plus its order's columns) from the source and compare
        them with the target. Reasons: absent, line (a fact column differs), order (a dimension
        column differs)."""
        prog = 'const S=db.getSiblingDB(%s),T=%s.getCollection(%s),rate=%f;' % (
            json.dumps(source), self.tdb(target), json.dumps(collection), rate)
        prog += r'''
let checked=0,bad=0,examples=[];
const sample=S.BENCH_LINES.aggregate([{$sample:{size:Math.max(200,Math.round(S.BENCH_LINES.estimatedDocumentCount()*rate))}}]).toArray();
for (const l of sample){ checked++;
  const d=T.findOne({LINE_ID:l._id});
  const o=S.BENCH_ORDERS.findOne({ORDER_ID:l.ORDER_ID});
  let why=null;
  if(!d) why='absent';
  else if(Number(d.ORDER_ID)!==Number(l.ORDER_ID)||Number(d.LINE_NO)!==Number(l.LINE_NO)||d.SKU!==l.SKU||Number(d.QTY)!==Number(l.QTY)||Number(d.PRICE)!==Number(l.PRICE)) why='line';
  else if(!o||d.STATUS!==o.STATUS||Number(d.CUSTOMER_ID)!==Number(o.CUSTOMER_ID)) why='order';
  if(why){bad++; if(examples.length<5) examples.push({line:l._id,why});}
}
'''
        prog += 'print(%s+JSON.stringify({checked,bad,examples}));' % json.dumps(MARK)
        return self.mongo(prog, timeout=1800)

    def store_cost(self, phases, units):
        """Store commands a stretch of the run cost: for each sampled mongod, the opcounter (and
        transaction) delta from the first to the last sample taken in any of `phases`, and the
        total divided by `units` (source rows for a load, events sent for a CDC step). The
        harness's own polling (counts, probes) lands in the same counters; it is a few commands per
        poll interval. None without --driver-container, which is what runs the mongod sampler."""
        path = self.out / 'mongod-stats.jsonl'
        if not self.args.driver_container or not path.exists():
            return None
        rows = [json.loads(l) for l in path.read_text().splitlines() if l.strip()]
        rows = [r for r in rows if r.get('phase') in phases and 'error' not in r]
        if len(rows) < 2:
            return None
        first, last = rows[0], rows[-1]
        result = {'phases': list(phases), 'seconds': last['t'] - first['t'], 'units': units}
        for server in ('source', 'target'):
            if server not in first or server not in last:
                continue
            a, b = first[server], last[server]
            ops = {k: b['opcounters'][k] - a['opcounters'][k] for k in OPCOUNTERS}
            total = sum(ops.values())
            tx = {k: (b['transactions'].get(k) or 0) - (a['transactions'].get(k) or 0) for k in ('started', 'committed', 'aborted')}
            result[server] = {'opcounters': ops, 'total': total, 'perUnit': total / units if units else None,
                              'transactions': tx, 'transactionsPerUnit': tx['committed'] / units if units else None}
        return result

    # ---------- engine objects ----------
    def create_connections(self, prefix, source_db, target_db, source_mode):
        ids = {}
        for role, db in (('in', source_db), ('out', target_db)):
            ident = '%s_%s' % (prefix, role)
            uri = self.args.target_engine_mongo_uri.format(database=db) if role == 'out' and self.args.target_engine_mongo_uri \
                else self.engine_mongo_uri(db)
            cfg = {'isUri': True, 'uri': uri, 'database': db}
            if role == 'in' and source_mode == 'cdc':
                cfg.update({'preImage': True, 'enableFillingModifiedData': False})
            self.api('/api/sources', 'POST', {'id': ident, 'connector': 'mongodb', 'config': cfg,
                     'mode': source_mode if role == 'in' else None,
                     'tables': [{'type': 'literal', 'name': n} for n in TABLES] if role == 'in' else []}, ok=(201,))
            if role == 'in':
                self.api('/api/connections:discover-schema', 'POST', {'id': ident, 'connectorId': 'mongodb', 'settings': cfg})
            ids[role] = ident
        return ids

    def wait(self, pipeline, done, limit, sample_name):
        t0 = time.monotonic()
        self.phase = sample_name.replace('-samples', '')
        while time.monotonic() - t0 < limit:
            st = self.status(pipeline)
            if st.get('state') == 'FAILED':
                self.write(sample_name + '-failed.json', st)
                raise RuntimeError(pipeline + ' FAILED')
            value = done()
            self.log(sample_name + '.jsonl', {'t': time.monotonic() - t0, 'state': st.get('state'), 'progress': value[1]})
            if value[0]:
                return time.monotonic() - t0
            time.sleep(self.args.poll_seconds)
        raise TimeoutError(sample_name + ' did not finish in %ds' % limit)

    # ---------- scenarios ----------
    def plain(self, prefix, source_db, expected):
        target_db = prefix + '_plain_target'
        if self.args.engine == 'flink':
            pid = prefix + '_plain'
            self.flink_define(pid, 'plain.sql', source_db, target_db)
            return self.plain_run(pid, target_db, expected)
        ids = self.create_connections(prefix + '_plain', source_db, target_db, 'snapshot')
        pid = prefix + '_plain'
        self.api('/api/pipelines', 'POST', {'id': pid, 'sources': [ids['in']],
                 'settings': {'readMode': 'snapshot_only', 'parallelism': 1}, 'transforms': [],
                 'serve': {'from': '/.*/', 'sync': [{'id': 'sink', 'source': ids['out'], 'writeMode': 'upsert',
                                                     'execution': json.loads(self.args.sink_execution)}]}}, ok=(201,))
        return self.plain_run(pid, target_db, expected)

    def plain_run(self, pid, target_db, expected):
        t0 = time.monotonic()
        self.start(pid)
        try:
            def done():
                c = self.count(target_db, target=True)
                return all(c.get(n, 0) >= expected[n] for n in TABLES), c
            seconds = self.wait(pid, done, self.args.snapshot_timeout, 'plain-samples')
            total = time.monotonic() - t0
        finally:
            self.stop(pid)
        rows = sum(expected.values())
        result = {'scenario': 'plain', 'pipeline': pid, 'rows': rows, 'seconds': total, 'rowsPerSecond': rows / total,
                  'store': self.store_cost(['plain'], rows)}
        self.write('plain.json', result)
        return result

    def nest_pipeline(self, prefix, source_db):
        target_db = prefix + '_nest_target'
        if self.args.engine == 'flink':
            pid = prefix + '_nest'
            self.flink_define(pid, 'nest.sql', source_db, target_db)
            return pid, target_db
        ids = self.create_connections(prefix + '_nest', source_db, target_db, 'cdc')
        pid = prefix + '_nest'
        p = {'id': pid, 'sources': [ids['in']], 'settings': {'readMode': 'snapshot_and_cdc', 'parallelism': 1},
             'transforms': [{'id': 'order_doc', 'type': 'nest', 'execution': json.loads(self.args.nest_execution),
                             'from': {'o': 'BENCH_ORDERS', 'l': 'BENCH_LINES', 'c': 'BENCH_CUSTOMERS'},
                             'root': {'from': 'o', 'key': ['ORDER_ID'], 'embed': [
                                 {'from': 'l', 'on': {'ORDER_ID': 'ORDER_ID'}, 'as': 'array', 'path': 'lines', 'arrayKey': ['LINE_NO']},
                                 {'from': 'c', 'on': {'_id': 'CUSTOMER_ID'}, 'as': 'object', 'path': 'customer'}]}}],
             'serve': {'from': 'order_doc', 'sync': [{'id': 'sink', 'source': ids['out'], 'writeMode': 'upsert',
                                                      'execution': json.loads(self.args.sink_execution)}]}}
        self.write('nest-pipeline.json', p)
        self.api('/api/pipelines', 'POST', p, ok=(201,))
        return pid, target_db

    def snapshot(self, pid, source_db, target_db, expected):
        t0 = time.monotonic()
        self.start(pid)
        holder = {}

        def done():
            c = self.count(target_db, target=True)
            holder['c'] = c
            n = max(c.values()) if c else 0
            return n >= expected['BENCH_ORDERS'], c
        self.wait(pid, done, self.args.snapshot_timeout, 'snapshot-samples')
        count_seconds = time.monotonic() - t0
        collection = max(holder['c'], key=holder['c'].get)
        self.target_collection = collection
        # All roots present is not yet complete: an engine may upsert a root before its embeds.
        self.phase = 'snapshot-complete'
        complete_seconds = None
        while time.monotonic() - t0 < self.args.snapshot_timeout:
            c = self.completeness(target_db, collection)
            self.log('snapshot-complete-samples.jsonl', {'t': time.monotonic() - t0, **c})
            if c['complete'] >= expected['BENCH_ORDERS']:
                complete_seconds = time.monotonic() - t0
                break
            time.sleep(self.args.poll_seconds)
        if complete_seconds is None:
            raise TimeoutError('snapshot documents did not complete in %ds' % self.args.snapshot_timeout)
        self.phase = 'snapshot-verify'
        try:
            self.write('engine-status-after-snapshot.json', self.status(pid))
            if self.args.engine == 'tapstate':
                self.write('engine-pipeline-after-snapshot.json', self.api('/api/pipelines/%s' % pid, ok=(200, 404)))
        except Exception as e:
            self.write('engine-status-after-snapshot.json', {'error': str(e)})
        if self.args.engine == 'flink':
            # Flink's Mongo sink keys order_doc by _id only; the check looks up ORDER_ID, which at Tier B
            # (1M documents) is a full scan per sample and overruns the mongosh timeout. Index it first.
            t_idx = time.monotonic()
            self.mongo('%s.getCollection(%s).createIndex({ORDER_ID:1});print(%s+"{}");' % (
                self.tdb(target_db), json.dumps(collection), json.dumps(MARK)), timeout=1800)
            self.log('verify-attempts.jsonl', {'phase': 'snapshot-index', 'unix': time.time(), 'seconds': time.monotonic() - t_idx})
        v = self.verify_sample(source_db, target_db, collection, self.args.sample_rate)
        self.log('verify-attempts.jsonl', {'phase': 'snapshot', 'unix': time.time(), 'bad': v['bad'], 'checked': v['checked']})
        deadline = time.monotonic() + 300
        while v['bad'] and time.monotonic() < deadline:  # sink may still be settling the last batch
            time.sleep(5)
            v = self.verify_sample(source_db, target_db, collection, self.args.sample_rate)
            self.log('verify-attempts.jsonl', {'phase': 'snapshot', 'unix': time.time(), 'bad': v['bad'], 'checked': v['checked']})
        rows = sum(expected.values())
        self.snapshot_hash = self.doc_hash(target_db, collection)
        result = {'scenario': 'snapshot', 'pipeline': pid, 'rows': rows, 'orders': expected['BENCH_ORDERS'], 'documentHash': self.snapshot_hash,
                  'secondsToAllRoots': count_seconds, 'secondsToComplete': complete_seconds,
                  'secondsToVerified': time.monotonic() - t0,
                  'docsPerSecond': expected['BENCH_ORDERS'] / complete_seconds, 'inputRowsPerSecond': rows / complete_seconds,
                  'rootsDocsPerSecond': expected['BENCH_ORDERS'] / count_seconds,
                  'verify': v, 'passed': v['bad'] == 0,
                  'store': self.store_cost(['snapshot', 'snapshot-complete'], rows)}
        self.write('snapshot.json', result)
        return result

    def completeness(self, target_db, collection):
        """Count target documents that are complete: the number of embedded lines and the presence
        of the customer object match what the fixture's generation rules put in the source."""
        f = FIXTURES[self.args.fixture]
        if self.args.fixture == 'tierb':
            lines = {'$cond': [{'$eq': [{'$mod': ['$ORDER_ID', 10]}, 0]}, 0, {'$add': [{'$mod': ['$ORDER_ID', 4]}, 1]}]}
            has_customer = {'$ne': [{'$mod': ['$ORDER_ID', 25]}, 0]}
        else:
            lines = {'$add': [2, {'$cond': [{'$lt': [{'$mod': ['$ORDER_ID', 10]}, 3]}, 1, 0]}]}
            has_customer = True
        present = {'$gt': [{'$size': {'$objectToArray': {'$ifNull': ['$customer', {}]}}}, 0]}
        complete = {'$and': [{'$eq': [{'$size': {'$ifNull': ['$lines', []]}}, lines]}, {'$eq': [present, has_customer]}]}
        pipeline = [{'$group': {'_id': None, 'total': {'$sum': 1}, 'complete': {'$sum': {'$cond': [complete, 1, 0]}}}}]
        prog = 'const r=%s.getCollection(%s).aggregate(%s,{allowDiskUse:true}).toArray()[0]||{total:0,complete:0};print(%s+JSON.stringify({total:r.total,complete:r.complete,orders:%d}));' % (
            self.tdb(target_db), json.dumps(collection), json.dumps(pipeline), json.dumps(MARK), f['orders'])
        return self.mongo(prog, timeout=600)

    def doc_hash(self, target_db, collection):
        """SHA-256 over the target documents in ORDER_ID order, each reduced to the content both engines
        produce (root STATUS and CUSTOMER_ID, customer NAME and TIER, lines sorted by LINE_NO with QTY, SKU,
        PRICE), numbers normalised, so the same source state hashes the same whatever the engine."""
        prog = r'''
const crypto=require('crypto'), h=crypto.createHash('sha256'); let n=0;
const T=%s.getCollection(%s);
T.find({}).sort({ORDER_ID:1}).forEach(d=>{ n++;
  const c=d.customer&&Object.keys(d.customer).length?[String(d.customer.NAME),String(d.customer.TIER)]:null;
  const L=(d.lines||[]).map(l=>[Number(l.LINE_NO),Number(l.QTY),String(l.SKU),Number(l.PRICE)]).sort((a,b)=>a[0]-b[0]);
  h.update(JSON.stringify([Number(d.ORDER_ID),String(d.STATUS),Number(d.CUSTOMER_ID),c,L])+'\n'); });
print(%s+JSON.stringify({documents:n,sha256:h.digest('hex')}));''' % (self.tdb(target_db), json.dumps(collection), json.dumps(MARK))
        return self.mongo(prog, timeout=1800)

    def probe_lag(self, target_db):
        """Lag of both change paths into the probe document: the root (STATUS = 'p:<ms>') and an
        embedded line (line 1's PRICE = <ms>). Each source table has its own change stream, so one
        path can be current while the other is far behind; the lag is the larger of the two.
        For the join the probe row is line 1 of the probe order: PRICE is the fact path and STATUS
        the dimension path."""
        if self.mode == 'join':
            prog = ('const d=%s.getCollection(%s).findOne({LINE_ID:"%d-1"},{STATUS:1,PRICE:1});'
                    'print(%s+JSON.stringify({s:d&&d.STATUS,p:d&&d.PRICE!=null?Number(d.PRICE):null,now:Date.now()}));') % (
                self.tdb(target_db), json.dumps(self.target_collection), PROBE_ORDER, json.dumps(MARK))
            return self.lag_of(self.mongo(prog, timeout=60))
        prog = ('const d=%s.getCollection(%s).findOne({ORDER_ID:%d},{STATUS:1,lines:1});'
                'const l=((d&&d.lines)||[]).find(x=>Number(x.LINE_NO)===1);'
                'print(%s+JSON.stringify({s:d&&d.STATUS,p:l?Number(l.PRICE):null,now:Date.now()}));') % (
            self.tdb(target_db), json.dumps(self.target_collection), PROBE_ORDER, json.dumps(MARK))
        return self.lag_of(self.mongo(prog, timeout=60))

    def lag_of(self, r):
        s = r['s'] or ''
        root = (r['now'] - int(s[2:])) / 1000.0 if s.startswith('p:') else None
        line = (r['now'] - r['p']) / 1000.0 if r['p'] and r['p'] > 1e12 else None
        self.last_probe = {'rootLagSeconds': root, 'lineLagSeconds': line}
        return None if root is None or line is None else max(root, line)

    def cdc(self, pid, source_db, target_db, name='cdc'):
        f = FIXTURES[self.args.fixture]
        steps, ceiling = [], None
        rates = [int(x) for x in self.args.cdc_rates.split(',')]
        for rate in rates:
            driver = 'const S=db.getSiblingDB(%s),O=%d,C=%d,rate=%d,secs=%d,lf=%f,cf=%f,probe=%d,tierb=%s;' % (
                json.dumps(source_db), f['orders'], f['customers'], rate, self.args.cdc_step_seconds,
                self.args.line_fraction, self.args.customer_fraction, PROBE_ORDER, 'true' if self.args.fixture == 'tierb' else 'false')
            driver += r'''
function order(){ for(;;){ const o=1+Math.floor(Math.random()*O); if(o!==probe && (!tierb || o%10!==0)) return o; } }
const t0=Date.now(); let sent=0, seq=0, nextProbe=t0, perSec=[], secStart=t0, secSent=0;
while (Date.now()-t0 < secs*1000) {
  const tick=Date.now(), target=Math.floor((tick-t0)/1000*rate), n=Math.min(target-sent, Math.max(1,rate));
  if (n>0) {
    const L=[],R=[],K=[];
    for (let i=0;i<n;i++){ seq++; const x=Math.random();
      if (x<lf) L.push({updateOne:{filter:{_id:order()+'-1'},update:{$inc:{QTY:1}}}});
      else if (x<lf+cf) K.push({updateOne:{filter:{_id:1+Math.floor(Math.random()*C)},update:{$set:{NAME:'c'+seq}}}});
      else R.push({updateOne:{filter:{_id:order()},update:{$set:{STATUS:'u'+seq}}}}); }
    if (L.length) S.BENCH_LINES.bulkWrite(L,{ordered:false});
    if (R.length) S.BENCH_ORDERS.bulkWrite(R,{ordered:false});
    if (K.length) S.BENCH_CUSTOMERS.bulkWrite(K,{ordered:false});
    sent+=n; secSent+=n;
  }
  if (Date.now()>=nextProbe){ S.BENCH_ORDERS.updateOne({_id:probe},{$set:{STATUS:'p:'+Date.now()}}); S.BENCH_LINES.updateOne({_id:probe+'-1'},{$set:{PRICE:Date.now()}}); sent+=2; secSent+=2; nextProbe+=1000; }
  if (Date.now()-secStart>=1000){ perSec.push(secSent); secSent=0; secStart=Date.now(); }
  const wait=Math.max(0, t0+Math.floor((sent+1)*1000/rate)-Date.now()); if (wait>0) sleep(Math.min(wait,50));
}
'''
            driver += 'print(%s+JSON.stringify({sent,seconds:(Date.now()-t0)/1000,perSecond:perSec}));' % json.dumps(MARK)
            lags, result_box = [], {}

            def run_driver():
                result_box['r'] = self.mongo(driver, timeout=self.args.cdc_step_seconds + 600)
            th = threading.Thread(target=run_driver)
            t0 = time.monotonic()
            th.start()
            self.phase = '%s-%d' % (name, rate)
            while th.is_alive():
                lag = self.probe_lag(target_db)
                lags.append((time.monotonic() - t0, lag))
                self.log(name + '-samples.jsonl', {'rate': rate, 't': time.monotonic() - t0, 'lagSeconds': lag, **self.last_probe})
                st = self.status(pid)
                if st.get('state') == 'FAILED':
                    self.write(name + '-failed.json', st)
                    raise RuntimeError('pipeline FAILED during CDC')
                time.sleep(self.args.poll_seconds)
            th.join()
            drv = result_box['r']
            achieved = drv['sent'] / drv['seconds']
            # Lag must stay bounded: compare the last quarter of the step with the second quarter.
            span = drv['seconds']
            q2 = [l for t, l in lags if span * 0.25 <= t < span * 0.5 and l is not None]
            q4 = [l for t, l in lags if t >= span * 0.75 and l is not None]
            end_lag = q4[-1] if q4 else None
            growth = (sum(q4) / len(q4) - sum(q2) / len(q2)) / (span * 0.5) if q2 and q4 else None
            drain_t0 = time.monotonic()
            drained = None
            while time.monotonic() - drain_t0 < self.args.drain_timeout:
                # A fresh probe after the load stops tells when the backlog has cleared.
                self.mongo('const S=db.getSiblingDB(%s);S.BENCH_ORDERS.updateOne({_id:%d},{$set:{STATUS:"p:"+Date.now()}});S.BENCH_LINES.updateOne({_id:"%d-1"},{$set:{PRICE:Date.now()}});print(%s+"{}");' % (
                    json.dumps(source_db), PROBE_ORDER, PROBE_ORDER, json.dumps(MARK)), timeout=60)
                time.sleep(2)
                lag = self.probe_lag(target_db)
                if lag is not None and lag < 5:
                    drained = time.monotonic() - drain_t0
                    break
            held = (achieved >= 0.95 * rate and end_lag is not None and end_lag < self.args.max_lag
                    and growth is not None and growth < 0.05)
            step = {'rate': rate, 'achievedEventsPerSecond': achieved, 'sent': drv['sent'], 'seconds': drv['seconds'],
                    'endLagSeconds': end_lag, 'lagGrowthSecondsPerSecond': growth,
                    'maxLagSeconds': max([l for _, l in lags if l is not None], default=None),
                    'drainSeconds': drained, 'held': held,
                    'store': self.store_cost(['%s-%d' % (name, rate)], drv['sent'])}
            steps.append(step)
            self.write(name + '.json', {'scenario': name, 'pipeline': pid, 'steps': steps, 'sustainedCeiling': ceiling})
            if not held:
                failures = getattr(self, '_cdc_failures', 0) + 1; self._cdc_failures = failures
                if self.args.cdc_stop_after_failures and failures >= self.args.cdc_stop_after_failures:
                    break
            if held:
                ceiling = rate
                # One extra step when the last listed rate held (same pipeline, same run).
                extra = [int(x) for x in str(self.args.cdc_extra_if_held or '').split(',') if x.strip() and int(x)]
                nxt = next((x for x in extra if x not in rates), None)
                if rate == rates[-1] and nxt:
                    rates.append(nxt)
            elif not self.args.cdc_continue:
                break
        # The drain probe watches one key; a partitioned engine can still be settling other keys,
        # so re-check until the sample is clean (bounded like the snapshot settle) and record how long.
        self.phase = name + '-verify'
        settle_t0 = time.monotonic()
        v = self.verify_sample(source_db, target_db, self.target_collection, self.args.sample_rate)
        self.log('verify-attempts.jsonl', {'phase': name, 'unix': time.time(), 't': time.monotonic() - settle_t0, 'bad': v['bad'], 'checked': v['checked']})
        first_bad = v['bad']
        while v['bad'] and time.monotonic() - settle_t0 < 300:
            time.sleep(5)
            v = self.verify_sample(source_db, target_db, self.target_collection, self.args.sample_rate)
            self.log('verify-attempts.jsonl', {'phase': name, 'unix': time.time(), 't': time.monotonic() - settle_t0, 'bad': v['bad'], 'checked': v['checked']})
        v = {**v, 'firstCheckBad': first_bad, 'secondsToSettle': time.monotonic() - settle_t0,
             'documentHash': self.doc_hash(target_db, self.target_collection)}
        result = {'scenario': name, 'pipeline': pid, 'steps': steps, 'sustainedCeiling': ceiling,
                  'mix': {'lines': self.args.line_fraction, 'customers': self.args.customer_fraction,
                          'orders': round(1 - self.args.line_fraction - self.args.customer_fraction, 3)},
                  'verifyAfter': v, 'passed': v['bad'] == 0}
        self.write(name + '.json', result)
        return result

    def join_pipeline(self, prefix, source_db):
        target_db = prefix + '_join_target'
        ids = self.create_connections(prefix + '_join', source_db, target_db, 'cdc')
        pid = prefix + '_join'
        step = {'id': 'line_wide', 'type': 'join', 'engine': 'builtin',
                'from': {'l': 'BENCH_LINES', 'o': 'BENCH_ORDERS'}, 'sql': JOIN_SQL}
        if self.args.join_execution:
            step['execution'] = json.loads(self.args.join_execution)
        p = {'id': pid, 'sources': [ids['in']], 'settings': {'readMode': 'snapshot_and_cdc', 'parallelism': 1},
             'transforms': [step],
             'serve': {'from': 'line_wide', 'sync': [{'id': 'sink', 'source': ids['out'], 'writeMode': 'upsert',
                                                      'execution': json.loads(self.args.sink_execution)}]}}
        self.write('join-pipeline.json', p)
        self.api('/api/pipelines', 'POST', p, ok=(201,))
        return pid, target_db

    def join_snapshot(self, pid, source_db, target_db, expected):
        """Start -> one target row per source line, then -> every row carries its order's STATUS
        (the dimension side has arrived), then a sampled content check."""
        lines = expected['BENCH_LINES']
        t0 = time.monotonic()
        self.start(pid)
        holder = {}

        def done():
            c = self.count(target_db, target=True)
            holder['c'] = c
            return (max(c.values()) if c else 0) >= lines, c
        self.wait(pid, done, self.args.snapshot_timeout, 'join-samples')
        count_seconds = time.monotonic() - t0
        collection = max(holder['c'], key=holder['c'].get)
        self.target_collection = collection
        self.phase = 'join-complete'
        complete_seconds = None
        prog = ('const T=%s.getCollection(%s);print(%s+JSON.stringify({total:T.estimatedDocumentCount(),'
                'complete:T.countDocuments({STATUS:{$type:"string"},LINE_ID:{$exists:true}})}));') % (
            self.tdb(target_db), json.dumps(collection), json.dumps(MARK))
        while time.monotonic() - t0 < self.args.snapshot_timeout:
            c = self.mongo(prog, timeout=600)
            self.log('join-complete-samples.jsonl', {'t': time.monotonic() - t0, **c})
            if c['complete'] >= lines:
                complete_seconds = time.monotonic() - t0
                break
            time.sleep(self.args.poll_seconds)
        if complete_seconds is None:
            raise TimeoutError('join rows did not complete in %ds' % self.args.snapshot_timeout)
        self.phase = 'join-verify'
        try:
            self.write('engine-status-after-join.json', self.status(pid))
            self.write('engine-pipeline-after-join.json', self.api('/api/pipelines/%s' % pid, ok=(200, 404)))
        except Exception as e:
            self.write('engine-status-after-join.json', {'error': str(e)})
        v = self.verify_sample(source_db, target_db, collection, self.args.sample_rate)
        self.log('verify-attempts.jsonl', {'phase': 'join', 'unix': time.time(), 'bad': v['bad'], 'checked': v['checked']})
        deadline = time.monotonic() + 300
        while v['bad'] and time.monotonic() < deadline:
            time.sleep(5)
            v = self.verify_sample(source_db, target_db, collection, self.args.sample_rate)
            self.log('verify-attempts.jsonl', {'phase': 'join', 'unix': time.time(), 'bad': v['bad'], 'checked': v['checked']})
        rows = sum(expected.values())
        result = {'scenario': 'join', 'pipeline': pid, 'rows': rows, 'lines': lines,
                  'secondsToAllRows': count_seconds, 'secondsToComplete': complete_seconds,
                  'secondsToVerified': time.monotonic() - t0,
                  'wideRowsPerSecond': lines / complete_seconds, 'inputRowsPerSecond': rows / complete_seconds,
                  'verify': v, 'passed': v['bad'] == 0,
                  'store': self.store_cost(['join', 'join-complete'], rows)}
        self.write('join.json', result)
        return result

    def run(self):
        a = self.args
        scen = a.scenarios.split(',')
        unknown = set(scen) - {'plain', 'snapshot', 'cdc', 'join', 'join-cdc'}
        if unknown:
            raise SystemExit('unknown scenarios: %s' % ','.join(sorted(unknown)))
        if a.engine == 'flink' and {'join', 'join-cdc'} & set(scen):
            raise SystemExit('the join scenarios run on the tapstate engine only')
        prefix = 'nb_' + uuid.uuid4().hex[:10]
        meta = {'prefix': prefix, 'fixture': a.fixture, 'scenarios': scen, 'startedUnix': time.time(),
                'label': a.label, 'api': a.api, 'members': self.engine_info(),
                'stats': self.docker_stats(), 'args': {k: (re.sub(r'//([^:/@]+):[^/]*@', r'//\1:***@', v) if isinstance(v, str) else v) for k, v in vars(a).items() if k != 'password'}}
        self.write('meta.json', meta)
        self.start_sampler()
        source_db = a.source_db or prefix + '_source'
        expected = self.seed(source_db) if not a.source_db else self.count(source_db)
        summary = {'prefix': prefix, 'label': a.label, 'fixture': a.fixture, 'source': source_db, 'expected': expected}
        if 'plain' in scen:
            summary['plain'] = self.plain(prefix, source_db, expected)
        if 'snapshot' in scen or 'cdc' in scen:
            self.mode = 'nest'
            pid, target_db = self.nest_pipeline(prefix, source_db)
            try:
                summary['snapshot'] = self.snapshot(pid, source_db, target_db, expected)
                if 'plain' in summary:
                    summary['snapshotVsPlain'] = summary['snapshot']['secondsToComplete'] / summary['plain']['seconds']
                    summary['snapshotRootsVsPlain'] = summary['snapshot']['secondsToAllRoots'] / summary['plain']['seconds']
                if a.idle_seconds:
                    # Pipeline running after the snapshot with no source changes: the engine's
                    # standing cost, sampled like every other phase (docker and mongod stats).
                    self.phase = 'idle'
                    idle_t0 = time.time()
                    time.sleep(a.idle_seconds)
                    summary['idle'] = {'startUnix': idle_t0, 'endUnix': time.time()}
                if 'cdc' in scen:
                    summary['cdc'] = self.cdc(pid, source_db, target_db)
            finally:
                self.stop(pid)
        if 'join' in scen or 'join-cdc' in scen:
            # After a NEST CDC the source has moved on; the join's checks read the source as it is
            # now, so the order is harmless, but a join A/B is cleanest run on its own.
            self.mode = 'join'
            pid, target_db = self.join_pipeline(prefix, source_db)
            try:
                summary['join'] = self.join_snapshot(pid, source_db, target_db, expected)
                if 'plain' in summary:
                    summary['joinVsPlain'] = summary['join']['secondsToComplete'] / summary['plain']['seconds']
                    summary['joinRowsVsPlain'] = summary['join']['secondsToAllRows'] / summary['plain']['seconds']
                if 'join-cdc' in scen:
                    summary['joinCdc'] = self.cdc(pid, source_db, target_db, name='join-cdc')
            finally:
                self.stop(pid)
        self.sampling = False
        summary['finishedUnix'] = time.time()
        self.write('summary.json', summary)
        print(json.dumps(summary, indent=2, default=str))


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('--engine', choices=['tapstate', 'flink'], default='tapstate')
    p.add_argument('--api', help='Tapstate base URL, e.g. http://localhost:38081 (tapstate engine)')
    p.add_argument('--flink-url', default='http://127.0.0.1:8081')
    p.add_argument('--connect-url', default='http://127.0.0.1:8083')
    p.add_argument('--flink-container', default='nestbench-flink')
    p.add_argument('--flink-sql-dir', default=str(pathlib.Path(__file__).resolve().parent.parent / 'flink' / 'sql'))
    p.add_argument('--kafka-bootstrap', default='kafka:9092')
    p.add_argument('--debezium-mongo-uri', default='mongodb://nestbench-mongo:27017/?replicaSet=nbrs')
    p.add_argument('--flink-mongo-uri', default='mongodb://nestbench-mongo:27017/?replicaSet=nbrs')
    p.add_argument('--nest-execution', default='{"parallelism": 1}', help='Tapstate nest step execution (JSON)')
    p.add_argument('--join-execution', help='Tapstate join step execution (JSON); omitted from the step when unset')
    p.add_argument('--sink-execution', default='{"parallelism": 1}', help='Tapstate sink execution (JSON), plain and nest')
    p.add_argument('--debezium-config', default='{}', help='JSON object merged into the Debezium connector config')
    p.add_argument('--flink-set', action='append', default=[], help="key=value, emitted as SET 'key' = 'value' (repeatable)")
    p.add_argument('--plain-flink-set', action='append', default=[], help='like --flink-set, plain copy only')
    p.add_argument('--sink-options', default='{}', help='JSON object of extra MongoDB sink table options')
    p.add_argument('--credentials', help='JSON with username/password (written by tapstate/install.sh)')
    p.add_argument('--username')
    p.add_argument('--password')
    p.add_argument('--mongo-container', required=True)
    p.add_argument('--mongo-port', type=int, default=27017)
    p.add_argument('--driver-container', help='run every mongosh call in this container instead of the Mongo container')
    p.add_argument('--driver-mongo-uri', default='mongodb://nestbench-mongo:27017/?replicaSet=nbrs')
    p.add_argument('--target-mongo-uri', help='target server URI as the driver container reaches it; target-side reads go there')
    p.add_argument('--target-engine-mongo-uri', help='URI template ({database}) the Tapstate out connections use (separate target server)')
    p.add_argument('--state-cache-db', help="engine durable cache database (e.g. tapstate_cache): sample its top counts, the pipeline's write fence and claim")
    p.add_argument('--idle-seconds', type=int, default=0, help='keep the nest pipeline running this long after the snapshot, no load')
    p.add_argument('--engine-mongo-uri', help='URI template the engine uses, with {database}; default from rs.conf()')
    p.add_argument('--fixture', choices=sorted(FIXTURES), default='942')
    p.add_argument('--source-db', help='reuse an already seeded, unmutated source database')
    p.add_argument('--scenarios', default='plain,snapshot,cdc')
    p.add_argument('--label', default='')
    p.add_argument('--sample-rate', type=float, default=0.01)
    p.add_argument('--snapshot-timeout', type=int, default=4 * 3600)
    p.add_argument('--poll-seconds', type=float, default=5)
    p.add_argument('--cdc-rates', default='150,500,1000,1500')
    p.add_argument('--cdc-step-seconds', type=int, default=600)
    p.add_argument('--cdc-stop-after-failures', type=int, default=0, help='stop stepping after this many steps that did not hold (0 = never)')
    p.add_argument('--cdc-extra-if-held', default='', help='comma list of CDC rates; each is added as a further step only if the step before it held')
    p.add_argument('--cdc-continue', action='store_true', help='keep stepping after a rate fails to hold')
    p.add_argument('--line-fraction', type=float, default=0.8)
    p.add_argument('--customer-fraction', type=float, default=0.0)
    p.add_argument('--max-lag', type=float, default=10.0)
    p.add_argument('--drain-timeout', type=int, default=900)
    p.add_argument('--stats-interval', type=float, default=5.0, help='docker stats sampling period, seconds')
    p.add_argument('--output', required=True)
    Bench(p.parse_args()).run()


if __name__ == '__main__':
    main()
