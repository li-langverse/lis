# Li Data Studio UI (PH-DB-11)

Supabase Studio–aligned web console for **`lis db`** and **lidb**. Part of epic PH-DB-11; plan in [lic](https://github.com/li-langverse/lic/blob/main/docs/superpowers/plans/ph-db-11-li-data-studio.md).

## Quick start

```bash
# From lis repo root — start data platform (optional)
export LI_DATA_DIR="${HOME}/.local/share/lis/data"
export LI_PROFILE=registry-min
./bin/lis db start

cd data-studio-ui
npm install
npm run dev
```

Open http://localhost:54324 — **Database** shows live `lis db status`.

## Environment

| Variable | Default | Purpose |
|----------|---------|---------|
| `LIS_ROOT` | `../` (parent of data-studio-ui) | Path to lis checkout for `bin/lis` |
| `LIS_DB_STATUS_SHELL` | `bash` on Windows | Shell to run `lis db status` |

## Scripts

| Command | Description |
|---------|-------------|
| `npm run dev` | Dev server on port **54324** (avoids registry :54321) |
| `npm run build` | Production build |
| `npm run start` | Serve production build |
