# `lis db` — data platform supervisor (PH-DB-3)

**Status:** Stub — interface contract for the lean **lidb + lis** bundle. Runtime wiring waits on [lidb](https://github.com/li-langverse/lidb) WP1.

## Quick start

```bash
export LI_DATA_DIR="${HOME}/.local/share/lis/data"
export LI_PROFILE=registry-min

./bin/lis db start
./bin/lis db status
./bin/lis db migrate
./bin/lis db stop
```

Default ports (Supabase-local parity for control-plane dev):

| Port | Role |
|------|------|
| 54321 | Registry REST / PostgREST-shaped API |
| 54322 | Postgres wire (lidb) |

## Profiles

| Profile | File | Use |
|---------|------|-----|
| `registry-min` | [profiles/registry-min.toml](../profiles/registry-min.toml) | lip registry + domain MVP |

## Environment

| Variable | Default | Purpose |
|----------|---------|---------|
| `LI_DATA_DIR` | `~/.local/share/lis/data` | WAL, heap, migrations state |
| `LI_PROFILE` | `registry-min` | Vertical bundle selection |
| `LI_API_PORT` | `54321` | REST listener |
| `LI_DB_PORT` | `54322` | DB listener |

## Implementation notes

- **Single supervisor:** `lis` owns process lifecycle; **lidb** is linked **in-process** (no separate `postgres` container).
- **WP1 blocker:** Until `lidb` ships embedded mode, `lis db start` writes stub state only.
- **Separate packages:** OAuth, Studio, Storage, Realtime remain opt-in per [profiles/registry-min.toml](../profiles/registry-min.toml).

See [architecture.md](architecture.md#li-data-platform-ph-db) for the bundle diagram.
