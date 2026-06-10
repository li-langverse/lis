# gitlab.lilangverse.xyz on engine K8s

## HA status (2026-06-09)

| Layer | Status |
|-------|--------|
| **Shared PostgreSQL** | `gitlab-postgresql.gitlab.svc:5432` (StatefulSet, 20 Gi) |
| **Shared Redis** | `gitlab-redis.gitlab.svc:6379` |
| **Omnibus webservice** | 1 pod (`gitlab-0`), external DB + Redis, 65 projects |
| **2+ webservice replicas** | Phase 2 — Helm chart (`ha/values-ha.yaml`, `ha/scripts/deploy-helm-ha.ps1`) |

See **[ha/README.md](ha/README.md)** for architecture, backup, and Helm migration.

## Recommended: existing Omnibus (live)

**Use the homelab Omnibus GitLab** already running in namespace `gitlab` (NodePort **30481**, pod on **engine**). Expose it at `gitlab.lilangverse.xyz` via **li-httpd** on blackpearl — no second install, no nginx Ingress required.

| Install | Namespace | Hostname(s) | Status |
|---------|-----------|-------------|--------|
| **Homelab Omnibus (use this)** | `gitlab` | `gitlab.klaut.pro`, `gitlab.d3bu7.com`, **`gitlab.lilangverse.xyz`** | **Live** on engine |
| Helm scaffold (below) | `gitlab-lilangverse` | `gitlab.lilangverse.xyz` | **Not deployed** — future option only |
| klaut.pro VPS | Docker Compose | `gitlab-vps.klaut.pro` | Separate VPS |

### Quick start (Omnibus + edge)

1. Edge route is in [beelink-cleanup/k8s/edge/homelab.httpd.toml](https://github.com/cap-jmk-launchpad/beelink-cleanup/blob/master/k8s/edge/homelab.httpd.toml) (`gitlab.lilangverse.xyz` → `proxy:gitlab` → `127.0.0.1:30481`).
2. Full guide: [beelink-cleanup/docs/gitlab-lilangverse-setup.md](https://github.com/cap-jmk-launchpad/beelink-cleanup/blob/master/docs/gitlab-lilangverse-setup.md).
3. From Windows:

```powershell
cd C:\Users\Julian\Documents\Programming\beelink-cleanup
.\scripts\deploy-gitlab-lilangverse-edge.ps1 -ApplyEdge
.\scripts\deploy-gitlab-lilangverse-edge.ps1 -ConfigureGitLabUrl   # after DNS
```

4. **DNS:** `A` record `gitlab.lilangverse.xyz` → **`77.23.124.82`** (Fritz WAN; same as `lip.lilangverse.xyz`).

### Why not Helm now?

| Blocker | Detail |
|---------|--------|
| Duplicate GitLab | Omnibus already uses 50 Gi PVC + 3–6 Gi RAM on engine |
| Engine overcommitted | 32 CPU / ~64 Gi node already heavily scheduled |
| No nginx Ingress | Homelab edge is **li-httpd** on blackpearl, not in-cluster Ingress |
| Data migration | Helm would be a greenfield install — not a hostname swap |

Deploy the Helm chart below only when you intend to **replace** Omnibus (export/import or fresh instance) and have engine headroom.

---

## Helm scaffold (future / greenfield)

Self-hosted **GitLab CE** via the [official GitLab Helm chart](https://docs.gitlab.com/charts/), pinned to node **engine**, namespace `gitlab-lilangverse`.

Mirrors patterns from `deploy/k8s/registry/` (engine `nodeSelector`, nginx `IngressClass`, `*.lilangverse.xyz` TLS secret naming).

## Prerequisites

- `kubectl` pointed at the **homelab** cluster (not a dead local `127.0.0.1:6443` kubeconfig)
- `helm` v3
- Engine node label / hostname:

```bash
kubectl label node engine li-langverse.io/node-pool=engine
# Workloads use: nodeSelector.li-langverse.io/node-pool: engine
```

- **nginx** `IngressClass` on the cluster (same expectation as `ingress-lip-registry.yaml`) — **not present on homelab today**; Omnibus path above avoids this
- DNS **A** record: `gitlab.lilangverse.xyz` → **`77.23.124.82`**
- Fritz port forward **TCP 80 + 443** → blackpearl `192.168.10.33`
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

**WAN note:** `77.23.124.82` terminates TLS at **li-httpd on blackpearl** for Omnibus; a Helm install would need either the same edge pattern (NodePort + li-httpd) or a working in-cluster Ingress.

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

GitLab Shell SSH is **not** configured in this minimal values file. For SSH remotes, add a `gitlab-shell` NodePort or LoadBalancer service and document the host key — or use HTTPS remotes only. The live Omnibus install exposes SSH on NodePort **30222**.

## Coexist with lip-registry

- Namespace **`gitlab-lilangverse`** is separate from **`lip-registry`**
- Same engine node; different PVCs and secrets
- Both use `*.lilangverse.xyz` DNS → `77.23.124.82`
- **Do not** run Helm GitLab alongside live Omnibus without reclaiming RAM and disk

## Uninstall

```bash
helm uninstall gitlab -n gitlab-lilangverse
# PVCs are retained by default — delete manually if reclaiming disk:
# kubectl -n gitlab-lilangverse delete pvc --all
```
