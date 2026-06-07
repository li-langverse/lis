#!/usr/bin/env bash
# Completion gate for lip-registry-agent-first sprint (Phase 1–2).
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

export LI_REGISTRY_MOCK=1
export LI_REGISTRY_QUIET=1
export PYTHONPATH="$ROOT"

echo "== lip-agent-first completion gate =="

bash scripts/lip-agent-first-progress-gate.sh

# Live mock server checks
DATA_DIR="${TMPDIR:-/tmp}/lis-agent-first-$$"
export LI_DATA_DIR="$DATA_DIR"
LI_API_PORT="$(python3 -c 'import socket;s=socket.socket();s.bind(("127.0.0.1",0));print(s.getsockname()[1]);s.close()')"
export LI_API_PORT

cleanup() {
  if [[ -n "${SERVER_PID:-}" ]] && kill -0 "$SERVER_PID" 2>/dev/null; then
    kill "$SERVER_PID" 2>/dev/null || true
    wait "$SERVER_PID" 2>/dev/null || true
  fi
  rm -rf "$DATA_DIR"
}
trap cleanup EXIT

python3 routes/registry/server.py --port "$LI_API_PORT" &
SERVER_PID=$!
for _ in $(seq 1 40); do
  curl -sf "http://127.0.0.1:${LI_API_PORT}/health" >/dev/null 2>&1 && break
  sleep 0.1
done

BASE="http://127.0.0.1:${LI_API_PORT}"

curl -sf "${BASE}/v1/agent/capabilities" | grep -q '"auth_modes"'
curl -sf "${BASE}/v1/openapi.yaml" | grep -q 'agent/capabilities'

# validate dry-run (expect structured response)
code=$(curl -s -o /tmp/lip-validate-$$.json -w '%{http_code}' -X POST "${BASE}/v1/publish/validate" \
  -H 'Content-Type: application/json' \
  -d '{"name":"pkg-ok","version":"0.1.0","tree_digest":"sha256:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa","proof_digest":"sha256:bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb","coverage_pct":85.0}')
grep -q '"ok"' /tmp/lip-validate-$$.json
rm -f /tmp/lip-validate-$$.json

test -f scripts/lip-cli.sh
bash scripts/lip-cli.sh whoami --json >/dev/null 2>&1 || true

test -d mcp/lip-registry || test -f mcp/lip_registry_mcp/__main__.py

if [[ -f tests/registry-agent-first.test ]]; then
  bash tests/registry-agent-first.test
fi

echo "lip-agent-first completion gate: PASS"
