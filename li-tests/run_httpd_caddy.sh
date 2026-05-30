#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PY="$ROOT/scripts"
FIXTURE="$ROOT/li-tests/httpd/fixtures/routing.toml"
OUT="$ROOT/li-tests/httpd/fixtures/generated-Caddyfile.ci"
mkdir -p "$(dirname "$OUT")"
python3 "$PY/httpd_render_caddy.py" "$FIXTURE" -o "$OUT"
echo "ok: $OUT"