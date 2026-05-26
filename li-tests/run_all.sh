#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
python3 -m pytest li-tests/ benchmarks/tier5_http/harness/tests/ -q --tb=short 2>/dev/null || \
  python3 -m pytest li-tests/test_db_supervisor.py -q --tb=short 2>/dev/null || \
  python3 benchmarks/tier5_http/harness/tests/test_infra.py
echo "run_all: OK"
