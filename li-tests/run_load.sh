#!/usr/bin/env bash
set -euo pipefail
cd "$(cd "$(dirname "$0")/.." && pwd)"
python3 benchmarks/tier5_http/harness/tests/test_bench_toml.py
echo "run_load: OK"
