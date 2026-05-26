# lis db profiles (PH-DB-3 / WP-I)

TOML profiles under this directory configure **lidb** embed mode, migrations, verticals, and pre-registered **liq** plans for `lis db start`.

Select with `LI_PROFILE` or `lis db --profile <name>`.

## Profiles

| Profile | Use case | TCP | Migration deps |
|---------|----------|-----|----------------|
| [`registry-min.toml`](registry-min.toml) | Package registry + minimal agent_runs reads | off (`tcp_port = 0`) | `lidb/migrations/001_registry.sql` |
| [`control-plane-min.toml`](control-plane-min.toml) | **Hosting** for `LI_CONTROL_PLANE_STORE=lidb` — registry + control-plane read plans | off | `001_registry.sql` + native `agent_runs` bootstrap; **WP-J** for full control-plane tables |
| [`tcp-wire-stub.toml`](tcp-wire-stub.toml) | **Document only** — future PG loopback on `:54321` | stub (`NotImplementedError`) | same as registry-min |

### registry-min

Default dev profile. In-process embed only; no TCP listener. Plans: `agent_runs.recent`, `agent_runs.by_status`, `packages.by_name`.

### control-plane-min (WP-I)

Production-shaped **hosting** profile without TCP wire:

- Same embed path as `registry-min` (`embed_mode = in_process`, `tcp_port = 0`).
- Adds control-plane vertical and liq plans aligned with `li-cursor-agents` `CONTROL_PLANE_TABLES` reads.
- `[hosting]` block drives orchestrator readiness checks in `lis db status` JSON.

**lidb migration dependencies**

| Layer | Status | Notes |
|-------|--------|-------|
| `001_registry.sql` | **Required** | publishers, packages, … |
| Native bootstrap `agent_runs` | **Required** | lidb `native_catalog.cpp` |
| `002_control_plane.sql` (WP-J) | **Soft / blocked** | `control_plane_state`, reports, snapshots — plans compile today; persist e2e blocked until WP-J |

### tcp-wire-stub

Reserved for PH-DB-4+ when `lis db start` opens a loopback TCP port (`tcp_port = 54321`, `embed_mode = tcp_loopback`). **Not implemented** — starting this profile fails fast with `NotImplementedError`. Use `control-plane-min` or `registry-min` for embed hosting.

## Environment contract

| Variable | Default | Purpose |
|----------|---------|---------|
| `LI_PROFILE` | `registry-min` | Profile stem (this directory) |
| `LI_DATA_DIR` | `./.li-data` | Heap/WAL + `.lis/db-state.json` |
| `LIDB_REPO` | `../lidb` | Sibling lidb checkout |

For agent stacks set `LI_PROFILE=control-plane-min` alongside `LI_CONTROL_PLANE_STORE=lidb` and shared `LI_DATA_DIR`.

## Health / readiness (orchestrators)

`lis db status` emits JSON for Docker `HEALTHCHECK`, Kubernetes probes, and systemd:

- **`live`**: process responded (always `true` when status exits 0).
- **`ready`**: catalog migrated + engine probe ok + plans registered (when started).
- **`checks`**: per-component status (`catalog`, `engine`, `plans`).
- **`protocol_version`**: `"1"` — bump on breaking status JSON changes (WP-J).

Example probe:

```bash
lis db status --json | jq -e '.ready == true'
```

Compose / k8s sketch:

```yaml
healthcheck:
  test: ["CMD", "lis", "db", "status", "--json"]
  interval: 30s
  timeout: 5s
  retries: 3
```

## systemd sample

See [`systemd/lis-db@.service`](systemd/lis-db@.service). Enable with profile name as instance:

```bash
sudo cp profiles/systemd/lis-db@.service /etc/systemd/system/
sudo systemctl enable --now lis-db@control-plane-min
```

## Smoke

```bash
LI_PROFILE=registry-min ./scripts/db-smoke.sh
LI_PROFILE=control-plane-min ./scripts/db-smoke.sh
```
