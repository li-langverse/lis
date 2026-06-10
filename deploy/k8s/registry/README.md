# lip-registry on engine K8s

Li-native package registry (`lis db start` + registry REST) and **liserver** (li-httpd) edge for [lip.lilangverse.xyz](https://lip.lilangverse.xyz).

**Edge:** use **liserver** (native `li-httpd`) on engine `:80`. Do **not** use Caddy/nginx patch jobs — those bypass liserver and are removed from this tree.

Mirrors patterns from `li-cursor-agents/deploy/k8s/engine/` (engine nodeSelector, `ghcr-li-langverse` pull secret, always-on worker loop).

## liserver (li-httpd) — preferred edge

```bash
# Validate + flatten profile
lis http validate deploy/edge/lip-registry.httpd.http-only.toml
lis http flatten deploy/edge/lip-registry.httpd.http-only.toml -o /run/li-httpd/lip-registry.runtime.conf

# On engine host (systemd, replaces nginx on :80)
LIP_REGISTRY_UPSTREAM=http://127.0.0.1:30422 \
  ./scripts/lip-liserver-apply.sh --http-only --stop-nginx --install-systemd

# Or via lis CLI
LIP_REGISTRY_UPSTREAM=http://127.0.0.1:30422 lis http apply-lip --http-only --stop-nginx --install-systemd
```

Build `li-httpd` first: `(cd ../lic && ./scripts/build.sh && ./scripts/build-li-httpd.sh)`.

On engine cluster (rebuild secret from lic-ci job):

```bash
kubectl apply -f deploy/k8s/registry/job-lip-rebuild-liserver-bin.yaml
kubectl -n lip-registry wait --for=condition=complete job/lip-rebuild-liserver-bin --timeout=900s
kubectl apply -f deploy/k8s/registry/job-lip-rotate-liserver-bin.yaml
kubectl -n lip-registry wait --for=condition=complete job/lip-rotate-liserver-bin --timeout=120s
kubectl -n lip-registry rollout restart deployment/lip-liserver
kubectl -n lip-registry rollout status deployment/lip-liserver --timeout=120s
```

**PUT smoke (liserver :80 only — no NodePort bypass):**

```bash
kubectl apply -f deploy/k8s/registry/job-lip-put-smoke.yaml
kubectl -n lip-registry wait --for=condition=complete job/lip-put-smoke --timeout=120s
kubectl -n lip-registry logs job/lip-put-smoke
```

**Multipeer E2E (publish + peer fetch via :80):**

```bash
kubectl apply -f deploy/k8s/registry/job-lip-multipeer-e2e.yaml
kubectl -n lip-registry wait --for=condition=complete job/lip-multipeer-e2e --timeout=600s
kubectl -n lip-registry logs job/lip-multipeer-e2e
```

**WAN note:** `77.23.124.82` currently terminates at upstream Caddy; engine liserver listens on `192.168.10.32:80`. Point upstream Caddy to engine `:80` once liserver is active.

## Prerequisites

- `kubectl` pointed at the **engine** cluster (not a dead local `127.0.0.1:6443` kubeconfig)
- Engine node label / hostname:

```bash
kubectl label node <engine-node-name> li-langverse.io/node-pool=engine
# Workers here use: nodeSelector.kubernetes.io/hostname: engine
```

- Image built and pushed (monorepo root with sibling `lidb/` + `lis/`):

```bash
docker build -f lis/docker/Dockerfile.supervisor -t lip-registry:latest .
docker tag lip-registry:latest ghcr.io/li-langverse/lis:registry-min
docker push ghcr.io/li-langverse/lis:registry-min
```

- `ghcr-li-langverse` imagePullSecret in namespace `lip-registry`
- DNS **A** record: `lip.lilangverse.xyz` → ingress/LB IP (e.g. `77.23.124.82`)

Homelab kubeconfig example:

```powershell
$env:KUBECONFIG = "C:\Users\Julian\.kube\config-homelab"
```

## Secrets (required before worker)

Create once in `lip-registry` (copy from `secret.yaml.example` when present, or):

```bash
kubectl -n lip-registry create secret generic lip-registry-secrets \
  --from-literal=LI_REGISTRY_DEV_TOKEN="$LI_REGISTRY_DEV_TOKEN" \
  --from-literal=LI_JWT_SECRET="$LI_JWT_SECRET" \
  --from-literal=GITLAB_TOKEN="$GITLAB_TOKEN" \
  --from-literal=GH_TOKEN="$GH_TOKEN" \
  --dry-run=client -o yaml | kubectl apply -f -
```

| Key | Used by |
|-----|---------|
| `LI_REGISTRY_DEV_TOKEN` | Registry publish + `toy-registry-smoke` |
| `LI_JWT_SECRET` | Auth routes (Phase 1) |
| `GITLAB_TOKEN` | Worker git clone from `gitlab.lilangverse.xyz` (primary) |
| `GH_TOKEN` | Transition fallback for git clone |

Do not commit real values. Rotate `LI_REGISTRY_DEV_TOKEN` before public launch.

## 1 TB SSD blob store (engine)

External SSD mounts at **`/var/lib/lip-registry`** on node `engine` (hostPath → pod `/data/blobs`).

```bash
kubectl apply -f job-lip-disk-detect.yaml   # inspect block devices
kubectl apply -f job-lip-ssd-mount-v2.yaml  # mount /dev/sdb1 if needed
kubectl -n lip-registry logs job/lip-ssd-mount-v2
```

Registry blob API (content-addressed):

| Method | Path | Auth |
|--------|------|------|
| `PUT` | `/v1/blobs/{sha256:…}` | bearer `publish` |
| `GET` | `/v1/blobs/{sha256:…}` | public |
| `POST` | `/v1/peers/announce` | optional (P2P seed hints) |

`lip publish --registry URL` uploads a tarball (`artifact_digest`) then posts metadata. Peers: `lip peer serve`.

## Apply — registry API (baseline)

When `namespace.yaml`, `deployment.yaml`, `service.yaml` exist in this directory:

```bash
cd lis/deploy/k8s/registry
kubectl apply -f namespace.yaml
kubectl apply -f pvc.yaml
kubectl apply -f configmap.yaml
kubectl apply -f secret.yaml          # from secret.yaml.example
kubectl apply -f deployment.yaml
kubectl apply -f service.yaml
kubectl -n lip-registry wait deployment/lip-registry --for=condition=Available --timeout=180s
```

## Apply — goal-directed platform worker

```bash
cd lis/deploy/k8s/registry
kubectl apply -f configmap-lip-platform-worker.yaml
kubectl apply -f deployment-lip-platform-worker.yaml
kubectl apply -f ingress-lip-registry.yaml
kubectl -n lip-registry rollout status deployment/lip-platform-worker --timeout=120s
```

The worker loop (see `configmap-lip-platform-worker.yaml` → `entrypoint.sh`):

1. `kubectl apply` ingress manifest (`/config/ingress-lip-registry.yaml`)
2. `lip/scripts/toy-registry-smoke.sh` against in-cluster `lip-registry-api:54321`
3. `lip/scripts/toy-git-install-smoke.sh` or `packages/lis-cli` git install fallback
4. Writes goal status to **`/data/status.json`** on PVC `lip-platform-worker-data`

### Verify

```bash
kubectl -n lip-registry logs -f deploy/lip-platform-worker --tail=80
kubectl -n lip-registry exec deploy/lip-platform-worker -- cat /data/status.json
kubectl -n lip-registry get ingress lip-registry
curl -fsS "https://lip.lilangverse.xyz/health"
curl -fsS "https://lip.lilangverse.xyz/v1/packages?limit=1"
```

Public **GET `/v1`** must return JSON (200 or 401), **not** an HTML `/login` redirect.

## Ingress routing (`ingress-lip-registry.yaml`)

| Path | Backend | Notes |
|------|---------|-------|
| `/v1` | `lip-registry-api:54321` | Public GET — **no** auth redirect |
| `/health` | `lip-registry-api:54321` | Health probe |
| `/account` | `lip-auth-api:54322` | Future auth UI |
| `/` | `lip-static:80` | Future landing/docs |

Router: forward WAN **80/443** to the **ingress controller node**, not port **54321**.

## ConfigMap env (worker)

| Variable | Default | Meaning |
|----------|---------|---------|
| `LIP_REGISTRY_PUBLIC_URL` | `https://lip.lilangverse.xyz/v1` | External smoke URL |
| `LIP_REPO_URL` | `https://gitlab.lilangverse.xyz/li-langverse/lip.git` | Clone for smokes |
| `LIS_REPO_URL` | `https://gitlab.lilangverse.xyz/li-langverse/lis.git` | Clone for smokes |
| `LIC_REPO_URL` | `https://gitlab.lilangverse.xyz/li-langverse/lic.git` | liserver rebuild + lic smokes |
| `LIS_CLI_GIT_URL` | same as `LIS_REPO_URL` | Git install test dep |
| `LI_PLATFORM_LOOP_SLEEP_SEC` | `300` | Loop interval |
All homelab cluster git clones use **GitLab primary** (GITLAB_TOKEN); GH_TOKEN is transition fallback only. See org rule gitlab-primary-github-mirror.

| `LI_PLATFORM_STATUS_FILE` | `/data/status.json` | Goal status output |

Goals checklist: ConfigMap key `goals-checklist.md`.

## Coexist with li-swarm goal workers

- Namespace **`lip-registry`** is separate from **`li-swarm`**
- Same engine node; different PVCs and secrets
- Worker uses `lip-registry-secrets`, not `li-agents-secrets`

## Image tags (GHCR primary)

Homelab pulls from **`ghcr.io/li-langverse/*`** — not GitLab registry, not local sideload. See [beelink-cleanup/docs/ghcr-image-strategy.md](https://github.com/cap-jmk-launchpad/beelink-cleanup/blob/master/docs/ghcr-image-strategy.md).

| Image | When |
|-------|------|
| `ghcr.io/li-langverse/lis:registry-min` | Default in `deployment-lip-platform-worker.yaml` |
| `lip-registry:latest` | Local build tag only (push to GHCR before deploy) |

**Build + push (blackpearl or dev host with `write:packages`):**

```bash
bash beelink-cleanup/scripts/build-push-lis-registry-min.sh
bash beelink-cleanup/scripts/check-ghcr-push.sh   # verify PAT first
```

**Verify pull secret:** `kubectl -n lip-registry get secret ghcr-li-langverse`

**Rotate pull secret** (after PAT with `read:packages`):

```bash
kubectl -n lip-registry create secret docker-registry ghcr-li-langverse \
  --docker-server=ghcr.io --docker-username=li-langverse --docker-password="$GH_TOKEN" \
  --dry-run=client -o yaml | kubectl apply -f -
kubectl -n lip-registry rollout restart deploy/lip-platform-worker
```

`imagePullPolicy: IfNotPresent` — kubelet pulls from GHCR once, then reuses cached layers on engine.

### Emergency sideload only (GHCR down)

Do **not** use as default — consumes ~533M+ on engine containerd.

1. `beelink-cleanup/scripts/import-lis-registry-min-to-engine.sh`
2. Or `kubectl apply -f job-import-lis-registry-min.yaml`

After GHCR tag exists: `beelink-cleanup/scripts/prune-engine-sideloaded-images.sh`

**Engine inventory job:** `kubectl apply -f job-engine-image-inventory.yaml && kubectl -n lip-registry logs job/engine-image-inventory`
