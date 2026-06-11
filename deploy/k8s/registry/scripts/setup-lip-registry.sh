#!/usr/bin/env bash
# One-shot homelab setup: namespace, secrets, lidb-backed registry, static site, backups.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../../../.." && pwd)"
NS="${LIP_REGISTRY_NS:-lip-registry}"
KUBECTL="${KUBECTL:-kubectl}"

echo "==> lip registry setup (namespace=${NS})"

"$KUBECTL" apply -f "${ROOT}/deploy/k8s/registry/namespace.yaml"
"$KUBECTL" apply -f "${ROOT}/deploy/k8s/registry/configmap.yaml"
"$KUBECTL" apply -f "${ROOT}/deploy/k8s/registry/pvc.yaml" 2>/dev/null || true

if ! "$KUBECTL" -n "$NS" get secret lip-registry-secrets >/dev/null 2>&1; then
  echo "Create secret lip-registry-secrets (see secret.yaml.example) before production."
fi

"$KUBECTL" apply -f "${ROOT}/deploy/k8s/registry/deployment-bootstrap.yaml"
"$KUBECTL" apply -f "${ROOT}/deploy/k8s/registry/service.yaml"
bash "${ROOT}/deploy/k8s/registry/scripts/apply-lip-static-site.sh"
"$KUBECTL" apply -f "${ROOT}/deploy/k8s/registry/backup/" 2>/dev/null || true

echo "==> waiting for registry pod"
"$KUBECTL" -n "$NS" rollout status deployment/lip-registry-bootstrap --timeout=300s || true

cat <<EOF

lip registry applied.

Inside the registry pod (after git clone picks up lidb auth):
  export LI_DATA_DIR=/data LI_AUTH_BACKEND=lidb LI_REGISTRY_MOCK=0
  ./bin/lis db setup
  ./bin/lis db import-auth /data/auth-mock.json   # if migrating mock data

Backup:
  kubectl -n ${NS} create job --from=cronjob/lip-registry-backup lip-registry-backup-manual-\$(date +%s)

Health:
  kubectl -n ${NS} port-forward svc/lip-registry-api 54321:54321
  curl -sS http://127.0.0.1:54321/health
EOF
