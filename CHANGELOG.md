# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [Unreleased]

### Added

- **Staging:** `profiles/httpd/majico-staging.toml`, `deploy/staging/` Docker Compose + Caddy bridge, `lis http` / `lis staging` CLI, `scripts/httpd_render_caddy.py`, `docs/staging-majico.md`, `packages/lis-cli` — [2026-05-28-staging-majico-httpd-bridge.md](docs/release-notes/2026-05-28-staging-majico-httpd-bridge.md).
- **PH-DB-4:** `docs/production-registry.md` host runbook (env template, `registry-min`, TLS via li-httpd) — [2026-05-25-production-registry.md](docs/release-notes/2026-05-25-production-registry.md).
- **WP-N3 / PH-DB:** `routes/realtime/` Phoenix v1.0.0 WebSocket, native `lidb_changefeed_poll` with JSONL fallback (`LI_CHANGEFEED_NATIVE=0`), JWT+RLS delivery filter, `profiles/stack-full.toml`, `tests/realtime-ws.test`, `docs/realtime.md` — blocked on [lidb#11](https://github.com/li-langverse/lidb/pull/11).
- **PH-DB-4:** `routes/registry/` REST handlers (list/get/publish/yank), `openapi/registry-v1.yaml`, mock liorm store, `tests/registry-api.test`, registry API on `lis db start`.
- **PH-DB-4 gap #2:** Registry store wires **lidb** `liorm.execute` (`store.py`, `liorm_store.py`); `LI_REGISTRY_MOCK=1` for mock — [2026-05-25-ph-db-4-lidb-liorm-wire.md](docs/release-notes/2026-05-25-ph-db-4-lidb-liorm-wire.md).
- **PH-DB-3:** `bin/lis db` supervisor stubs, `profiles/registry-min.toml`, architecture bundle diagram, `li-tests/db/run_cli_stub.sh`.
- Agent-kit sync and release-notes policy (roadmap v1.1.0).

### Changed

- **tier5_http:** multi-oracle `bench_http.py` + measured `benchmarks/results/latest.csv` (WP6 fill-all) — [2026-05-25-tier5-http-csv-full.md](docs/release-notes/2026-05-25-tier5-http-csv-full.md).
