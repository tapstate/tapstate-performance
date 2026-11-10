-- Operator tuning chosen on the 942 fixture (see the README, "Flink tuning"): mini-batch cuts the
-- retraction write amplification of the join + ARRAY_AGG plan and moved the CDC ceiling from
-- below 150/s to 300/s. Applied to the plain copy as well, so both scenarios use one config.
SET 'table.exec.mini-batch.enabled' = 'true';
SET 'table.exec.mini-batch.allow-latency' = '1s';
SET 'table.exec.mini-batch.size' = '1000';

-- Change streams of the three source collections, as written by the Debezium MongoDB source
-- with ExtractNewDocumentState and ValueToKey(_id): one upsert-kafka table per collection.
-- mongosh writes plain JS numbers as BSON doubles, so numeric fields arrive as JSON numbers that
-- may carry a fraction; they are read as DOUBLE and cast where an integer is meant.
-- Placeholders: ${TOPIC_PREFIX}, ${SOURCE_DB}, ${BOOTSTRAP}.
CREATE TABLE src_orders (
  `_id` DOUBLE, ORDER_ID DOUBLE, CUSTOMER_ID DOUBLE, STATUS STRING, ORDER_TS BIGINT,
  PRIMARY KEY (`_id`) NOT ENFORCED
) WITH ('connector' = 'upsert-kafka', 'topic' = '${TOPIC_PREFIX}.${SOURCE_DB}.BENCH_ORDERS',
        'properties.bootstrap.servers' = '${BOOTSTRAP}', 'key.format' = 'json', 'value.format' = 'json');

CREATE TABLE src_lines (
  `_id` STRING, ORDER_ID DOUBLE, LINE_NO DOUBLE, SKU STRING, QTY DOUBLE, PRICE DOUBLE,
  PRIMARY KEY (`_id`) NOT ENFORCED
) WITH ('connector' = 'upsert-kafka', 'topic' = '${TOPIC_PREFIX}.${SOURCE_DB}.BENCH_LINES',
        'properties.bootstrap.servers' = '${BOOTSTRAP}', 'key.format' = 'json', 'value.format' = 'json');

CREATE TABLE src_customers (
  `_id` DOUBLE, CUSTOMER_ID DOUBLE, NAME STRING, TIER STRING, CREATED BIGINT,
  PRIMARY KEY (`_id`) NOT ENFORCED
) WITH ('connector' = 'upsert-kafka', 'topic' = '${TOPIC_PREFIX}.${SOURCE_DB}.BENCH_CUSTOMERS',
        'properties.bootstrap.servers' = '${BOOTSTRAP}', 'key.format' = 'json', 'value.format' = 'json');
