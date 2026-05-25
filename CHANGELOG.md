# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [Unreleased]

### Added

<<<<<<< HEAD
<<<<<<< HEAD
- **PH-DB-4:** `docs/production-registry.md` host runbook (env template, `registry-min`, TLS via li-httpd) — [2026-05-25-production-registry.md](docs/release-notes/2026-05-25-production-registry.md).
=======
- **WP-N3 / PH-DB:** `routes/realtime/` Phoenix v1.0.0 WebSocket, WAL JSONL changefeed poll, JWT+RLS delivery filter, `profiles/stack-full.toml`, `tests/realtime-ws.test`, `docs/realtime.md`.
>>>>>>> b9980b3 (feat(ph-db): Realtime WebSocket changefeed (WP-N3))
=======
- **WP-N3 / PH-DB:** `routes/realtime/` Phoenix v1.0.0 WebSocket, native `lidb_changefeed_poll` with JSONL fallback (`LI_CHANGEFEED_NATIVE=0`), JWT+RLS delivery filter, `profiles/stack-full.toml`, `tests/realtime-ws.test`, `docs/realtime.md` — blocked on [lidb#11](https://github.com/li-langverse/lidb/pull/11).
>>>>>>> 5317161 (feat(ph-db): wire lis realtime to native lidb changefeed)
- **PH-DB-4:** `routes/registry/` REST handlers (list/get/publish/yank), `openapi/registry-v1.yaml`, mock liorm store, `tests/registry-api.test`, registry API on `lis db start`.
- **PH-DB-4 gap #2:** Registry store wires **lidb** `liorm.execute` (`store.py`, `liorm_store.py`); `LI_REGISTRY_MOCK=1` for mock — [2026-05-25-ph-db-4-lidb-liorm-wire.md](docs/release-notes/2026-05-25-ph-db-4-lidb-liorm-wire.md).
- **PH-DB-3:** `bin/lis db` supervisor stubs, `profiles/registry-min.toml`, architecture bundle diagram, `li-tests/db/run_cli_stub.sh`.
- Agent-kit sync and release-notes policy (roadmap v1.1.0).
