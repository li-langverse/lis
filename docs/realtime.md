# Realtime (Supabase parity start — WP-N3)

`lis` exposes a **Phoenix Channels v1.0.0** WebSocket compatible with [Supabase Realtime protocol](https://supabase.com/docs/guides/realtime/protocol) for `postgres_changes` only (no broadcast/presence/binary v2 in this phase).

## Endpoints

| Surface | Default | Profile |
|---------|---------|---------|
| WebSocket | `ws://127.0.0.1:54323/realtime/v1/websocket?apikey=<jwt>` | `stack-full` |
| Changefeed | Native `lidb_changefeed_poll` or `$LI_DATA_DIR/wal.changefeed.jsonl` | all realtime profiles |

Start manually:

```bash
export LI_DATA_DIR=/tmp/lis-data
export PYTHONPATH="$(pwd)"
python3 routes/realtime/server.py --port 54323
```

Or via supervisor:

```bash
LI_PROFILE=stack-full ./bin/lis db start
```

## Protocol (v1.0.0 subset)

1. Connect WebSocket (optional `apikey` query = JWT).
2. Send `phx_join` on topic `realtime:<channel>` with `payload.config.postgres_changes[]` (`event`, `schema`, `table`, optional `filter`).
3. Receive `phx_reply` + `system` (postgres subscription ok).
4. Receive `postgres_changes` when WAL/changefeed emits a matching row.

Client message shape (JSON text frames):

```json
{
  "topic": "realtime:registry",
  "event": "phx_join",
  "payload": {
    "config": {
      "postgres_changes": [
        { "event": "INSERT", "schema": "public", "table": "package_versions" }
      ]
    },
    "access_token": "<jwt>"
  },
  "ref": "1",
  "join_ref": "1"
}
```

Server `postgres_changes` payload matches Supabase `data` + `ids` fields (see protocol docs).

**Not implemented (yet):** v2.0.0 array framing, binary broadcast, presence, private channel replication, `access_token` refresh mid-flight.

## Changefeed source interface

**Default:** `ChangefeedSource` calls `lidb_changefeed_poll` via ctypes when `liblidb_changefeed` is on `LD_LIBRARY_PATH` / `LIDB_CHANGEFEED_LIB`, or via `scripts/lidb_changefeed_poll_once.py` when `LI_CHANGEFEED_NATIVE=subprocess`.

| Env | Effect |
|-----|--------|
| `LI_CHANGEFEED_NATIVE=0` | JSONL-only (`wal.changefeed.jsonl` + mock file) |
| `LI_CHANGEFEED_NATIVE=subprocess` | One-shot poll helper per loop |
| `LIDB_CHANGEFEED_LIB` | Path to `liblidb_changefeed.{dylib,so}` |
| `LIDB_BUILD_DIR` | Prefer this lidb cmake build dir for lib discovery |

**Dependency:** [li-langverse/lidb#11](https://github.com/li-langverse/lidb/pull/11) (`lidb_changefeed_c.h`). Do not merge this lis PR until #11 is on lidb `main` and the shared library is built (`scripts/changefeed_smoke.sh`).

Native poll JSON (from `lidb::Changefeed::event_to_json`):

```json
{"lsn":2,"table":"package_versions","op":"insert","payload_bytes":0}
```

lis maps that to `WalChangefeedEvent` (`record` may be `{}` until heap row materialization lands).

Full-row JSONL (tests / ops) still supported:

| Field | Type | Notes |
|-------|------|-------|
| `lsn` | int | Monotonic log id |
| `schema` | string | Default `public` |
| `table` | string | Required |
| `op` | string | `insert` \| `update` \| `delete` |
| `record` | object | New row |
| `old_record` | object | Prior row (updates/deletes) |

Paths:

- **Native:** `lidb_changefeed_open(LI_DATA_DIR)` in the poll thread (`routes/realtime/lidb_native.py`).
- **Fallback:** `$LI_DATA_DIR/wal.changefeed.jsonl` and `wal.changefeed.mock.jsonl`.
- **Tests / dev:** `push_mock()` or `native_insert()` when the library is linked.

See `lidb/docs/changefeed.md` for Unix socket fan-out (`lidb_changefeed_serve_unix`).

## JWT authentication

| Source | Precedence |
|--------|------------|
| `payload.access_token` on `phx_join` | Highest |
| `apikey` query parameter | Fallback |
| Neither | `anon` role |

Verification:

- **`LI_REALTIME_JWT_SECRET` set:** HS256 HMAC verify (stub; use same secret as lis auth when wired).
- **Unset:** decode payload only (dev/test) — **not for production**.

Reject join when `LI_REALTIME_REQUIRE_AUTH=1` and token resolves to anonymous without `sub`.

## RLS filter on subscription delivery

Realtime does **not** re-run SQL policies; it filters **changefeed rows** before `postgres_changes` push, aligned with [lidb `docs/auth-rls.md`](../lidb/docs/auth-rls.md) registry tenants:

| Role | Delivery |
|------|----------|
| `service_role` | All rows |
| `authenticated` + `publisher_id` claim | Rows where `record.publisher_id` matches claim (or column absent) |
| `anon` | Public rows only (`publisher_id` absent on record) |

Mismatch rows are dropped silently (no leak). Full policy evaluation remains in lidb executor; Realtime filter is a coarse gate until logical replication carries policy proofs.

## Environment

| Variable | Default | Purpose |
|----------|---------|---------|
| `LI_REALTIME_PORT` | `54323` | WebSocket listen port |
| `LI_REALTIME_HOST` | `127.0.0.1` | Bind address |
| `LI_REALTIME_WS_PATH` | `/realtime/v1/websocket` | Logged path hint |
| `LI_REALTIME_REQUIRE_AUTH` | `0` | Reject anonymous joins |
| `LI_REALTIME_JWT_SECRET` | unset | Enable HS256 verify |
| `LI_DATA_DIR` | `~/.local/share/lis/data` | WAL JSONL location |

## Dependencies

Python package **`websockets`** (async server). Install for dev/CI:

```bash
python3 -m pip install websockets
```

## Tests

`tests/realtime-ws.test` — connect, `phx_join`, mock insert, assert `postgres_changes` INSERT.
