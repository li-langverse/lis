#!/usr/bin/env bash
# PH-DB-3 integration smoke: registry-min profile on clean LI_DATA_DIR.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

LIDB_REPO="${LIDB_REPO:-$ROOT/../lidb}"
export LIDB_REPO
[[ -d "$LIDB_REPO/liorm" ]] || { echo "missing lidb at LIDB_REPO=$LIDB_REPO" >&2; exit 1; }

DATA_DIR="$(mktemp -d "${TMPDIR:-/tmp}/lis-db-smoke.XXXXXX")"
export LI_DATA_DIR="$DATA_DIR"
export LI_PROFILE=registry-min
trap 'rm -rf "$DATA_DIR"' EXIT

export PYTHONPATH="$ROOT${PYTHONPATH:+:$PYTHONPATH}"
if python3 -m pip --version >/dev/null 2>&1; then
  python3 -m pip install -e . -q
  LIS=(lis)
else
  LIS=(python3 -m lis.cli)
fi

echo "[lis db smoke] start"
"${LIS[@]}" db start --json
echo "[lis db smoke] status"
"${LIS[@]}" db status --json
echo "[lis db smoke] migrate (idempotent)"
"${LIS[@]}" db migrate
echo "[lis db smoke] stop"
"${LIS[@]}" db stop
echo "[lis db smoke] OK"
