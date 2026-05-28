#!/usr/bin/env bash
# Render li-httpd TOML → Caddy and start staging compose.
set -euo pipefail
LIS_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
STAGING_DIR="${LIS_ROOT}/deploy/staging"
PROFILE="${LI_HTTPD_PROFILE:-${LIS_ROOT}/profiles/httpd/majico-staging.toml}"
GEN="${STAGING_DIR}/generated"
export PYTHONPATH="${LIS_ROOT}/scripts${PYTHONPATH:+:$PYTHONPATH}"

mkdir -p "$GEN"
python3 "${LIS_ROOT}/scripts/httpd_render_caddy.py" "$PROFILE" -o "${GEN}/Caddyfile"

compose() {
  if docker compose version >/dev/null 2>&1; then
    docker compose "$@"
  else
    docker-compose "$@"
  fi
}

cd "$STAGING_DIR"
files=(-f docker-compose.yml)
if [[ "${LI_STAGING_WITH_SUPABASE:-0}" == "1" ]]; then
  files+=(-f docker-compose.supabase.yml)
fi
if [[ -f .env ]]; then
  compose "${files[@]}" --env-file .env up -d "$@"
else
  echo "staging-up: copy .env.example to .env first" >&2
  exit 1
fi
echo "staging-up: Caddyfile at ${GEN}/Caddyfile"
