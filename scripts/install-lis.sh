#!/usr/bin/env bash
# Install lis CLI wrapper to ~/.local/bin (sets LIS_ROOT to this repo).
set -euo pipefail
LIS_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
DEST="${LI_INSTALL_BIN:-$HOME/.local/bin}"
mkdir -p "$DEST"
cat >"${DEST}/lis" <<EOF
#!/usr/bin/env bash
export LIS_ROOT="${LIS_ROOT}"
exec "\${LIS_ROOT}/bin/lis" "\$@"
EOF
chmod +x "${DEST}/lis" "${LIS_ROOT}/bin/lis" "${LIS_ROOT}/scripts/staging-up.sh" 2>/dev/null || true
echo "installed lis -> ${DEST}/lis (LIS_ROOT=${LIS_ROOT})"
