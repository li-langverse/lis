#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
pkgs=(li-bytes li-net li-rng li-prob li-crypto li-tls li-acme li-schema li-log li-http li-httpd li-math)
for p in "${pkgs[@]}"; do
  [[ -d "packages/$p" ]] || { echo "missing packages/$p"; exit 1; }
  [[ -f "packages/$p/li.toml" ]] || { echo "missing packages/$p/li.toml"; exit 1; }
done
for d in benchmarks/tier5_http/harness li-tests docs docs/packages; do
  [[ -d "$d" ]] || { echo "missing $d"; exit 1; }
done
[[ -f docs/plan.md ]] || { echo "missing docs/plan.md"; exit 1; }
[[ -f .github/workflows/ci.yml ]] || { echo "missing CI workflow"; exit 1; }
echo "check-infra: OK"
