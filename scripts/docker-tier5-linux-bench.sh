#!/usr/bin/env bash
# Build li-httpd on Linux and refresh benchmarks/results/latest.csv with lang=li rows.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
LIC="${LIC_ROOT:-$ROOT/../lic}"
IMAGE="${TIER5_DOCKER_IMAGE:-ubuntu:24.04}"

docker run --rm --platform linux/amd64 \
  -v "$ROOT:/lis" \
  -v "$LIC:/lic" \
  -w /lis \
  "$IMAGE" bash -lc '
set -euo pipefail
apt-get update -qq
DEBIAN_FRONTEND=noninteractive apt-get install -y -qq nginx wrk python3 git clang lld curl build-essential >/dev/null
if [[ ! -x /lic/build/compiler/lic/lic ]]; then
  cd /lic && ./scripts/build.sh
fi
export LI_REPO_ROOT=/lic LI_LINK_RUNTIME_FULL=1 CC=clang CXX=clang++
/lic/build/compiler/lic/lic build --allow-open-vc --no-lean-verify \
  /lic/packages/li-net-httpd/src/main.li -o /lic/build/li-httpd
export LI_HTTPD_BIN=/lic/build/li-httpd LIC_ROOT=/lic
export BENCH_HTTP_PROFILE=nightly BENCH_HTTP_ORACLES=nginx,li BENCH_HTTP_QUICK_SEC=8
./scripts/run-tier5-http-bench.sh
'
