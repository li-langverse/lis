#!/usr/bin/env bash
# Launch goal-directed agent for lip-registry-agent-first (wrapper for li-cursor-agents).
set -euo pipefail
WS="$(cd "$(dirname "$0")/../.." && pwd)"
AGENTS="$WS/li-cursor-agents"
GOAL="data/goal-directed-sprints/lip-registry-agent-first.md"
if [[ ! -d "$AGENTS" ]]; then
  echo "missing $AGENTS" >&2
  exit 1
fi
cd "$AGENTS"
exec ./scripts/goal-directed-loop.sh \
  --agent code_implementer \
  --workflow-repo lis \
  --cwd "../lis" \
  --goal-file "$GOAL" \
  --max "${1:-0}"
