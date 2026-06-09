# GitLab HA — homelab (engine K8s)

## Architecture

| Component | Phase 1 (live) | Phase 2 (planned) |
|-----------|----------------|-------------------|
| **Install** | Omnibus StatefulSet `gitlab-0` | GitLab Helm chart (cloud-native) |
| **PostgreSQL** | Shared `gitlab-postgresql-0` StatefulSet | + read replica optional |
| **Redis** | Shared `gitlab-redis` Deployment | Redis Sentinel |
| **Webservice** | Single Omnibus pod (Puma workers: 4) | Helm `webservice` minReplicas: 2 |
| **Gitaly / repos** | Omnibus PVC `gitlab-data` (50 Gi) | Helm Gitaly PVC |
| **Ingress** | li-httpd edge → NodePort **30481** | Same NodePort on Helm webservice |
| **SSH** | NodePort **30222** | Helm gitlab-shell NodePort |
| **Edition** | CE 17.11.x | CE (Geo/HA multi-node needs EE) |

### CE vs EE

- **CE**: External PostgreSQL + Redis, multiple webservice replicas via Helm chart, shared Gitaly, backups.
- **EE only**: Geo replication, advanced HA reference architectures with multiple Gitaly nodes in Praefect.

## Endpoints

| Service | DNS | Port |
|---------|-----|------|
| PostgreSQL | `gitlab-postgresql.gitlab.svc.cluster.local` | 5432 |
| Redis | `gitlab-redis.gitlab.svc.cluster.local` | 6379 |
| GitLab HTTP | `gitlab.gitlab.svc` NodePort | 30481 |
| GitLab SSH | NodePort | 30222 |

## Deploy shared database (done once)

```powershell
$env:KUBECONFIG = "$env:USERPROFILE\.kube\config-homelab"
.\ha\scripts\deploy-shared-db.ps1
```

Creates `gitlab-postgresql-secret` (password not printed), StatefulSet `gitlab-postgresql`, Deployment `gitlab-redis`, PDB `gitlab-omnibus`.

## Phase 1: Omnibus → external PostgreSQL/Redis

1. **Backup** (automatic in script):

```powershell
.\ha\scripts\migrate-omnibus-external-db.ps1
```

The script:

1. Runs `gitlab-backup create`
2. Patches `gitlab-secrets` / `omnibus.rb` for external DB + Redis
3. Restarts Omnibus pod
4. Runs `gitlab-backup restore` into external PostgreSQL

**Verified 2026-06-09**: 65 projects restored; `database.yml` host = `gitlab-postgresql.gitlab.svc.cluster.local`.

### Manual rollback

If restore fails, re-enable embedded DB in `omnibus.rb` (`postgresql['enable'] = true`, remove `gitlab_rails['db_host']`), restart pod, restore backup.

## Phase 2: Helm webservice replicas (2+)

Requires Omnibus scale-to-zero and ~5 Gi additional RAM on `engine`.

```powershell
.\ha\scripts\deploy-helm-ha.ps1
```

Then restore repositories into Gitaly (DB already in shared PostgreSQL):

```bash
# Copy backup tar from old PVC or create fresh backup before scale-down
kubectl exec -it deploy/gitlab-toolbox -n gitlab -- backup-utility --restore -t <timestamp> SKIP=db
```

## Backup PostgreSQL

```bash
kubectl exec -n gitlab gitlab-postgresql-0 -- pg_dump -U gitlab gitlabhq_production -Fc -f /tmp/gitlab.sql
kubectl cp gitlab/gitlab-postgresql-0:/tmp/gitlab.sql ./gitlab-$(date +%F).dump
```

Schedule via CronJob in Phase 2.

## Scale webservice (Helm)

```bash
helm upgrade gitlab gitlab/gitlab -n gitlab -f ha/values-ha.yaml \
  --set gitlab.webservice.minReplicas=3 \
  --set gitlab.webservice.maxReplicas=3
```

## Upgrade path

1. `gitlab-backup create` (Omnibus or toolbox)
2. `helm repo update && helm upgrade gitlab gitlab/gitlab -n gitlab -f ha/values-ha.yaml`
3. Watch `kubectl -n gitlab rollout status deploy/gitlab-webservice-default`

## Verification

```bash
kubectl -n gitlab get pods
curl -H 'Host: gitlab.lilangverse.xyz' http://127.0.0.1:30481/api/v4/version   # 401 without token is OK
kubectl -n gitlab delete pod -l app=webservice --field-selector='metadata.name!=gitlab-webservice-default-<keep-one>'  # fail-one test (Helm)
```

## Files

| Path | Purpose |
|------|---------|
| `ha/external-postgresql.yaml` | Shared PostgreSQL StatefulSet |
| `ha/external-redis.yaml` | Shared Redis |
| `ha/values-ha.yaml` | Helm CE HA values (2 webservice) |
| `ha/scripts/deploy-shared-db.ps1` | Bootstrap shared services |
| `ha/scripts/migrate-omnibus-external-db.ps1` | Omnibus external DB migration |
| `ha/scripts/deploy-helm-ha.ps1` | Helm install |
| `omnibus/pdb.yaml` | PDB for Omnibus pod |
| `omnibus/configmap.yaml` | Omnibus base config |
