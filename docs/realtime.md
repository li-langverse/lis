# Realtime (Supabase parity start — WP-N3)

`lis` exposes a **Phoenix Channels v1.0.0** WebSocket compatible with [Supabase Realtime protocol](https://supabase.com/docs/guides/realtime/protocol) for `postgres_changes` only (no broadcast/presence/binary v2 in this phase).

## Endpoints

| Surface | Default | Profile |
|---------|---------|---------|
| WebSocket | `ws://127.0.0.1:54323/realtime/v1/websocket?apikey=<jwt>` | `stack-full` |
| Changefeed stub | `$LI_DATA_DIR/wal.changefeed.jsonl` | all realtime profiles |

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

Until **lidb** exposes `subscribe_wal()` to lis in-process, the supervisor polls a JSONL stub (same shape as `lidb::Changefeed::poll_json_line`):

| Field | Type | Notes |
|-------|------|-------|
| `lsn` | int | Monotonic log id |
| `schema` | string | Default `public` |
| `table` | string | Required |
| `op` | string | `insert` \| `update` \| `delete` |
| `record` | object | New row |
| `old_record` | object | Prior row (updates/deletes) |

Paths:

- **Production path (future):** lidb WAL fan-out → lis embed adapter → `ChangefeedSource` (no file poll).
- **Current stub:** poll `$LI_DATA_DIR/wal.changefeed.jsonl` written by lidb embed or ops tooling.
- **Tests / dev:** append to `wal.changefeed.mock.jsonl` or call `ChangefeedSource.push_mock()` from Python.

Planned lidb C++ API (see `lidb/engine/include/lidb/changefeed.hpp`):

```cpp
SubscriptionId subscribe(std::string_view table, Callback callback);
void on_wal_append(uint64_t lsn, ChangefeedOp op, std::string_view table, const std::vector<std::byte>& payload);
```

lis will replace file poll with:

```python
# future (pseudo)
lidb.changefeed.subscribe_wal(data_dir, on_event=source.ingest_native)
```

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
