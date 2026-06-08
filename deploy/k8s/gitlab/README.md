# gitlab.lilangverse.xyz on engine K8s

Self-hosted **GitLab CE** via the [official GitLab Helm chart](https://docs.gitlab.com/charts/), pinned to node **engine**, exposed at [gitlab.lilangverse.xyz](https://gitlab.lilangverse.xyz).

Mirrors patterns from `deploy/k8s/registry/` (engine `nodeSelector`, nginx `IngressClass`, `*.lilangverse.xyz` TLS secret naming).

## Relation to other GitLab installs

| Install | Namespace | Hostname | Manifests |
|---------|-----------|----------|-----------|
| **This scaffold** | `gitlab-lilangverse` | `gitlab.lilangverse.xyz` | `lis-work/deploy/k8s/gitlab/` (Helm) |
| Homelab Omnibus (live) | `gitlab` | `gitlab.d3bu7.com`, `gitlab.klaut.pro` | `homelab-k3s/k8s/gitlab/` via [beelink-cleanup](https://github.com/cap-jmk-launchpad/homelab-k3s) |
| klaut.pro VPS | Docker Compose | `gitlab-vps.klaut.pro` | `beelink-cleanup/deploy/cloud-pro-vps/` |

Do **not** apply both Helm (`gitlab-lilangverse`) and Omnibus (`gitlab`) for the same data without a migration plan — they compete for engine RAM and storage.

## Prerequisites

- `kubectl` pointed at the **homelab** cluster (not a dead local `127.0.0.1:6443` kubeconfig)
- `helm` v3
- Engine node label / hostname:

```bash
kubectl label node engine li-langverse.io/node-pool=engine
# Workloads use: nodeSelector.kubernetes.io/hostname: engine
```

- **nginx** `IngressClass` on the cluster (same expectation as `ingress-lip-registry.yaml`)
- DNS **A** record: `gitlab.lilangverse.xyz` → **`77.23.124.82`** (Fritz WAN / blackpearl edge)
- Fritz port forward **TCP 80 + 443** → ingress node (same as `lip.lilangverse.xyz`, `majico.d3bu7.com`)
- TLS secret `gitlab-lilangverse-tls` in namespace `gitlab-lilangverse` (cert-manager, manual, or upstream terminator)

Homelab kubeconfig example:

```powershell
$env:KUBECONFIG = "C:\Users\Julian\.kube\config-homelab"
kubectl get nodes
```

Verified cluster (2026-06-08): nodes `blackpearl` (control-plane), `engine` (worker, 32 CPU / ~64 Gi RAM — already heavily scheduled), `anch0r`, `deck`.

## Resource notes (engine)

GitLab CE needs **≥ 4 Gi RAM** for a minimal chart install; the live Omnibus pod on `engine` already uses a 50 Gi PVC and has seen liveness-probe restarts during long reconfigures.

Before install, check headroom:

```bash
kubectl describe node engine | grep -A5 'Allocated resources'
kubectl top node engine    # requires metrics-server
```

Tune `values.yaml` limits if scheduling fails. Disable `registry.enabled` to save ~512 Mi if you do not need the container registry.

## 1. Namespace

```bash
cd lis-work/deploy/k8s/gitlab
kubectl apply -f namespace.yaml
```

## 2. TLS (before or after Helm)

Create `gitlab-lilangverse-tls` once (example — adjust for your cert flow):

```bash
# cert-manager Certificate (when ClusterIssuer exists):
# kubectl apply -f certificate-gitlab-lilangverse.yaml

# Or copy an existing wildcard / host cert:
kubectl -n gitlab-lilangverse create secret tls gitlab-lilangverse-tls \
  --cert=fullchain.pem --key=privkey.pem
```

**WAN note:** `77.23.124.82` may terminate TLS upstream (Caddy / li-httpd on blackpearl) before nginx ingress on engine — match `global.hosts.https` and ingress TLS to your actual termination point.

## 3. Helm install

```bash
helm repo add gitlab https://charts.gitlab.io/
helm repo update

# Initial root password (store safely; chart prints on first install):
export GITLAB_ROOT_PASSWORD="$(openssl rand -base64 24 | tr -d '/+=' | head -c 20)"

helm upgrade --install gitlab gitlab/gitlab \
  --namespace gitlab-lilangverse \
  --timeout 600s \
  --set global.initialRootPassword.password="$GITLAB_ROOT_PASSWORD" \
  -f values.yaml
```

First boot can take **15–30 minutes**. Watch:

```bash
kubectl -n gitlab-lilangverse get pods -w
kubectl -n gitlab-lilangverse get ingress
```

## 4. Ingress

**Default:** Helm creates ingress from `global.ingress` in `values.yaml`.

**Alternative:** disable chart ingress (`global.ingress.enabled: false`) and apply the standalone manifest:

```bash
kubectl apply -f ingress-gitlab.yaml
```

Update `ingress-gitlab.yaml` `backend.service.name` if your release name differs from `gitlab` (run `kubectl -n gitlab-lilangverse get svc`).

## Verify

```bash
kubectl -n gitlab-lilangverse get pods,ingress,pvc
curl -fsS -o /dev/null -w '%{http_code}\n' https://gitlab.lilangverse.xyz/users/sign_in
```

Sign in as `root` with the password from `GITLAB_ROOT_PASSWORD` (or `kubectl get secret gitlab-gitlab-initial-root-password -o jsonpath='{.data.password}' | base64 -d`).

## SSH / git clone

GitLab Shell SSH is **not** configured in this minimal values file. For SSH remotes, add a `gitlab-shell` NodePort or LoadBalancer service and document the host key — or use HTTPS remotes only.

## Coexist with lip-registry

- Namespace **`gitlab-lilangverse`** is separate from **`lip-registry`**
- Same engine node; different PVCs and secrets
- Both use `*.lilangverse.xyz` DNS → `77.23.124.82`

## Uninstall

```bash
helm uninstall gitlab -n gitlab-lilangverse
# PVCs are retained by default — delete manually if reclaiming disk:
# kubectl -n gitlab-lilangverse delete pvc --all
```
