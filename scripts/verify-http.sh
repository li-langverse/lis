#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
HARNESS="$ROOT/benchmarks/tier5_http/harness"
CSV="$ROOT/benchmarks/results/verify-http.csv"
python3 "$HARNESS/bench_http.py" --profile ci --no-bench --csv "$CSV"
python3 "$HARNESS/exploit_http.py" --profile pr
test -s "$CSV"
echo "verify-http: OK"
