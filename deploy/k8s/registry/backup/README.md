# lip registry backup (Li-native)

CronJob `lip-registry-backup` runs daily at 04:00 UTC.

## What is backed up

- `/data/.lidb/catalog.heap` — registry + auth metadata
- `/data/blobs/` — package artifact CAS

## Apply

```bash
kubectl apply -f deploy/k8s/registry/backup/pvc.yaml
kubectl apply -f deploy/k8s/registry/backup/cronjob.yaml
```

## Manual run

```bash
kubectl -n lip-registry create job --from=cronjob/lip-registry-backup lip-registry-backup-now
kubectl -n lip-registry logs -f job/lip-registry-backup-now
kubectl -n lip-registry exec deploy/lip-registry-bootstrap -- ls -lh /backups  # if shared mount
```

Backups land on PVC `lip-registry-backup` at `/backups/lip-registry-YYYYMMDD-HHMM.tar.gz`.

## Restore on engine

```bash
kubectl -n lip-registry cp ./lip-registry-….tar.gz lip-registry-bootstrap-…:/tmp/restore.tar.gz
kubectl -n lip-registry exec -it deploy/lip-registry-bootstrap -- bash -lc \
  'export LI_DATA_DIR=/data PYTHONPATH=/opt/lis && python3 /opt/lis/scripts/lidb_backup.py restore /tmp/restore.tar.gz --force'
```

See [docs/registry-setup-backup.md](../../../../docs/registry-setup-backup.md).
