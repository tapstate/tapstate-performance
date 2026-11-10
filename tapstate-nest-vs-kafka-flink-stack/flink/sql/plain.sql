-- Plain copy: the denominator. Each source collection is upserted unchanged into the target.
-- Placeholders: ${JOB}, ${MONGO_URI}, ${TARGET_DB} (plus those of sources.sql).
SET 'pipeline.name' = '${JOB}';

CREATE TABLE dst_orders (
  `_id` DOUBLE, ORDER_ID DOUBLE, CUSTOMER_ID DOUBLE, STATUS STRING, ORDER_TS BIGINT,
  PRIMARY KEY (`_id`) NOT ENFORCED
) WITH ('connector' = 'mongodb', 'uri' = '${MONGO_URI}', 'database' = '${TARGET_DB}', 'collection' = 'BENCH_ORDERS'${SINK_OPTIONS});
CREATE TABLE dst_lines (
  `_id` STRING, ORDER_ID DOUBLE, LINE_NO DOUBLE, SKU STRING, QTY DOUBLE, PRICE DOUBLE,
  PRIMARY KEY (`_id`) NOT ENFORCED
) WITH ('connector' = 'mongodb', 'uri' = '${MONGO_URI}', 'database' = '${TARGET_DB}', 'collection' = 'BENCH_LINES'${SINK_OPTIONS});
CREATE TABLE dst_customers (
  `_id` DOUBLE, CUSTOMER_ID DOUBLE, NAME STRING, TIER STRING, CREATED BIGINT,
  PRIMARY KEY (`_id`) NOT ENFORCED
) WITH ('connector' = 'mongodb', 'uri' = '${MONGO_URI}', 'database' = '${TARGET_DB}', 'collection' = 'BENCH_CUSTOMERS'${SINK_OPTIONS});

EXECUTE STATEMENT SET BEGIN
  INSERT INTO dst_orders SELECT * FROM src_orders;
  INSERT INTO dst_lines SELECT * FROM src_lines;
  INSERT INTO dst_customers SELECT * FROM src_customers;
END;
