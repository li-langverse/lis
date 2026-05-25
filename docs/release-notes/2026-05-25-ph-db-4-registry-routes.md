# Release notes: 2026-05-25 — PH-DB-4 registry REST routes

**Status:** Ready for review (stub)  
**Repo:** li-langverse/lis  
**PH / REQ:** PH-DB-4 / registry data platform  
**Author:** agent

---

## Summary

Adds **registry REST route stubs** (`GET/POST /v1/packages*`), **OpenAPI serve** (`GET /v1/openapi.yaml`), **mock liorm/lidb store**, **`profiles/registry-min.toml` modules list**, and **`tests/registry-api.test`** integration smoke. Depends on lidb contract only — no lidb link yet.

## Agent continuation

1. Read: `routes/registry/README.md`, `openapi/registry-v1.yaml`, `lidb/migrations/001_registry.sql`, `lidb/liorm/README.md`.
2. Run: `./scripts/ci.sh` and `./tests/registry-api.test`; `lis db start` then `curl http://127.0.0.1:54321/v1/packages`.
3. Then: replace `liorm_mock.py` with `liorm.execute` plans registered from profile `[modules.liorm_plans]` when WP1–WP2 merge.
4. Blocked on: embedded lidb engine + real SQL for `package_versions` / `yanks` — do not remove mock until `execute` passes security tests.

## Changed

| Area | What | Evidence |
|------|------|----------|
| Routes | `routes/registry/{handlers,liorm_mock,server}.py` | `tests/registry-api.test` |
| OpenAPI | `openapi/registry-v1.yaml` (from lip stub, port 54321) | `GET /v1/openapi.yaml` |
| Profile | `profiles/registry-min.toml` `[modules]` + `liorm_plans` | phase PH-DB-4 |
| CLI | `bin/lis db start` starts registry listener | `LI_REGISTRY_API` env |
| CI | `scripts/ci.sh` runs registry test | green locally |

## Not changed

- **li-httpd** M1 implementation and tier5 timing benches (still Python oracle).
- **lidb** C++ engine / WAL — WP1 repo only.
- **lip** publish client — still GitHub-first; no `lip registry push` wiring.
- **li-cursor-agents** control-plane store — still Supabase/disk (PH-DB-10).
- **Auth/OAuth** for registry-min profile — bearer token accepted but not validated (stub).

## Breaking changes

None.

## Security

Stub listener binds **127.0.0.1** only; bearer auth not verified. No new CVE tests — registry path is mock-only. When linking lidb, run `lidb/tests/security/run_all.sh` before defaulting `LI_REGISTRY_API=1` on non-loopback.

## Performance

N/A — in-memory mock; no benchmark row.

## Downstream

- **lip:** OpenAPI canonical stays in `lip/registry/api/`; sync `lis/openapi/registry-v1.yaml` on contract changes.
- **lidb:** WP1 migrations must match mock field names (`tree_digest`, `coverage_pct`, yank flags).
