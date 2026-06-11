# Auth REST routes (MVP)

Email+password signup/login and API token management. Wired into the registry listener at `/v1/auth/*`.

| Method | Path | Auth | Handler |
|--------|------|------|---------|
| `POST` | `/v1/auth/signup` | — | Create user + publisher |
| `POST` | `/v1/auth/login` | — | Session JWT |
| `POST` | `/v1/auth/tokens` | Session bearer | Create `lip_…` API token |
| `GET` | `/v1/auth/tokens` | Session bearer | List tokens |
| `DELETE` | `/v1/auth/tokens/{id}` | Session bearer | Revoke token |
| `GET` | `/v1/auth/whoami` | Session bearer | Current user + publisher |
| `POST` | `/v1/auth/device/start` | — | Device login: `device_code`, `user_code`, `verification_uri` |
| `POST` | `/v1/auth/device/poll` | — | Poll `device_code` until `token` returned |
| `POST` | `/v1/auth/device/approve` | Session bearer | Approve shell login by `user_code` |
| `POST` | `/v1/auth/signup-tokens` | Session bearer | Mint gated signup invite |

Phase 1 TOTP/WebAuthn spec: [docs/auth-2fa-webauthn.md](../../docs/auth-2fa-webauthn.md).

## Run

```bash
export LI_DATA_DIR="${LI_DATA_DIR:-./.li-data}"
export LI_JWT_SECRET="${LI_JWT_SECRET:-dev-change-me}"
export LI_API_PORT=54321
export LI_REGISTRY_MOCK=1
python3 routes/registry/server.py
```

Optional dev publish bypass:

```bash
export LI_REGISTRY_DEV_TOKEN=test-token
```

## Smoke test

```bash
export LI_JWT_SECRET=dev-test-secret
export LI_DATA_DIR="$(mktemp -d)"
export LI_REGISTRY_MOCK=1
export LI_API_PORT=54321
python3 routes/auth/test_auth_smoke.py
```

Or use `lip/scripts/lip-login.sh` after starting the server.

## Storage (Li-native)

| Backend | Env | Path |
|---------|-----|------|
| **lidb** (production) | `LI_AUTH_BACKEND=lidb` or `auto` + catalog exists | `LI_DATA_DIR/.lidb/catalog.heap` |
| **mock** (offline dev) | `LI_AUTH_BACKEND=mock` or `LI_REGISTRY_MOCK=1` | `LI_DATA_DIR/auth-mock.json` |

Setup:

```bash
./bin/lis db setup                    # ensure auth tables in catalog.heap
./bin/lis db import-auth auth-mock.json   # optional migration from JSON
```

Schema: `lidb/migrations/004_auth_tokens.sql`, `005_registry_security.sql`.

Backup: `./bin/lis db backup -o lip-registry.tar.gz` (catalog + blobs). See [docs/registry-setup-backup.md](../../docs/registry-setup-backup.md).

## Registry integration

`routes/auth/verify.py` resolves bearer tokens for `liorm_mock.py` publish/yank. Valid sources:

1. `LI_REGISTRY_DEV_TOKEN` (dev only)
2. API tokens created via `POST /v1/auth/tokens`
