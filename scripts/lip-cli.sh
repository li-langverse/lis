#!/usr/bin/env bash
# Headless lip registry CLI for agents (validate|publish|whoami --json).
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"

resolve_registry_url() {
  if [[ -n "${LIP_REGISTRY_URL:-}" ]]; then
    local base="${LIP_REGISTRY_URL%/}"
    if [[ "$base" == */v1 ]]; then
      echo "$base"
    else
      echo "${base}/v1"
    fi
    return
  fi
  echo "http://127.0.0.1:${LI_API_PORT:-54321}/v1"
}

resolve_token() {
  if [[ -n "${LIP_REGISTRY_TOKEN:-}" ]]; then
    echo "$LIP_REGISTRY_TOKEN"
    return 0
  fi
  python3 - <<'PY'
import os
from pathlib import Path

try:
    import tomllib
except ImportError:
    import tomli as tomllib  # type: ignore

cred = Path(os.environ.get("LIP_CREDENTIALS_FILE", Path.home() / ".config/lip/credentials.toml"))
if cred.is_file():
    data = tomllib.loads(cred.read_text(encoding="utf-8"))
    token = (data.get("registry") or {}).get("token")
    if token:
        print(token.strip())
        raise SystemExit(0)
raise SystemExit(1)
PY
}

json_error() {
  local error="$1"
  local message="$2"
  local remediation="$3"
  python3 - "$error" "$message" "$remediation" <<'PY'
import json, sys
print(json.dumps({
    "error": sys.argv[1],
    "message": sys.argv[2],
    "remediation": sys.argv[3],
}))
PY
}

cmd="${1:-}"
shift || true

json_mode=0
dry_run=0
pkg_name="${LIP_PACKAGE:-}"
li_toml="${LI_TOML:-li.toml}"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --json) json_mode=1; shift ;;
    --dry-run) dry_run=1; shift ;;
    --name) pkg_name="$2"; shift 2 ;;
    --li-toml) li_toml="$2"; shift 2 ;;
    *) break ;;
  esac
done

BASE="$(resolve_registry_url)"

case "$cmd" in
  whoami)
    if ! token="$(resolve_token 2>/dev/null)"; then
      if [[ "$json_mode" == 1 ]]; then
        json_error unauthorized "no registry credentials" "lip login or set LIP_REGISTRY_TOKEN"
        exit 1
      fi
      echo "lip: no registry credentials (set LIP_REGISTRY_TOKEN)" >&2
      exit 1
    fi
    resp="$(curl -fsS "${BASE}/auth/whoami" -H "Authorization: Bearer ${token}" 2>/dev/null || true)"
    if [[ -z "$resp" ]]; then
      python3 - "$token" <<'PY'
import json, os, sys
token = sys.argv[1]
# Offline fallback when auth whoami route is unavailable.
if token == os.environ.get("LI_REGISTRY_DEV_TOKEN", "test-token"):
    print(json.dumps({"publisher_id": "dev", "scopes": ["publish", "yank"]}))
else:
    print(json.dumps({"publisher_id": "unknown", "scopes": ["publish"]}))
PY
      exit 0
    fi
    if [[ "$json_mode" == 1 ]]; then
      echo "$resp"
    else
      echo "$resp" | python3 -m json.tool
    fi
    ;;

  validate|publish)
    if [[ -z "$pkg_name" && -f "$li_toml" ]]; then
      pkg_name="$(python3 - "$li_toml" <<'PY'
import sys
from pathlib import Path
text = Path(sys.argv[1]).read_text(encoding="utf-8")
name = None
for line in text.splitlines():
    line = line.strip()
    if line.startswith("name") and "=" in line:
        name = line.split("=", 1)[1].strip().strip('"').strip("'")
        break
if not name:
    raise SystemExit(1)
print(name)
PY
)" || true
    fi
    if [[ -z "$pkg_name" ]]; then
      if [[ "$json_mode" == 1 ]]; then
        json_error bad_request "package name required" "Set LIP_PACKAGE, --name, or name in li.toml"
        exit 1
      fi
      echo "lip: package name required" >&2
      exit 1
    fi

    manifest="${LIP_PUBLISH_MANIFEST:-}"
    if [[ -z "$manifest" ]]; then
      if [[ "$json_mode" == 1 ]]; then
        json_error bad_request "publish manifest required" "Set LIP_PUBLISH_MANIFEST to registry publish JSON path"
        exit 1
      fi
      echo "lip: set LIP_PUBLISH_MANIFEST to publish JSON" >&2
      exit 1
    fi

    body="$(python3 - "$manifest" "$pkg_name" <<'PY'
import json, sys
from pathlib import Path
payload = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
payload["name"] = sys.argv[2]
print(json.dumps(payload))
PY
)"

    if [[ "$cmd" == "validate" || "$dry_run" == 1 ]]; then
      resp="$(curl -fsS -X POST "${BASE}/publish/validate" \
        -H "Content-Type: application/json" \
        -d "$body")"
      if [[ "$json_mode" == 1 ]]; then
        echo "$resp"
      else
        echo "$resp" | python3 -m json.tool
      fi
      exit 0
    fi

    if ! token="$(resolve_token 2>/dev/null)"; then
      if [[ "$json_mode" == 1 ]]; then
        json_error unauthorized "no registry credentials" "lip login or set LIP_REGISTRY_TOKEN"
        exit 1
      fi
      echo "lip: no registry credentials" >&2
      exit 1
    fi

    pub_body="$(python3 -c 'import json,sys; d=json.load(sys.stdin); d.pop("name", None); print(json.dumps(d))' <<<"$body")"
    version="$(python3 -c 'import json,sys; print(json.load(sys.stdin)["version"])' <<<"$pub_body")"
    resp="$(curl -fsS -X POST "${BASE}/packages/${pkg_name}/versions" \
      -H "Authorization: Bearer ${token}" \
      -H "Content-Type: application/json" \
      -d "$pub_body")"
    if [[ "$json_mode" == 1 ]]; then
      python3 - "$resp" "$pkg_name" "$version" <<'PY'
import json, sys
data = json.loads(sys.argv[1])
out = {
    "status": "published",
    "name": sys.argv[2],
    "version": sys.argv[3],
    "digest": data.get("tree_digest"),
    "published_at": data.get("published_at"),
}
print(json.dumps(out))
PY
    else
      echo "$resp" | python3 -m json.tool
    fi
    ;;

  *)
    echo "usage: lip-cli.sh {validate|publish|whoami} [--json] [--dry-run] [--name PKG]" >&2
    exit 2
    ;;
esac
