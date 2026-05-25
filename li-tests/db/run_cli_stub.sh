#!/usr/bin/env bash
# Smoke: lis db CLI stub exits 0 and round-trips status (PH-DB-3).
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$ROOT"
chmod +x bin/lis

export LI_DATA_DIR="${TMPDIR:-/tmp}/lis-db-test-$$"
export LI_PROFILE=registry-min
trap 'rm -rf "$LI_DATA_DIR"' EXIT

./bin/lis db stop >/dev/null 2>&1 || true
./bin/lis db start
./bin/lis db status | grep -q 'running'
./bin/lis db migrate --to head
test -f "$LI_DATA_DIR/.lis-db-migrate-stub"
./bin/lis db stop
./bin/lis db status | grep -q 'stopped'
echo "lis db CLI stub: OK"
