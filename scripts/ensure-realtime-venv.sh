#!/usr/bin/env bash
# Create .venv-realtime with websockets for Realtime WS tests (PEP 668 safe).
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
VENV="${ROOT}/.venv-realtime"
if [[ -x "${VENV}/bin/python" ]] && "${VENV}/bin/python" -c "import websockets" 2>/dev/null; then
  exit 0
fi
python3 -m venv "$VENV"
"${VENV}/bin/pip" install -q websockets
echo "lis: .venv-realtime ready (${VENV})"
