#!/bin/sh
# build-image.sh BUILD
# Builds a Tapstate server image from public source revisions, tagged nestbench/tapstate:BUILD.
#   main    0a8fe300  tapstate main at the time of the benchmark (the baseline)
#   revamp  04a5ad4a  the NEST revamp stack: PR #1020 + #1026 (direct store) + #1032 (capture lease)
#                     + #1036 (read-side lease); used for the 34k runs
#   tierb   04a5ad4a merged with a39adf64 (PR #1026 head: closes a NEST state group at its bounds;
#                     fixes a snapshot-time heap exhaustion at 1M orders); used for the Tier B runs
# The build runs in containers (Maven + JDK 21, then docker build), so the host needs only git and Docker.
set -eu
BUILD=${1:?usage: build-image.sh main|revamp|tierb}
SRC=${SRC:-$HOME/nestbench/tapstate-$BUILD}
case "$BUILD" in
  main)   BASE=0a8fe300360676cd4ebd4da8e902ea607aebee81; MERGE= ;;
  revamp) BASE=04a5ad4acb55d207d58c10627038f873e2928c27; MERGE= ;;
  tierb)  BASE=04a5ad4acb55d207d58c10627038f873e2928c27; MERGE=a39adf64140c47e77b14ecdd25be868485000b97 ;;
  *) echo "unknown build $BUILD" >&2; exit 2 ;;
esac
if [ ! -d "$SRC/.git" ]; then
  git clone https://github.com/tapstate/tapstate "$SRC"
fi
cd "$SRC"
# The revamp commits live on pull-request and work branches; fetch them explicitly.
git fetch -q origin main refs/pull/1026/head ws/issue-1035-on-1026
git checkout -q --detach "$BASE"
if [ -n "$MERGE" ]; then
  git -c user.name=nestbench -c user.email=nestbench@localhost merge -q --no-edit "$MERGE"
fi
echo "building $BUILD at $(git rev-parse HEAD)"
rm -f app/target/app-*-boot.jar
docker run --rm -v "$PWD":/src -v nestbench-m2:/root/.m2 -w /src maven:3.9-eclipse-temurin-21 \
  mvn -q -B -pl app -am -DskipTests package
docker build -q -f deploy/docker/Dockerfile --target server \
  --build-arg TAPSTATE_REVISION="$(git rev-parse HEAD)" -t "nestbench/tapstate:$BUILD" .
docker image inspect --format '{{.Id}} {{index .Config.Labels "org.opencontainers.image.revision"}}' "nestbench/tapstate:$BUILD"
