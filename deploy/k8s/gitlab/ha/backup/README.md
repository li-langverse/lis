# GitLab backup — hourly DB + daily full Omnibus

Automated backups for homelab GitLab CE (Omnibus) in namespace `gitlab`.

## Schedules

| CronJob | Schedule | What |
|---------|----------|------|
| `gitlab-backup-db-hourly` | `0 * * * *` (every hour UTC) | `pg_dump` of `gitlabhq_production` → gzip |
| `gitlab-backup-full-daily` | `0 3 * * *` (03:00 UTC daily) | `gitlab-backup create` (DB + repos) → copy to PVC |

## Retention (rotation)

All backups live on PVC **`gitlab-backup-storage`**, mount path **`/backups`**.

| Tier | Path | Keep | Promotion |
|------|------|------|-----------|
| Hourly DB | `/backups/hourly/gitlab-db-hourly-YYYYMMDD-HH.sql.gz` | **24** | — |
| Daily DB | `/backups/daily/gitlab-db-daily-YYYYMMDD.sql.gz` | **7** | Midnight UTC hourly → daily |
| Weekly DB | `/backups/weekly/gitlab-db-weekly-YYYY-Www.sql.gz` | **4** | Sunday midnight UTC daily → weekly |
| Full Omnibus | `/backups/full/gitlab-full-*.tar` | **7 daily + 4 weekly** | 03:00 UTC run tagged daily; Monday weekly |

Rotation is idempotent: `rotate-backups.sh` sorts by filename (timestamp embedded) and deletes oldest files beyond the keep count.

## Database source

**Production (current cluster):** Omnibus **embedded** PostgreSQL only � no `gitlab-postgresql` StatefulSet. Hourly CronJob sets `GITLAB_DB_TARGET=embedded` and dumps via `kubectl exec gitlab-0` + embedded `pg_dump` on socket `/var/opt/gitlab/postgresql`.

**HA phase 1 (optional):** Deploy `../external-postgresql.yaml`, point Omnibus at external DB, then set `GITLAB_DB_TARGET=external` (or `auto`) on the CronJob so dumps use `gitlab-postgresql.gitlab.svc.cluster.local` and `gitlab-postgresql-secret`.

## Deploy

```powershell
$env:KUBECONFIG = "$env:USERPROFILE\.kube\config-homelab"
.\ha\scripts\deploy-backup.ps1
```

Requires existing `gitlab-postgresql-secret` (created by `deploy-shared-db.ps1`). Password is never printed or committed.

## Manual test

```powershell
kubectl -n gitlab delete job gitlab-backup-db-test gitlab-backup-rotation-test --ignore-not-found
kubectl apply -f ha/backup/job-test-backup.yaml
kubectl -n gitlab wait --for=condition=complete job/gitlab-backup-db-test --timeout=600s
kubectl -n gitlab logs job/gitlab-backup-db-test
kubectl -n gitlab exec deploy/gitlab-backup-debug -- ls -lh /backups/hourly/  # optional
```

Or inspect from a one-off debug pod:

```bash
kubectl -n gitlab run gitlab-backup-debug --rm -it --restart=Never \
  --overrides='{"spec":{"nodeSelector":{"li-langverse.io/node-pool":"engine"},"containers":[{"name":"debug","image":"alpine:3.20","command":["sh","-c","ls -lhR /backups; sleep 3600"],"volumeMounts":[{"name":"b","mountPath":"/backups"}]}],"volumes":[{"name":"b","persistentVolumeClaim":{"claimName":"gitlab-backup-storage"}}]}}'
```

## Restore (quick reference)

**From hourly/daily SQL dump (external or embedded PG was source):**

```bash
gunzip -c gitlab-db-daily-YYYYMMDD.sql.gz | kubectl exec -i -n gitlab gitlab-postgresql-0 -- \
  psql -U gitlab -d gitlabhq_production
# Or Omnibus embedded:
gunzip -c dump.sql.gz | kubectl exec -i -n gitlab gitlab-0 -c gitlab -- \
  gitlab-ctl exec -T postgresql psql -U gitlab -d gitlabhq_production
```

**From full Omnibus tar:**

```bash
kubectl cp ./TIMESTAMP_gitlab_backup.tar gitlab/gitlab-0:/var/opt/gitlab/backups/
kubectl exec -n gitlab gitlab-0 -c gitlab -- gitlab-backup restore BACKUP=TIMESTAMP force=yes
```

## Files

| File | Purpose |
|------|---------|
| `pvc.yaml` | 30 Gi `gitlab-backup-storage` on `local-path` |
| `rbac.yaml` | SA + Role for `pods/exec` into `gitlab-0` |
| `configmap-scripts.yaml` | `backup-db.sh`, `backup-full.sh`, `rotate-backups.sh` |
| `cronjob-db-hourly.yaml` | Hourly DB CronJob |
| `cronjob-full-daily.yaml` | Daily full Omnibus CronJob |
| `job-test-backup.yaml` | Manual DB backup + rotation test jobs |
| `../scripts/deploy-backup.ps1` | Apply all manifests |
