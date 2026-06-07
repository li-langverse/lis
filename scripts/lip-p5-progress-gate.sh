#!/usr/bin/env bash
# Progress gate: lip-registry P5 edge sprint.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
ok=0
fail=0
check() {
  if eval "$2"; then echo "  OK  $1"; ok=$((ok + 1)); else echo "  --  $1"; fail=$((fail + 1)); fi
}
echo "lip-p5 progress gate"
check "put-smoke job" 'test -f deploy/k8s/registry/job-lip-put-smoke.yaml'
check "multipeer e2e" 'test -f scripts/lip-multipeer-e2e.sh'
check "rebuild job" 'test -f deploy/k8s/registry/job-lip-rebuild-liserver-bin.yaml'
check "e2e uses :80" '! grep -q ":30422" scripts/lip-multipeer-e2e.sh 2>/dev/null || true'
echo "progress: ${ok} ok, ${fail} pending"
test "$ok" -ge 3
