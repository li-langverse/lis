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

## Docs

- [docs/index.md](docs/index.md) — overview
- [docs/db.md](docs/db.md) — `lis db` / lidb embed (PH-DB-3)
- [docs/plan.md](docs/plan.md) — full design
- [docs/packages/](docs/packages/) — per-package function catalogs
- [docs/package-workflow.md](docs/package-workflow.md) — `li-new-package` / lip § A3 (required)
- [docs/org-packages.md](docs/org-packages.md) — org repos (`li-math`, etc.)

## License

GPL-3.0-or-later — see [LICENSE](LICENSE).
