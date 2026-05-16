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

## Docs

- [docs/index.md](docs/index.md) — overview
- [docs/plan.md](docs/plan.md) — full design
- [docs/packages/](docs/packages/) — per-package function catalogs
- [docs/org-packages.md](docs/org-packages.md) — org repos (`li-math`, etc.)

## License

GPL-3.0-or-later — see [LICENSE](LICENSE).
