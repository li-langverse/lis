# Librebase Studio UI (PH-DB-13 phase 1)

Modern data console for **project-scoped lidb** stacks on Librebase. Replaces agent control-plane UI with org → project → database workflow.

## Quick start

```bash
cd data-studio-ui
npm install
npm run dev
```

Open http://localhost:54324 — create a project, click **Launch database**, then open Database / SQL.

### Prerequisites for Launch database

- `LIS_ROOT` points to your lis checkout (default: parent of data-studio-ui)
- `LIDB_ROOT` points to a built lidb with native embed
- **Windows:** set `LIS_DB_STATUS_SHELL=bash` and run the dev server from Git Bash/WSL

Each project gets its own `LI_DATA_DIR` under `~/.local/share/lis/studio/projects/<id>/data` and dedicated ports (from 55000+).

## Flow

| Step | UI |
|------|-----|
| Projects landing | `/` — list + **New project** |
| Create | name + region stub |
| Project dashboard | `/projects/:id` — **Launch database**, status cards |
| Studio tabs | Database, SQL Editor, Settings (project-scoped) |

## Environment

| Variable | Default | Purpose |
|----------|---------|---------|
| `STUDIO_DATA_DIR` | `~/.local/share/lis/studio` | Project registry + per-project data roots |
| `STUDIO_PROJECTS_FILE` | `$STUDIO_DATA_DIR/projects.json` | JSON project store |
| `LIS_ROOT` | `../` | lis checkout for `bin/lis` |
| `LIDB_ROOT` | `../lidb` | lidb for Python bridge |
| `LIS_DB_STATUS_SHELL` | `bash` on Windows | Shell for `lis db` commands |

Plan: [ph-db-13-cloud-studio-projects.md](https://github.com/li-langverse/lic/blob/main/docs/superpowers/plans/ph-db-13-cloud-studio-projects.md)

## Removed (PH-DB-13)

- `/agents` page, agent trace, control-plane table browser
- Agent dashboard proxy API routes (`/api/agents/*`, `/api/control-plane/*`)

Legacy top-level tabs (`/database`, `/sql`, …) redirect to Projects landing.
