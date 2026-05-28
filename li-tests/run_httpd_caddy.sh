#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PY="${ROOT}/scripts"
export PYTHONPATH="$PY${PYTHONPATH:+:$PYTHONPATH}"

echo "== httpd caddy render (fixtures) =="
python3 "$PY/httpd_render_caddy.py" "$ROOT/li-tests/config_desugar/good/agent_gateway.toml" >/dev/null
python3 "$PY/httpd_render_caddy.py" "$ROOT/profiles/httpd/majico-staging.toml" -o "$ROOT/deploy/staging/generated/Caddyfile.ci"
grep -q "reverse_proxy" "$ROOT/deploy/staging/generated/Caddyfile.ci"

echo "run_httpd_caddy: OK"
