# lis

**li-httpd** â€” proved AI/agent HTTP gateway written in [Li](https://github.com/li-langverse/li).

**Live handbook:** https://li-langverse.github.io/lis/ Â· [docs/handbook.md](docs/handbook.md)

Secure-by-design TOML config, optional leak censorship (schema-driven setup), streaming SSE, rate limits, and cross-platform CI.

## Status

**Infrastructure only** â€” packages, harness, and docs are in place; **application code is not started** while the Li language surface stabilizes.

| Branch | Use |
|--------|-----|
| [`main`](https://github.com/li-langverse/lis/tree/main) | Stable; green CI |
| [`dev`](https://github.com/li-langverse/lis/tree/dev) | Integration |

## Quick start (contributors)

```bash
git clone https://github.com/li-langverse/lis.git
cd lis
git checkout dev
./scripts/ci.sh
```

## Data platform stub (PH-DB-3)

Registry-min bundle supervisor (stubs until [lidb](https://github.com/li-langverse/lidb) WP1):

```bash
export LI_DATA_DIR=~/.local/share/lis/data
export LI_PROFILE=registry-min
./bin/lis db start
./bin/lis db status
```

See [docs/cli-db.md](docs/cli-db.md) and [profiles/registry-min.toml](profiles/registry-min.toml).

## Registry auth (MVP)

Email+password signup/login and API tokens on the same registry port (`/v1/auth/*`). Phase 1 TOTP/WebAuthn spec: [docs/auth-2fa-webauthn.md](docs/auth-2fa-webauthn.md).

```bash
export LI_DATA_DIR=~/.local/share/lis/data
export LI_JWT_SECRET="$(openssl rand -hex 32)"   # required for sessions
export LI_REGISTRY_MOCK=1                        # optional offline store
python3 routes/registry/server.py
```

Interactive client login (from **lip** checkout):

```bash
./scripts/lip-login.sh
```

Writes `~/.config/lip/credentials.toml` with `registry.url` and `registry.token`.

### Environment (interactive setup)

| Variable | Required | Purpose |
|----------|----------|---------|
| `LI_JWT_SECRET` | Yes (auth) | HS256 key for session JWTs — generate once per deploy |
| `LI_REGISTRY_DEV_TOKEN` | No | Dev-only publish bearer bypass (never in production) |
| `LI_DATA_DIR` | Yes | Persistent auth + registry mock data |
| `LI_API_PORT` | No | Registry listener port (default `54321`) |

Example `.env` for local dev (do not commit):

```bash
LI_DATA_DIR=./.li-data
LI_JWT_SECRET=local-dev-secret-change-me
LI_REGISTRY_DEV_TOKEN=test-token
LI_REGISTRY_MOCK=1
LI_API_PORT=54321
```

## Staging (Majico / containers)

Self-hosted VPS staging without Supabase Cloud: validated **li-httpd TOML** â†’ **Caddy** edge, Docker Compose for app containers.

```bash
./scripts/install-lis.sh
```


## Li Data Studio (PH-DB-11)

Web console: [data-studio-ui/README.md](data-studio-ui/README.md) — 
pm run dev on port 54324 after lis db start.

## Docs

- [docs/index.md](docs/index.md) â€” overview
- [docs/plan.md](docs/plan.md) â€” full design
- [docs/packages/](docs/packages/) â€” per-package function catalogs
- [docs/package-workflow.md](docs/package-workflow.md) â€” `li-new-package` / lip Â§ A3 (required)
- [docs/org-packages.md](docs/org-packages.md) â€” org repos (`li-math`, etc.)

## License

GPL-3.0-or-later â€” see [LICENSE](LICENSE).
