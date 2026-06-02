#!/usr/bin/env bash
# Homelab edge: merge TOML → flatten (li-httpd scripts) → li-httpd dual :443/:80.
# Config/tooling lives under li/ (li-httpd + lis), not lic/.
set -euo pipefail

RENDER_ONLY=0
INSTALL_SYSTEMD=0
RELOAD=1

while [[ $# -gt 0 ]]; do
  case "$1" in
    --render-only) RENDER_ONLY=1; shift ;;
    --install-systemd) INSTALL_SYSTEMD=1; shift ;;
    --no-reload) RELOAD=0; shift ;;
    -h|--help)
      echo "usage: edge-lis-apply.sh [--render-only] [--install-systemd] [--no-reload]"
      exit 0
      ;;
    *) echo "unknown arg: $1" >&2; exit 1 ;;
  esac
done

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if [[ -f "${SCRIPT_DIR}/scripts/flatten-httpd-config.py" ]]; then
  LI_HTTPD_ROOT="${LI_HTTPD_ROOT:-${SCRIPT_DIR}}"
  LIS_ROOT="${LIS_ROOT:-$(cd "${SCRIPT_DIR}/../lis" 2>/dev/null && pwd || echo "${SCRIPT_DIR}")}"
else
  LIS_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
  LI_HTTPD_ROOT="${LI_HTTPD_ROOT:-$(cd "${LIS_ROOT}/../li-httpd" && pwd)}"
fi
BEELINK_ROOT="${BEELINK_ROOT:-$(cd "${LIS_ROOT}/../beelink-cleanup" 2>/dev/null && pwd || echo "/home/s4il0r/staging/beelink-cleanup")}"
EDGE_DIR="${BEELINK_ROOT}/k8s/edge"

LIC_ROOT="${LIC_ROOT:-$(cd "${LIS_ROOT}/../lic-pure-https" 2>/dev/null && pwd || cd "${LIS_ROOT}/../lic" && pwd)}"
MAJICO_HTTPD_TOML="${MAJICO_HTTPD_TOML:-/home/s4il0r/staging/majico.xyz/deploy/staging/edge/majico-staging.httpd.toml}"

FLATTEN="${LI_HTTPD_ROOT}/scripts/flatten-httpd-config.py"
SETUP_TLS="${LI_HTTPD_ROOT}/scripts/setup-tls-httpd.py"
GEN_HTTPS="${EDGE_DIR}/gen-https-overlay.py"
MERGE="${EDGE_DIR}/merge-httpd-config.py"
RUNTIME_DIR="/run/li-httpd"
MERGED="${RUNTIME_DIR}/homelab.httpd.toml"
MERGED_TLS="${RUNTIME_DIR}/homelab.https.httpd.toml"
RUNTIME="${RUNTIME_DIR}/homelab.runtime.conf"
TLS_CERT_DIR="/var/lib/li-httpd/tls/homelab"

[[ -f "${EDGE_DIR}/homelab.httpd.toml" ]] || { echo "missing ${EDGE_DIR}/homelab.httpd.toml" >&2; exit 1; }
[[ -f "$FLATTEN" ]] || { echo "missing $FLATTEN (set LI_HTTPD_ROOT)" >&2; exit 1; }
[[ -x "${LI_HTTPD_ROOT}/build/li-httpd" ]] || [[ -x /usr/local/bin/li-httpd ]] || {
  echo "missing li-httpd binary — run: (cd ${LI_HTTPD_ROOT} && ./scripts/build-li-httpd.sh)" >&2
  exit 1
}

mkdir -p "$RUNTIME_DIR" /var/lib/li-httpd/empty "$TLS_CERT_DIR"

inputs=("${EDGE_DIR}/homelab.httpd.toml")
if [[ -f "$MAJICO_HTTPD_TOML" ]]; then
  inputs+=("$MAJICO_HTTPD_TOML")
else
  echo "warn: majico TOML not found at ${MAJICO_HTTPD_TOML}" >&2
fi

export LIS_ROOT LI_HTTPD_ROOT
python3 "$MERGE" "${inputs[@]}" -o "$MERGED" --validate

export PYTHONPATH="${LI_HTTPD_ROOT}/scripts${PYTHONPATH:+:$PYTHONPATH}"

python3 "$GEN_HTTPS" "$MERGED" -o "$MERGED_TLS"

if [[ -f "$SETUP_TLS" ]]; then
  python3 "$SETUP_TLS" "$MERGED_TLS" || echo "warn: setup-tls-httpd failed" >&2
fi

# Single runtime: HTTPS terminate on :443 + cleartext :80 (listen_port_http)
python3 "$FLATTEN" "$MERGED_TLS" -o "$RUNTIME"
if ! grep -q '^listen_port_http=' "$RUNTIME"; then
  if grep -q '^listen_port=443' "$RUNTIME"; then
    echo "listen_port_http=80" >>"$RUNTIME"
  fi
fi
echo "flatten edge: $RUNTIME ($(wc -l <"$RUNTIME") lines)"

if [[ "$RENDER_ONLY" -eq 1 ]]; then
  exit 0
fi

HTTPD_BIN="/usr/local/bin/li-httpd"
if [[ -x "${LI_HTTPD_ROOT}/build/li-httpd" ]]; then
  install -m 755 "${LI_HTTPD_ROOT}/build/li-httpd" "$HTTPD_BIN"
fi

if [[ "$INSTALL_SYSTEMD" -eq 1 ]]; then
  cat >/etc/systemd/system/li-httpd-homelab.service <<EOF
[Unit]
Description=li-httpd homelab edge (Li, dual :80/:443)
After=network-online.target k3s.service
Wants=network-online.target

[Service]
Type=simple
Environment=LI_HTTPD_ROOT=${LI_HTTPD_ROOT}
Environment=MAJICO_HTTPD_TOML=${MAJICO_HTTPD_TOML}
ExecStartPre=/bin/mkdir -p /run/li-httpd /var/lib/li-httpd/empty
ExecStartPre=/bin/bash -c 'LI_HTTPD_ROOT=${LI_HTTPD_ROOT} LIS_ROOT=${LIS_ROOT} BEELINK_ROOT=${BEELINK_ROOT} MAJICO_HTTPD_TOML=${MAJICO_HTTPD_TOML} ${SCRIPT_DIR}/edge-lis-apply.sh --render-only'
ExecStart=${HTTPD_BIN} ${RUNTIME}
User=root
Group=root
Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF
  systemctl daemon-reload
  systemctl disable --now li-httpd-homelab-tls.service 2>/dev/null || true
  systemctl disable --now caddy.service 2>/dev/null || true
  systemctl enable li-httpd-homelab.service
fi

if [[ "$RELOAD" -eq 1 ]]; then
  if systemctl is-active --quiet caddy.service 2>/dev/null; then
    systemctl stop caddy.service || true
  fi
  if [[ -f /etc/systemd/system/li-httpd-homelab.service ]]; then
    systemctl restart li-httpd-homelab.service
  else
    echo "run: sudo bash ${SCRIPT_DIR}/edge-lis-apply.sh --install-systemd" >&2
    exit 1
  fi
fi

echo "edge-lis-apply: done (native li-httpd :443 TLS + :80)"
