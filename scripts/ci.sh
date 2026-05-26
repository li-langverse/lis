#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
chmod +x scripts/*.sh li-tests/*.sh 2>/dev/null || true
./scripts/check-infra.sh
./scripts/check-toml.sh
./scripts/check-no-sqlite.sh
export PYTHONPATH="$ROOT${PYTHONPATH:+:$PYTHONPATH}"
if python3 -m pip --version >/dev/null 2>&1; then
  python3 -m pip install -e . -q
fi
if [[ -d "${LIDB_REPO:-$ROOT/../lidb}/liorm" ]] && command -v cmake >/dev/null; then
  export LIDB_REPO="${LIDB_REPO:-$ROOT/../lidb}"
  ./scripts/db-smoke.sh
else
  echo "ci: skip db-smoke (set LIDB_REPO + cmake for full PH-DB-3 gate)"
fi
./li-tests/run_all.sh
./li-tests/run_security.sh
./li-tests/run_load.sh
echo "== lis CI OK =="
