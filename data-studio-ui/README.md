# Li Data Studio UI (PH-DB-11)

Supabase Studio–aligned web console for **`lis db`** and **lidb**. Part of epic PH-DB-11; plan in [lic](https://github.com/li-langverse/lic/blob/main/docs/superpowers/plans/ph-db-11-li-data-studio.md).

## Quick start

```bash
# From lis repo root — start data platform
export LI_DATA_DIR="${HOME}/.local/share/lis/data"
export LI_PROFILE=registry-min
export LIDB_ROOT="../lidb"   # sibling lidb checkout
./bin/lis db start

cd data-studio-ui
npm install
npm run dev
```

Open http://localhost:54324

| Tab | Status |
|-----|--------|
| **Database** | Live `lis db status` + catalog table browser + read-only row viewer |
| **SQL Editor** | Read-only SELECT runner + CSV export |
| **Authentication** | Registry health + published packages grid + RLS doc links |
| **Storage** | Honest “not configured” for registry-min |
| **Realtime** | Supervisor status for WS :54323 |
| **Logs** | Tail changefeed JSONL / supervisor logs from `LI_DATA_DIR` |
| **Settings** | Profile, ports, masked JWT secret, RLS/storage flags |

## Docker (optional)

With the PH-DB compose stack running:

```bash
docker compose -f docker-compose.ph-db.yml up -d
cd data-studio-ui && npm install && npm run dev
```

Set `LIS_ROOT`, `LI_DATA_DIR`, and `LIDB_ROOT` to match the container layout when the UI runs on the host against a Dockerized lis-db.

## Environment

| Variable | Default | Purpose |
|----------|---------|---------|
| `LIS_ROOT` | `../` (parent of data-studio-ui) | Path to lis checkout for `bin/lis` |
| `LI_DATA_DIR` | `~/.local/share/lis/data` | lidb data directory |
| `LIDB_ROOT` | `../lidb` | lidb checkout for Python bridge |
| `LIS_PYTHON` | `python3` / `python` | Python for `scripts/lidb_studio_bridge.py` |
| `LIS_DB_STATUS_SHELL` | `bash` on Windows | Shell to run `lis db status` |
| `LI_API_PORT` | `54321` | Registry REST proxy target |
| `LI_REALTIME_PORT` | `54323` | Realtime WS port for status panel |

## Scripts

| Command | Description |
|---------|-------------|
| `npm run dev` | Dev server on port **54324** (avoids registry :54321) |
| `npm run build` | Production build |
| `npm run start` | Serve production build |

## Architecture

Next.js API routes call:

- `bin/lis db status` — supervisor health
- `scripts/lidb_studio_bridge.py` — lidb catalog / read-only SQL via `liorm.embed_engine`
- Registry REST at `LI_API_PORT` — packages list for Auth tab

No write path in the studio UI; CRUD remains via registry API or future liorm plans.
