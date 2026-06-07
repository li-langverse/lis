#!/usr/bin/env bash
# Multi-peer E2E on engine cluster: all traffic via liserver (:80), two peer seeders, parallel fetch.
set -euo pipefail

REGISTRY_HOST="${REGISTRY_HOST:-127.0.0.1}"
REGISTRY_PORT="${REGISTRY_PORT:-80}"
HOST_HDR="${LIP_REGISTRY_HOST:-lip.lilangverse.xyz}"
BASE="http://${REGISTRY_HOST}:${REGISTRY_PORT}/v1"
CURL=(curl -fsS --max-time 30 -H "Host: ${HOST_HDR}")

TOKEN="${LIP_REGISTRY_TOKEN:?set LIP_REGISTRY_TOKEN}"
PEER_A="${LIP_PEER_A_URL:-http://lip-peer-a.lip-registry.svc.cluster.local:8765/v1}"
PEER_B="${LIP_PEER_B_URL:-http://lip-peer-b.lip-registry.svc.cluster.local:8766/v1}"
PKG="${LIP_TEST_PKG:-multipeer-demo}"
VER="${LIP_TEST_VER:-0.1.$((RANDOM % 9000 + 1000))}"

echo "== multipeer-e2e: liserver ${REGISTRY_HOST}:${REGISTRY_PORT} Host=${HOST_HDR} =="

health="$("${CURL[@]}" "http://${REGISTRY_HOST}:${REGISTRY_PORT}/health")"
echo "health: $health"
echo "$health" | python3 -c "import json,sys; d=json.load(sys.stdin); assert d.get('service')=='lis-registry', d"

echo "edge: native li-httpd liserver on :${REGISTRY_PORT}"

payload="li-multipeer-artifact-${RANDOM}"
digest="sha256:$(printf '%s' "$payload" | sha256sum | awk '{print $1}')"
tree="$digest"
proof="sha256:$(printf '%s-proof' "$payload" | sha256sum | awk '{print $1}')"

echo "== PUT blob $digest (via liserver) =="
curl -fsS --max-time 30 -X PUT \
  -H "Authorization: Bearer ${TOKEN}" \
  -H "Content-Type: application/vnd.li.package+tar" \
  --data-binary "$payload" \
  "${BASE}/blobs/${digest}"

echo "== POST publish ${PKG}@${VER} =="
curl -fsS --max-time 30 -X POST \
  -H "Authorization: Bearer ${TOKEN}" \
  -H "Content-Type: application/json" \
  -d "{\"version\":\"${VER}\",\"tree_digest\":\"${tree}\",\"proof_digest\":\"${proof}\",\"coverage_pct\":88.0,\"artifact_digest\":\"${digest}\"}" \
  "${BASE}/packages/${PKG}/versions"

echo "== announce peers =="
for ep in "$PEER_A" "$PEER_B"; do
  python3 - "${BASE}" "$ep" "$digest" "$TOKEN" <<'PY'
import json, os, sys, urllib.request
base, endpoint, digest, token = sys.argv[1:5]
url = base.rstrip("/") + "/peers/announce"
body = {"endpoint": endpoint, "digests": [digest], "ttl_sec": 3600}
req = urllib.request.Request(
    url, data=json.dumps(body).encode(),
    headers={"Content-Type": "application/json", "Authorization": f"Bearer {token}"},
    method="POST",
)
urllib.request.urlopen(req, timeout=30)
print(f"announced {endpoint}")
PY
done

echo "== GET package sources (via liserver) =="
list_json="$("${CURL[@]}" "${BASE}/packages?limit=5")"
echo "liserver list: $(echo "$list_json" | python3 -c "import json,sys; d=json.load(sys.stdin); print(d.get('total', d))")"
pkg_json="$("${CURL[@]}" "${BASE}/packages/${PKG}/${VER}")"
echo "$pkg_json"
python3 - "$pkg_json" <<'PY'
import json, sys
d = json.loads(sys.argv[1])
sources = d.get("sources") or []
types = [s.get("type") for s in sources]
assert "origin" in types, sources
peers = [s for s in sources if s.get("type") == "peer"]
assert len(peers) >= 2, f"expected >=2 peers in sources, got {sources}"
print(f"sources ok: origin + {len(peers)} peers")
PY

echo "== GET /v1/peers?digest= =="
peers_json="$("${CURL[@]}" "${BASE}/peers?digest=${digest}")"
echo "$peers_json"
python3 - "$peers_json" <<'PY'
import json, sys
d = json.loads(sys.argv[1])
peers = d.get("peers") or []
assert len(peers) >= 2, peers
print(f"peer index ok: {len(peers)} peers")
PY

echo "== parallel fetch from origin + peers =="
export REGISTRY_HOST REGISTRY_PORT HOST_HDR BASE
python3 - "$pkg_json" "$payload" "$digest" <<'PY'
import hashlib, json, os, sys, urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed

pkg = json.loads(sys.argv[1])
want = sys.argv[2]
digest = sys.argv[3]
host = os.environ.get("REGISTRY_HOST", "127.0.0.1")
port = os.environ.get("REGISTRY_PORT", "80")
host_hdr = os.environ.get("HOST_HDR", "lip.lilangverse.xyz")
edge = f"http://{host}:{port}"
sources = pkg.get("sources") or []

def fetch(src: dict) -> bytes:
    url = src["url"]
    if src.get("type") == "origin" or url.startswith("/"):
        full = f"{edge}{url}" if url.startswith("/") else f"{edge}/v1/blobs/{digest.split(':', 1)[1]}"
        req = urllib.request.Request(full, headers={"Host": host_hdr})
    else:
        base = url.rstrip("/")
        full = base if "/blobs/" in base else f"{base}/blobs/{digest}"
        req = urllib.request.Request(full)
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read()

ok = 0
with ThreadPoolExecutor(max_workers=max(1, len(sources))) as ex:
    futs = {ex.submit(fetch, s): s for s in sources}
    for fut in as_completed(futs):
        src = futs[fut]
        data = fut.result()
        got = hashlib.sha256(data).hexdigest()
        exp = digest.split(":", 1)[1]
        assert data == want.encode(), (src, len(data))
        assert got == exp, (src, got)
        ok += 1
        print(f"fetch ok: {src.get('type')} {src.get('url')} ({len(data)} bytes)")

assert ok == len(sources), (ok, len(sources))
print(f"multipeer-e2e: parallel fetch ok from {ok} sources")
PY

echo "multipeer-e2e: PASS"
