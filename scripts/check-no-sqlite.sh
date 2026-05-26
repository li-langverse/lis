#!/usr/bin/env bash
# PH-DB-3.1: lis must not depend on sqlite3 for db supervisor paths.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
if command -v sqlite3 >/dev/null 2>&1; then
  echo "note: sqlite3 on PATH is allowed; lis db must not invoke it"
fi
hits=()
while IFS= read -r line; do
  hits+=("$line")
done < <(rg -n 'sqlite3' lis/ profiles/ scripts/db-smoke.sh li-tests/test_db_supervisor.py 2>/dev/null || true)
if ((${#hits[@]})); then
  echo "sqlite3 references in lis db paths (forbidden):" >&2
  printf '%s\n' "${hits[@]}" >&2
  exit 1
fi
echo "check-no-sqlite: OK"
