-- Operator tuning chosen on the 942 fixture (see ../README.md, tuning log): mini-batch cuts the
-- retraction write amplification of the join + ARRAY_AGG plan and moved the CDC ceiling from
-- below 150/s to 300/s. Applied to the plain copy as well, so both scenarios use one config.
SET 'table.exec.mini-batch.enabled' = 'true';
SET 'table.exec.mini-batch.allow-latency' = '1s';
SET 'table.exec.mini-batch.size' = '1000';

-- Change streams of the three source collections, as written by the Debezium MongoDB source
-- with ExtractNewDocumentState and ValueToKey(_id): one upsert-kafka table per collection.
-- mongosh writes plain JS numbers as BSON doubles, so numeric fields arrive as JSON numbers that
-- may carry a fraction; they are read as DOUBLE and cast where an integer is meant.
-- Placeholders: nb_7d41cbd8e6_nest, nb_7d41cbd8e6_source, kafka:9092.
CREATE TABLE src_orders (
  `_id` DOUBLE, ORDER_ID DOUBLE, CUSTOMER_ID DOUBLE, STATUS STRING, ORDER_TS BIGINT,
  PRIMARY KEY (`_id`) NOT ENFORCED
) WITH ('connector' = 'upsert-kafka', 'topic' = 'nb_7d41cbd8e6_nest.nb_7d41cbd8e6_source.BENCH_ORDERS',
        'properties.bootstrap.servers' = 'kafka:9092', 'key.format' = 'json', 'value.format' = 'json');

CREATE TABLE src_lines (
  `_id` STRING, ORDER_ID DOUBLE, LINE_NO DOUBLE, SKU STRING, QTY DOUBLE, PRICE DOUBLE,
  PRIMARY KEY (`_id`) NOT ENFORCED
) WITH ('connector' = 'upsert-kafka', 'topic' = 'nb_7d41cbd8e6_nest.nb_7d41cbd8e6_source.BENCH_LINES',
        'properties.bootstrap.servers' = 'kafka:9092', 'key.format' = 'json', 'value.format' = 'json');

CREATE TABLE src_customers (
  `_id` DOUBLE, CUSTOMER_ID DOUBLE, NAME STRING, TIER STRING, CREATED BIGINT,
  PRIMARY KEY (`_id`) NOT ENFORCED
) WITH ('connector' = 'upsert-kafka', 'topic' = 'nb_7d41cbd8e6_nest.nb_7d41cbd8e6_source.BENCH_CUSTOMERS',
        'properties.bootstrap.servers' = 'kafka:9092', 'key.format' = 'json', 'value.format' = 'json');

-- The NEST order document, the same shape Tapstate's `nest` step builds:
--   root    BENCH_ORDERS keyed by ORDER_ID
--   lines   BENCH_LINES on ORDER_ID, as an array (one entry per LINE_NO)
--   customer BENCH_CUSTOMERS on _id = CUSTOMER_ID, as an object
-- Left joins keep orders without lines (lines absent/null) and orders whose customer does not
-- exist (customer null), matching what the harness's content check accepts for Tapstate.
-- ARRAY_AGG has no ORDER BY in Flink 1.20, so array order is not guaranteed; the content check
-- compares lines as a sorted set of LINE_NO:QTY:SKU, as it does for Tapstate.
-- Upserts into Mongo keyed by ORDER_ID (the connector writes it as _id).
-- Placeholders: nb_7d41cbd8e6_nest, mongodb://nestbench-mongo:27017/?replicaSet=nbrs, nb_7d41cbd8e6_nest_target (plus those of sources.sql).
SET 'pipeline.name' = 'nb_7d41cbd8e6_nest';

CREATE TABLE order_doc (
  ORDER_ID BIGINT, CUSTOMER_ID BIGINT, STATUS STRING, ORDER_TS BIGINT,
  customer ROW<CUSTOMER_ID BIGINT, NAME STRING, TIER STRING, CREATED BIGINT>,
  lines ARRAY<ROW<LINE_NO INT, SKU STRING, QTY INT, PRICE DOUBLE>>,
  PRIMARY KEY (ORDER_ID) NOT ENFORCED
) WITH ('connector' = 'mongodb', 'uri' = 'mongodb://nestbench-mongo:27017/?replicaSet=nbrs', 'database' = 'nb_7d41cbd8e6_nest_target', 'collection' = 'order_doc');

INSERT INTO order_doc
SELECT
  CAST(o.ORDER_ID AS BIGINT),
  CAST(o.CUSTOMER_ID AS BIGINT),
  o.STATUS,
  o.ORDER_TS,
  CASE WHEN c.`_id` IS NULL THEN CAST(NULL AS ROW<CUSTOMER_ID BIGINT, NAME STRING, TIER STRING, CREATED BIGINT>)
       ELSE ROW(CAST(c.CUSTOMER_ID AS BIGINT), c.NAME, c.TIER, c.CREATED) END,
  l.lines
FROM src_orders AS o
LEFT JOIN src_customers AS c ON CAST(o.CUSTOMER_ID AS BIGINT) = CAST(c.`_id` AS BIGINT)
LEFT JOIN (
  SELECT CAST(ORDER_ID AS BIGINT) AS ORDER_ID,
         ARRAY_AGG(ROW(CAST(LINE_NO AS INT), SKU, CAST(QTY AS INT), PRICE)) AS lines
  FROM src_lines
  GROUP BY CAST(ORDER_ID AS BIGINT)
) AS l ON CAST(o.ORDER_ID AS BIGINT) = l.ORDER_ID;
