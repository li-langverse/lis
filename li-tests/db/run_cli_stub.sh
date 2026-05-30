#!/usr/bin/env bash
# Smoke: lis db CLI with native lidb embed (PH-DB-3).
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$ROOT"
chmod +x bin/lis

export LI_DATA_DIR="${TMPDIR:-/tmp}/lis-db-test-$$"
export LI_PROFILE=registry-min
export LIDB_ROOT="${LIDB_ROOT:-$ROOT/../lidb}"
trap 'rm -rf "$LI_DATA_DIR"' EXIT

./bin/lis db stop >/dev/null 2>&1 || true

if [[ ! -f "$LIDB_ROOT/liorm/embed_engine.py" ]]; then
  echo "lis db CLI: SKIP (no lidb at LIDB_ROOT=$LIDB_ROOT)"
  exit 0
fi

./bin/lis db start
./bin/lis db status | grep -q 'state:.*running'
./bin/lis db status | grep -q 'lidb_link:.*native'
./bin/lis db migrate --to head
test -f "$LI_DATA_DIR/.lis-db-migrate-rev"
test -f "$LI_DATA_DIR/.lidb/catalog.heap"
./bin/lis db stop
./bin/lis db status | grep -q 'state:.*stopped'
echo "lis db CLI native embed: OK"
