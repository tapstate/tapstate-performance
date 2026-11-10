# Flink 1.20.2 with the Kafka and MongoDB SQL connectors, checksums pinned.
FROM flink:1.20.2-scala_2.12-java17@sha256:f0f0a1bcdad2b1b21246256b4c3754c527833930750a5189270aa639043a25c0
ARG MAVEN=https://repo1.maven.org/maven2/org/apache/flink
RUN set -eu; cd /opt/flink/lib; \
    wget -q $MAVEN/flink-sql-connector-kafka/3.4.0-1.20/flink-sql-connector-kafka-3.4.0-1.20.jar; \
    wget -q $MAVEN/flink-sql-connector-mongodb/2.0.0-1.20/flink-sql-connector-mongodb-2.0.0-1.20.jar; \
    echo "266330f8f26fec4957339b5ff31aa67b81c31462  flink-sql-connector-kafka-3.4.0-1.20.jar" | sha1sum -c -; \
    echo "74cc0ba81f3eff74061dfb8031b1db5888e831e0  flink-sql-connector-mongodb-2.0.0-1.20.jar" | sha1sum -c -; \
    mkdir -p /opt/flink/checkpoints && chown flink:flink /opt/flink/checkpoints
COPY session.sh /session.sh
RUN chmod 755 /session.sh
ENTRYPOINT ["/session.sh"]
