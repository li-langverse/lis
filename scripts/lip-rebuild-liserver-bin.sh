#!/usr/bin/env bash
# Build li-httpd on engine, rotate lip-liserver-bin secret, rollout liserver.
set -euo pipefail
KUBECONFIG="${KUBECONFIG:-$HOME/.kube/config-homelab}"
NS=lip-registry
JOB=lip-rebuild-liserver-bin
BIN_HOST=/var/lib/lip-registry/build/li-httpd

kubectl apply -f "$(dirname "$0")/../deploy/k8s/registry/job-lip-rebuild-liserver-bin.yaml"
kubectl -n "$NS" delete job "$JOB" --ignore-not-found
kubectl apply -f "$(dirname "$0")/../deploy/k8s/registry/job-lip-rebuild-liserver-bin.yaml"
kubectl -n "$NS" wait --for=condition=complete "job/$JOB" --timeout=900s
kubectl -n "$NS" logs "job/$JOB"

# Copy binary off engine hostPath via a short-lived pod
COPY_POD=lip-bin-copy-$RANDOM
kubectl -n "$NS" run "$COPY_POD" --restart=Never --image=ubuntu:24.04 --overrides="$(cat <<EOF
{
  "spec": {
    "nodeSelector": {"kubernetes.io/hostname": "engine"},
    "containers": [{
      "name": "copy",
      "image": "ubuntu:24.04",
      "command": ["sleep", "600"],
      "volumeMounts": [{"name": "bin", "mountPath": "/host-bin", "readOnly": true}]
    }],
    "volumes": [{"name": "bin", "hostPath": {"path": "/var/lib/lip-registry/build", "type": "Directory"}}]
  }
}
EOF
)"
kubectl -n "$NS" wait --for=condition=Ready "pod/$COPY_POD" --timeout=120s
TMP="$(mktemp)"
kubectl -n "$NS" cp "$COPY_POD:/host-bin/li-httpd" "$TMP"
kubectl -n "$NS" delete pod "$COPY_POD" --force --grace-period=0

kubectl -n "$NS" create secret generic lip-liserver-bin \
  --from-file=li-httpd="$TMP" \
  --dry-run=client -o yaml | kubectl apply -f -
rm -f "$TMP"

kubectl apply -f "$(dirname "$0")/../deploy/k8s/registry/deployment-lip-liserver.yaml"
kubectl -n "$NS" rollout restart deployment/lip-liserver
kubectl -n "$NS" rollout status deployment/lip-liserver --timeout=180s
curl -fsS -H "Host: lip.lilangverse.xyz" http://192.168.10.32/health
echo
echo "lip-rebuild-liserver-bin: done"
