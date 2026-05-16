#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
HARNESS="$ROOT/benchmarks/tier5_http/harness"
export PYTHONPATH="$HARNESS${PYTHONPATH:+:$PYTHONPATH}"
cd "$HARNESS"
python3 verify_http.py --all --profile ci
python3 exploit_http.py --profile pr
python3 bench_http.py static_small --profile ci
echo "verify-http: OK"
