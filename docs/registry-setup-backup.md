# lip registry — Li-native setup & backup

Everything durable lives under **`LI_DATA_DIR`** (default `/data` on homelab):

| Path | Contents |
|------|----------|
| `.lidb/catalog.heap` | lidb snapshot — registry metadata **and** auth (users, tokens, publishers) |
| `blobs/sha256/…` | Content-addressed package artifacts (CAS) |

No separate auth JSON in production. No S3 required for registry-min.

## First-time setup (local)

```bash
export LIDB_ROOT=/path/to/lidb          # build lidb_embed once: cmake --build build/smoke --target lidb_embed
export LI_DATA_DIR=~/.local/share/lis/data
export LI_JWT_SECRET=$(openssl rand -hex 32)
export LI_AUTH_BACKEND=lidb
export LI_REGISTRY_MOCK=0

./bin/lis db setup                      # migrate + auth schema
./bin/lis db start --foreground         # registry API on :54321
```

Sign up at `http://127.0.0.1:54321` is via `/v1/auth/signup` or the account UI when static site is deployed.

## Migrate from auth-mock.json

```bash
export LI_DATA_DIR=/data
./bin/lis db import-auth /data/auth-mock.json
export LI_AUTH_BACKEND=lidb
export LI_REGISTRY_MOCK=0
```

## Backup (Li-native)

```bash
export LI_DATA_DIR=/data
export LIP_BLOB_DIR=/data/blobs
./bin/lis db backup -o /backups/lip-registry-$(date -u +%Y%m%d-%H%M).tar.gz
```

Archive contains:

- `manifest.json` — format version, timestamps, SHA-256 per file
- `.lidb/catalog.heap`
- `blobs/` (if present)

## Restore

```bash
./bin/lis db stop
./bin/lis db restore /backups/lip-registry-….tar.gz --force
./bin/lis db start --foreground
```

## Homelab (engine node)

```bash
# From lis repo on a machine with kubectl + KUBECONFIG
bash deploy/k8s/registry/scripts/setup-lip-registry.sh
kubectl apply -f deploy/k8s/registry/backup/
```

Backup CronJob writes to PVC `lip-registry-backup` (mount `/backups`).

## Environment reference

| Variable | Purpose |
|----------|---------|
| `LI_DATA_DIR` | Root data directory |
| `LI_AUTH_BACKEND` | `auto` (default), `lidb`, or `mock` |
| `LI_REGISTRY_MOCK` | `1` = mock registry + usually mock auth |
| `LIP_BLOB_DIR` | Blob CAS root |
| `LI_JWT_SECRET` | Session JWT signing (required) |

## Schema migrations (lidb repo)

- `lidb/migrations/004_auth_tokens.sql` — users, api_tokens
- `lidb/migrations/005_registry_security.sql` — signup_tokens, device_codes, audit log

Embedded engine applies auth tables via `lis db migrate` → `ensure_auth_schema()` writing `catalog.heap`.
