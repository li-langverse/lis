# Realtime routes (WP-N3)

Supabase-shaped **Phoenix v1.0.0** WebSocket for `postgres_changes`.

| File | Role |
|------|------|
| `server.py` | Async WebSocket listener (`websockets`) |
| `protocol.py` | JSON frame encode/decode |
| `changefeed.py` | Native `lidb_changefeed_poll` + JSONL fallback |
| `lidb_native.py` | ctypes / subprocess lidb FFI |
| `auth.py` | JWT claims + RLS row filter |
| `session.py` | Channel postgres_changes subscriptions |

See [docs/realtime.md](../../docs/realtime.md).
