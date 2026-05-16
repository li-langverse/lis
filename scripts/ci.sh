#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
chmod +x scripts/*.sh li-tests/*.sh 2>/dev/null || true
./scripts/check-infra.sh
./scripts/check-toml.sh
./li-tests/run_all.sh
./li-tests/run_security.sh
./li-tests/run_load.sh
echo "== lis CI OK =="
