# lis

**li-httpd** — proved AI/agent HTTP gateway written in [Li](https://github.com/li-langverse/li).

Secure-by-design TOML config, optional leak censorship (schema-driven setup), streaming SSE, rate limits, and cross-platform CI.

## Status

**Infrastructure only** — packages, harness, and docs are in place; **application code is not started** while the Li language surface stabilizes.

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

## Staging (Majico / containers)

Self-hosted VPS staging without Supabase Cloud: validated **li-httpd TOML** → **Caddy** edge, Docker Compose for app containers.

```bash
./scripts/install-lis.sh
lis http validate profiles/httpd/majico-staging.toml
# see docs/staging-majico.md
```

## Docs

- [docs/index.md](docs/index.md) — overview
- [docs/plan.md](docs/plan.md) — full design
- [docs/packages/](docs/packages/) — per-package function catalogs
- [docs/package-workflow.md](docs/package-workflow.md) — `li-new-package` / lip § A3 (required)
- [docs/org-packages.md](docs/org-packages.md) — org repos (`li-math`, etc.)

## License

GPL-3.0-or-later — see [LICENSE](LICENSE).
