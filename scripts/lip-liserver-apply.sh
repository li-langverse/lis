#!/usr/bin/env bash
# Apply liserver (li-httpd) edge for lip.lilangverse.xyz on the engine host.
# Replaces interim nginx/Caddy patch jobs — native Li HTTP only.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LIS_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
LI_HTTPD_ROOT="${LI_HTTPD_ROOT:-$(cd "${LIS_ROOT}/../li-httpd" 2>/dev/null && pwd || echo "")}"
EDGE_TOML="${LIP_LISERVER_TOML:-${LIS_ROOT}/deploy/edge/lip-registry.httpd.http-only.toml}"
RUNTIME_DIR="${LI_HTTPD_RUNTIME_DIR:-/run/li-httpd}"
RUNTIME_CONF="${RUNTIME_DIR}/lip-registry.runtime.conf"
HTTPD_BIN="${LI_HTTPD_BIN:-/usr/local/bin/li-httpd}"
INSTALL_SYSTEMD=0
STOP_NGINX=0
RENDER_ONLY=0

usage() {
  cat <<EOF
usage: lip-liserver-apply.sh [--http-only|--tls] [--install-systemd] [--stop-nginx] [--render-only]

  --http-only       Use deploy/edge/lip-registry.httpd.http-only.toml (default on homelab)
  --tls             Use deploy/edge/lip-registry.httpd.toml (ACME on :443 + :80)
  --install-systemd Write /etc/systemd/system/li-httpd-lip.service
  --stop-nginx      systemctl stop nginx before starting liserver (engine :80)
  --render-only     Flatten TOML only; do not start/reload
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --http-only) EDGE_TOML="${LIS_ROOT}/deploy/edge/lip-registry.httpd.http-only.toml"; shift ;;
    --tls) EDGE_TOML="${LIS_ROOT}/deploy/edge/lip-registry.httpd.toml"; shift ;;
    --install-systemd) INSTALL_SYSTEMD=1; shift ;;
    --stop-nginx) STOP_NGINX=1; shift ;;
    --render-only) RENDER_ONLY=1; shift ;;
    -h|--help) usage; exit 0 ;;
    *) echo "unknown arg: $1" >&2; exit 1 ;;
  esac
done

[[ -f "$EDGE_TOML" ]] || { echo "missing edge TOML: $EDGE_TOML" >&2; exit 1; }

if [[ -n "${LIP_REGISTRY_UPSTREAM:-}" ]]; then
  export LIP_REGISTRY_UPSTREAM
  tmp="$(mktemp)"
  sed "s|http://127.0.0.1:30422|${LIP_REGISTRY_UPSTREAM}|g" "$EDGE_TOML" >"$tmp"
  EDGE_TOML="$tmp"
fi

lis http validate "$EDGE_TOML"

FLATTEN="${LI_HTTPD_ROOT}/scripts/flatten-httpd-config.py"
[[ -f "$FLATTEN" ]] || FLATTEN="${LIS_ROOT}/scripts/flatten-httpd-config.py"
[[ -f "$FLATTEN" ]] || { echo "missing flatten-httpd-config.py (set LI_HTTPD_ROOT)" >&2; exit 1; }

mkdir -p "$RUNTIME_DIR" /var/lib/li-httpd/empty
export PYTHONPATH="${LI_HTTPD_ROOT}/scripts:${LIS_ROOT}/scripts${PYTHONPATH:+:$PYTHONPATH}"
python3 "$FLATTEN" "$EDGE_TOML" -o "$RUNTIME_CONF"
echo "liserver flatten: $RUNTIME_CONF ($(wc -l <"$RUNTIME_CONF") lines)"

if [[ "$RENDER_ONLY" -eq 1 ]]; then
  exit 0
fi

if [[ -x "${LI_HTTPD_ROOT}/build/li-httpd" ]]; then
  install -m 755 "${LI_HTTPD_ROOT}/build/li-httpd" "$HTTPD_BIN"
elif [[ ! -x "$HTTPD_BIN" ]]; then
  echo "missing li-httpd binary — build: (cd ${LI_HTTPD_ROOT:-../li-httpd} && ./scripts/build-li-httpd.sh)" >&2
  exit 1
fi

if [[ "$INSTALL_SYSTEMD" -eq 1 ]]; then
  cat >/etc/systemd/system/li-httpd-lip.service <<EOF
[Unit]
Description=liserver — lip.lilangverse.xyz (li-httpd)
After=network-online.target k3s.service
Wants=network-online.target

[Service]
Type=simple
Environment=LIS_ROOT=${LIS_ROOT}
Environment=LI_HTTPD_ROOT=${LI_HTTPD_ROOT}
Environment=LIP_LISERVER_TOML=${EDGE_TOML}
Environment=LIP_REGISTRY_UPSTREAM=${LIP_REGISTRY_UPSTREAM:-http://127.0.0.1:30422}
ExecStartPre=/bin/mkdir -p ${RUNTIME_DIR} /var/lib/li-httpd/empty
ExecStartPre=${LIS_ROOT}/scripts/lip-liserver-apply.sh --render-only
ExecStart=${HTTPD_BIN} ${RUNTIME_CONF}
Restart=on-failure
RestartSec=3

[Install]
WantedBy=multi-user.target
EOF
  systemctl daemon-reload
  systemctl enable li-httpd-lip.service
fi

if [[ "$STOP_NGINX" -eq 1 ]]; then
  systemctl stop nginx.service 2>/dev/null || systemctl stop nginx 2>/dev/null || true
  systemctl disable nginx.service 2>/dev/null || true
fi

if systemctl is-active --quiet li-httpd-lip.service 2>/dev/null; then
  systemctl restart li-httpd-lip.service
elif [[ -f /etc/systemd/system/li-httpd-lip.service ]]; then
  systemctl start li-httpd-lip.service
else
  echo "run foreground: ${HTTPD_BIN} ${RUNTIME_CONF}"
  exec "$HTTPD_BIN" "$RUNTIME_CONF"
fi

echo "lip-liserver-apply: done (native li-httpd for lip.lilangverse.xyz)"
