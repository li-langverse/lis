# lis

**li-httpd** — proved AI/agent HTTP gateway written in [Li](https://github.com/li-langverse/li).

Secure-by-design TOML config, optional leak censorship (schema-driven setup), streaming SSE, rate limits, and cross-platform CI.

## Status

**Infrastructure** — packages, harness, and docs are in place; **li-httpd application code** is not started while the Li language surface stabilizes.

**PH-DB-3 (`lis db`)** — embedded **lidb** supervisor (`start|migrate|status|stop`) with `registry-min` profile is available; see [docs/db.md](docs/db.md).

| Branch | Use |
|--------|-----|
| [`main`](https://github.com/li-langverse/lis/tree/main) | Stable; green CI |
| [`dev`](https://github.com/li-langverse/lis/tree/dev) | Integration |

## Quick start (contributors)

```bash
git clone https://github.com/li-langverse/lis.git
cd lis
git clone https://github.com/li-langverse/lidb.git ../lidb  # sibling for lis db
pip install -e .
export LI_DATA_DIR=./.li-data
lis db start && lis db status
./scripts/ci.sh
```

## Dev containers (WP-H)

**Dev-only** — embed `registry-min` profile, not production Postgres or TCP wire.

Requires sibling **`lidb`** at `../lidb` (same layout as native `lis db`).

```bash
cd lis
docker compose -f docker-compose.ph-db.yml up --build -d
docker compose -f docker-compose.ph-db.yml exec lis-db lis db status
```

Default bind-mount: `./.li-data` → container `/data`. Override with `LI_DATA_DIR=/path/to/data`.

Without the compose plugin:

```bash
DOCKER_BUILDKIT=1 docker build -f docker/Dockerfile.supervisor --build-context lidb=../lidb -t li-langverse/lis-db-dev:local .
docker run -d -v ./.li-data:/data --name lis-db li-langverse/lis-db-dev:local
docker exec lis-db lis db status
```

Optional Postgres oracle for benchmarks (compose profile `bench`):

```bash
docker compose -f docker-compose.ph-db.yml --profile bench up -d postgres-oracle
export POSTGRES_URL=postgres://bench:bench@localhost:5432/registry_bench
```

### Connect agents (host)

Point **li-cursor-agents** (or other consumers) at the same data dir the container uses:

```bash
export LI_CONTROL_PLANE_STORE=lidb
export LI_DATA_DIR="${LI_DATA_DIR:-./.li-data}"   # must match compose bind-mount
export LI_LIDB_REPO="${LI_LIDB_REPO:-../lidb}"    # host checkout for bridge build
# optional health gate:
lis db status   # or: docker compose -f docker-compose.ph-db.yml exec lis-db lis db status
```

Images: `lis/docker/Dockerfile.supervisor` (multi-stage, bakes `lidb_embed`); standalone embed build in `lidb/docker/Dockerfile.embed`.

## Docs

- [docs/index.md](docs/index.md) — overview
- [docs/db.md](docs/db.md) — `lis db` / lidb embed (PH-DB-3)
- [docs/plan.md](docs/plan.md) — full design
- [docs/packages/](docs/packages/) — per-package function catalogs
- [docs/package-workflow.md](docs/package-workflow.md) — `li-new-package` / lip § A3 (required)
- [docs/org-packages.md](docs/org-packages.md) — org repos (`li-math`, etc.)

## License

GPL-3.0-or-later — see [LICENSE](LICENSE).
