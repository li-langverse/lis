# Li Langverse packages

## How to create packages (required)

Use the Li master-plan toolchain — **never** copy `li.toml` by hand:

1. **[`li-new-package`](https://github.com/li-langverse/li/blob/dev/docs/superpowers/plans/2026-05-16-li-package-scaffold.md)** — `./scripts/li-new-package <name> --kind library|binary`
2. **[`li.toml` schema](https://github.com/li-langverse/li/blob/dev/docs/superpowers/plans/2026-05-16-li-package-manager-lip.md)** — § A3 (`edition`, `[package.metadata.lip]`, workspace `members`)
3. **`lip init` / `lip install`** (later) — same layout; adds lockfile + registry

Details: [package-workflow.md](package-workflow.md).

## Where packages live

| Package | In `lis` monorepo | Separate org repo (when ready) |
|---------|-------------------|--------------------------------|
| `li-httpd`, `li-http`, `li-net`, … | yes — re-scaffold with `li-new-package` | optional split |
| `li-math` | infra stub until re-scaffolded | **li-langverse/li-math** (create repo via same CLI) |

Server-specific code stays in **lis**; shared numerics → **li-math** org repo when split.
