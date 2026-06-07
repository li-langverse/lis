#!/usr/bin/env bash
# Completion gate: P5 requires put-smoke job manifest + e2e script using public URL.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
bash scripts/lip-p5-progress-gate.sh
grep -q 'lip.lilangverse.xyz' scripts/lip-multipeer-e2e.sh
grep -q 'job-lip-put-smoke' deploy/k8s/registry/README.md 2>/dev/null || \
  test -f deploy/k8s/registry/job-lip-put-smoke.yaml
echo "lip-p5 completion gate: PASS (cluster verify manual or job log in PR)"
