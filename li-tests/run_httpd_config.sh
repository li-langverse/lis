#!/usr/bin/env bash
# M1 prep: easy TOML desugar, validate, routing cases (Python oracle until li-httpd ships).
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PY="${ROOT}/scripts"
export PYTHONPATH="$PY${PYTHONPATH:+:$PYTHONPATH}"

echo "== httpd config desugar (good) =="
for f in "$ROOT/li-tests/config_desugar/good"/*.toml; do
  python3 "$PY/httpd_config.py" "$f"
done

echo "== httpd config reject =="
for rej in "$ROOT/li-tests/config_desugar/reject"/*.toml; do
  name="$(basename "$rej")"
  if python3 "$PY/httpd_config.py" "$rej" 2>/dev/null; then
    echo "expected reject to fail: $name" >&2
    exit 1
  fi
  echo "$name: rejected OK"
done

echo "== routing cases =="
for cases in "$ROOT/li-tests/routing/cases"/*.toml; do
  python3 "$PY/httpd_match.py" "$ROOT/li-tests/httpd/fixtures/routing.toml" "$cases"
done

echo "run_httpd_config: OK"
