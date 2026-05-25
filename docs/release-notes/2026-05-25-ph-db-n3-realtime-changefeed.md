# Release notes: 2026-05-25 — ph-db-n3-realtime-changefeed

**Status:** Ready for review  
**Repo:** li-langverse/lis  
**PR:** (feat/ph-db-realtime-changefeed)  
**PH / REQ:** PH-DB, WP-N3  
**Author:** agent

---

## Summary (one sentence)

Adds Supabase-shaped Realtime WebSocket (`postgres_changes` only) with WAL JSONL changefeed polling, JWT/RLS row filter, and `stack-full` profile enabling the module on `lis db start`.

## Agent continuation (required)

1. Read: `docs/realtime.md`, `lidb/engine/include/lidb/changefeed.hpp`, Supabase Realtime protocol diff in PR body.
2. Run: `python3 -m pip install websockets && ./tests/realtime-ws.test` and `./scripts/ci.sh`.
3. Then: wire lidb `subscribe_wal()` in-process (replace JSONL poll); add v2.0.0 protocol array framing if clients require it.
4. Blocked on: lidb native embed fan-out from lis supervisor — **until WP1 embed lands**.

## Changed (specific)

| Area | What | Evidence |
|------|------|----------|
| Realtime WS | `routes/realtime/` Phoenix v1.0.0 server, `phx_join` / `postgres_changes` | `./tests/realtime-ws.test` |
| Changefeed | Poll `wal.changefeed.jsonl` + mock JSONL; `push_mock()` for tests | test receives INSERT |
| Auth | JWT payload / optional HS256; RLS tenant filter on `publisher_id` | test RLS no-leak path |
| Profile | `profiles/stack-full.toml` port 54323 | `bin/lis db start --profile stack-full` |
| Supervisor | `lis_realtime_start` / stop / status | `bin/lis` |
| Docs | `docs/realtime.md` interface + JWT/RLS | — |

## Not changed (scope fence)

- Registry REST handlers / OpenAPI — unchanged.
- Broadcast, presence, private channels, protocol v2.0.0 binary frames — **not** in this PR.
- lidb `subscribe_wal()` Python binding — poll stub only.
- PostgREST / Storage / Studio verticals — **not** started.

## Breaking changes

None.

## Security

N/A for production deploy — bind `127.0.0.1`, JWT verify off unless `LI_REALTIME_JWT_SECRET` set. RLS filter is coarse row gate; full policy remains in lidb executor. Documented in `docs/realtime.md`.

## Performance

N/A — stub poll interval 50ms; no bench row.

## Downstream

| Repo | Action |
|------|--------|
| lip / clients | May point Supabase Realtime client at `ws://host:54323/realtime/v1/websocket` for dev |
| lidb | Expose `subscribe_wal` to replace JSONL poll |

## CHANGELOG entry (paste into Unreleased)

```markdown
### Added
- **WP-N3 / PH-DB:** Realtime WebSocket (`routes/realtime/`), `stack-full` profile, changefeed WAL stub poll, `tests/realtime-ws.test`, `docs/realtime.md`.
```
