#!/usr/bin/env bash
# Progress gate for lip-registry-agent-first sprint (checks incremental deliverables).
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

ok=0
fail=0
check() {
  if eval "$2"; then
    echo "  OK  $1"
    ok=$((ok + 1))
  else
    echo "  --  $1"
    fail=$((fail + 1))
  fi
}

echo "lip-agent-first progress gate (lis)"

check "spec present" 'test -f docs/superpowers/specs/2026-06-08-lip-registry-agent-first-design.md'
check "handlers.py" 'test -f routes/registry/handlers.py'
check "capabilities route" 'grep -q agent/capabilities routes/registry/handlers.py 2>/dev/null || grep -q agent_capabilities routes/registry/'
check "validate route" 'grep -q publish/validate routes/registry/handlers.py 2>/dev/null || grep -q validate_publish routes/registry/'
check "lip-cli script" 'test -x scripts/lip-cli.sh || test -f scripts/lip-cli.sh'
check "mcp package" 'test -d mcp/lip-registry || test -f mcp/lip_registry_mcp/__main__.py'
check "mcp example" 'test -f .cursor/mcp.json.example || test -f docs/agent/mcp-lip-registry.example.json'
check "agent-first test" 'test -f tests/registry-agent-first.test'

echo "progress: ${ok} ok, ${fail} pending"
# Exit 0 if at least P1 started (capabilities in handlers)
if grep -q agent/capabilities routes/registry/handlers.py 2>/dev/null; then
  exit 0
fi
exit 1
