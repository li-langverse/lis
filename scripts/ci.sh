#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
chmod +x scripts/*.sh li-tests/*.sh 2>/dev/null || true
./scripts/check-infra.sh
./scripts/check-toml.sh
./scripts/verify-http.sh
chmod +x ./li-tests/run_httpd_config.sh 2>/dev/null || true
./li-tests/run_httpd_config.sh
chmod +x ./li-tests/run_httpd_caddy.sh 2>/dev/null || true
./li-tests/run_httpd_caddy.sh
./li-tests/run_all.sh
chmod +x ./li-tests/db/run_cli_stub.sh 2>/dev/null || true
./li-tests/db/run_cli_stub.sh
chmod +x ./tests/registry-api.test 2>/dev/null || true
./tests/registry-api.test
chmod +x ./scripts/ensure-realtime-venv.sh ./tests/realtime-ws.test 2>/dev/null || true
./scripts/ensure-realtime-venv.sh
export LI_CHANGEFEED_NATIVE=0
export LI_REALTIME_WS_RECV_TIMEOUT=5.0
./tests/realtime-ws.test
./li-tests/run_security.sh
./li-tests/run_load.sh
echo "== lis CI OK =="
