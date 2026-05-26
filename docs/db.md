# lis db supervisor (PH-DB-3)

**lis** supervises an embedded [**lidb**](https://github.com/li-langverse/lidb) engine for local registry-min workloads. Downstream tools (**li-cursor-agents**, **benchmarks** tier_db_registry) use `LI_DATA_DIR` and `lis db status` as a health gate.

Handoff contract: [lidb/docs/handoff-wp5-lis.md](https://github.com/li-langverse/lidb/blob/main/docs/handoff-wp5-lis.md).

## Prerequisites

- Sibling clone: `li-langverse/lidb` at `main` (native `lidb_embed`; no sqlite3).
- `cmake` on PATH (first run builds `lidb_embed` under `lidb/build/smoke/`).
- Python 3.11+.

```bash
pip install -e .
export LIDB_REPO=../lidb   # optional if lidb is beside lis
```

## Environment

| Variable | Default | Purpose |
|----------|---------|---------|
| `LI_DATA_DIR` | `./.li-data` | Heap/WAL + `.lis/db-state.json` |
| `LI_PROFILE` | `registry-min` | Profile TOML under `profiles/` |
| `LIDB_REPO` | `../lidb` | Path to lidb checkout |
| `LIDB_EMBED` | auto | Override `lidb_embed` binary |

**registry-min** uses in-process embed only — no TCP loopback unless a profile sets `tcp_port > 0` (not implemented yet).

## Commands

```bash
export LI_DATA_DIR="${LI_DATA_DIR:-./.li-data}"
export LI_PROFILE="${LI_PROFILE:-registry-min}"

lis db start      # migrate, register liq plans, write ready state
lis db migrate    # apply migrations only
lis db status     # JSON health; exit 0 when ready
lis db stop       # clear supervisor state (keeps data dir)
```

`lis db status` prints JSON:

```json
{
  "ready": true,
  "profile": "registry-min",
  "data_dir": "/path/.li-data",
  "catalog": "/path/.li-data/.lidb/catalog.heap",
  "migrated": true,
  "engine": "lidb_embed",
  "tcp_listen": false
}
```

## Profile: registry-min

See [`profiles/registry-min.toml`](../profiles/registry-min.toml). Pre-registered plans include `agent_runs.recent`, `agent_runs.by_status`, and `packages.by_name` (compiled via **liq** at start).

## Smoke

```bash
./scripts/db-smoke.sh
./scripts/check-no-sqlite.sh
```

## Dependencies on lidb

- **Hard:** `lidb_embed` (`open`, `migrate`, `exec-json`), `migrations/001_registry.sql`.
- **Soft (WP-A):** full `liorm.execute` parity for all registry plans — supervisor already calls native embed; remaining pytest failures on lidb `main` are tracked in WP-A.
