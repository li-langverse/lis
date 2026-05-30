#!/usr/bin/env bash
# Create .venv-realtime with websockets for Realtime WS tests (PEP 668 safe).
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
VENV="${ROOT}/.venv-realtime"

realtime_venv_python() {
  local venv="$1"
  if [[ -x "${venv}/bin/python" ]]; then
    echo "${venv}/bin/python"
  elif [[ -x "${venv}/Scripts/python.exe" ]]; then
    echo "${venv}/Scripts/python.exe"
  else
    echo "${venv}/bin/python"
  fi
}

realtime_venv_pip() {
  local venv="$1"
  if [[ -x "${venv}/bin/pip" ]]; then
    echo "${venv}/bin/pip"
  elif [[ -x "${venv}/Scripts/pip.exe" ]]; then
    echo "${venv}/Scripts/pip.exe"
  else
    echo "${venv}/bin/pip"
  fi
}

PY="$(realtime_venv_python "$VENV")"
PIP="$(realtime_venv_pip "$VENV")"

if [[ -x "$PY" ]] && "$PY" -c "import websockets" 2>/dev/null; then
  if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    exit 0
  fi
  return 0
fi
if python3 -c "import websockets" 2>/dev/null; then
  echo "lis: websockets available on system python"
  if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    exit 0
  fi
  return 0
fi
if ! python3 -m venv "$VENV" 2>/dev/null; then
  rm -rf "$VENV"
  python3 -m pip install -q --user --break-system-packages websockets 2>/dev/null || python3 -m pip install -q --user websockets
  python3 -c "import websockets"
  echo "lis: websockets via user pip (venv unavailable)"
  if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    exit 0
  fi
  return 0
fi
PY="$(realtime_venv_python "$VENV")"
PIP="$(realtime_venv_pip "$VENV")"
"$PIP" install -q websockets
echo "lis: .venv-realtime ready (${VENV})"
