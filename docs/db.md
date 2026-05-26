# lis db supervisor (PH-DB-3 / WP-I)

**lis** supervises an embedded [**lidb**](https://github.com/li-langverse/lidb) engine for local registry and control-plane workloads. Downstream tools (**li-cursor-agents**, **benchmarks** tier_db_registry) use `LI_DATA_DIR` and `lis db status` as a health gate.

Handoff contract: [lidb/docs/handoff-wp5-lis.md](https://github.com/li-langverse/lidb/blob/main/docs/handoff-wp5-lis.md).

Profile catalog: [`profiles/README.md`](../profiles/README.md).

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

**Embed profiles** (`registry-min`, `control-plane-min`) use in-process embed only — no TCP loopback unless a profile sets `tcp_port > 0` with a non-`in_process` embed mode (see TCP stub below).

## Commands

```bash
export LI_DATA_DIR="${LI_DATA_DIR:-./.li-data}"
export LI_PROFILE="${LI_PROFILE:-registry-min}"

lis db start      # migrate, register liq plans, write ready state
lis db start --foreground   # WP-I: block for systemd/Docker; JSON on stdout
lis db migrate    # apply migrations only
lis db status     # JSON health; exit 0 when ready
lis db stop       # clear supervisor state (keeps data dir)
```

`lis db status` prints JSON (protocol version **1**):

```json
{
  "protocol_version": "1",
  "live": true,
  "ready": true,
  "profile": "control-plane-min",
  "service": "control-plane",
  "data_dir": "/path/.li-data",
  "catalog": "/path/.li-data/.lidb/catalog.heap",
  "migration": "001_registry.sql",
  "verticals": ["registry", "control-plane"],
  "migrated": true,
  "engine": "lidb_embed",
  "plans_registered": 7,
  "checks": {
    "catalog": "ok",
    "engine": "ok",
    "plans": "ok",
    "tcp_listen": "off"
  },
  "readiness_requires": ["catalog", "engine", "plans"],
  "tcp_listen": false,
  "tcp_port": 0,
  "embed_mode": "in_process"
}
```

### Orchestrator probes

| Field | Meaning |
|-------|---------|
| `live` | CLI responded (liveness) |
| `ready` | All `readiness_requires` checks pass |
| `checks` | Per-component status for debugging |
| `protocol_version` | Bump on breaking JSON changes (WP-J) |

Docker / compose:

```yaml
healthcheck:
  test: ["CMD", "lis", "db", "status", "--json"]
  interval: 30s
  timeout: 5s
  retries: 3
```

systemd: see [`profiles/systemd/lis-db@.service`](../profiles/systemd/lis-db@.service).

## Profiles

| Profile | Use |
|---------|-----|
| `registry-min` | Package registry + minimal agent_runs reads (default dev) |
| `control-plane-min` | **Hosting** for `LI_CONTROL_PLANE_STORE=lidb` — registry + control-plane liq plans |
| `tcp-wire-stub` | **Document only** — future TCP loopback `:54321`; start fails with `NotImplementedError` |

See [`profiles/registry-min.toml`](../profiles/registry-min.toml), [`profiles/control-plane-min.toml`](../profiles/control-plane-min.toml), and [`profiles/README.md`](../profiles/README.md).

### control-plane-min (WP-I)

For agent stacks:

```bash
export LI_PROFILE=control-plane-min
export LI_CONTROL_PLANE_STORE=lidb   # in li-cursor-agents
lis db start && lis db status
```

Pre-registered plans include registry reads plus `control_plane_state.latest`, `control_plane_reports.recent`, `briefing_snapshots.by_hash`, and `queued_agent_tasks.by_briefing`.

### TCP wire stub (not implemented)

[`profiles/tcp-wire-stub.toml`](../profiles/tcp-wire-stub.toml) reserves `embed_mode = tcp_loopback` and `tcp_port = 54321` for PH-DB-4+. **Do not use in production** — `lis db start` raises `NotImplementedError`. External clients should use embed + `LI_DATA_DIR` until wire lands.

## Smoke

```bash
./scripts/db-smoke.sh                              # registry-min (default)
LI_PROFILE=control-plane-min ./scripts/db-smoke.sh # hosting profile
./scripts/check-no-sqlite.sh
python3 -m pytest li-tests/test_db_supervisor.py -q
```

## Dependencies on lidb

| Migration / feature | Required by | Status |
|---------------------|-------------|--------|
| `migrations/001_registry.sql` | all profiles | **Hard** |
| Native bootstrap `agent_runs` | `control-plane-min` reads | **Hard** (lidb native catalog) |
| `002_control_plane.sql` (WP-J) | full control-plane persist | **Soft / blocked** — plans compile; tables pending WP-J |
| `lidb_embed` (`open`, `migrate`, `exec-json`) | supervisor | **Hard** |

- **Soft (WP-A):** full `liorm.execute` parity for all registry plans — supervisor already calls native embed; remaining pytest failures on lidb `main` are tracked in WP-A.
