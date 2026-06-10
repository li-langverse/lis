#!/usr/bin/env bash
# Build lip-static-site ConfigMap from lis/site/ and apply lip-static stack.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../../../.." && pwd)"
NS="${LIP_REGISTRY_NS:-lip-registry}"

kubectl create configmap lip-static-site -n "$NS" \
  --from-file=index.html="${ROOT}/site/index.html" \
  --from-file=account.html="${ROOT}/site/account.html" \
  --from-file=app.js="${ROOT}/site/app.js" \
  --from-file=styles.css="${ROOT}/site/styles.css" \
  --dry-run=client -o yaml | kubectl apply -f -

kubectl apply -f "${ROOT}/deploy/k8s/registry/configmap-lip-static-nginx.yaml"
kubectl apply -f "${ROOT}/deploy/k8s/registry/deployment-lip-static.yaml"
kubectl apply -f "${ROOT}/deploy/k8s/registry/service-lip-static.yaml"
kubectl apply -f "${ROOT}/deploy/k8s/registry/ingress-lip-registry.yaml"

echo "lip-static applied in namespace ${NS}"
