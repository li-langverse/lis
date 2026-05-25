# Release notes: 2026-05-25 — PH-DB-3 lis bundle stub

**Status:** In progress (stub)  
**Repo:** li-langverse/lis  
**PH / REQ:** PH-DB-3 / registry data platform  
**Author:** agent

---

## Summary

Adds **`lis db`** supervisor CLI stubs (`start|stop|status|migrate`), **`registry-min`** profile TOML, and architecture docs for **lidb in-process** embedding. No real database engine yet — interface contract until WP1 (`lidb` scaffold) lands.

## Agent continuation

1. After WP1 merges: replace stub supervisor with `lidb` embedded link + real ports.
2. Wire `lis db migrate` to `lidb/migrations/001_registry.sql`.
3. Align REST port 54321 with lip registry OpenAPI (WP4).
4. Run `./scripts/ci.sh` and `li-tests/db/run_cli_stub.sh` before PR updates.

## Changed

| Area | What | Evidence |
|------|------|----------|
| CLI | `bin/lis db *` | `docs/cli-db.md` |
| Profile | `profiles/registry-min.toml` | verticals + WP deps |
| Docs | `docs/architecture.md` PH-DB section | mermaid bundle diagram |
| Tests | `li-tests/db/run_cli_stub.sh` | CI smoke |

## Dependencies (sequenced)

| WP | Delivers | Blocks |
|----|----------|--------|
| WP1 | `lidb` repo, `001_registry.sql` | Real `lis db start` |
| WP2 | `liorm`, `liq` | Agent-safe queries |
| WP4 | lip registry OpenAPI | Port 54321 handlers |

## Breaking changes

None.

## Security

Stub only — no network listeners opened in PH-DB-3.
