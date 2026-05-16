# Package workflow (lis)

**Do not hand-roll `packages/` directories.** Follow the Li compiler master plan:

| Doc | Role |
|-----|------|
| [li: engineering-standards](https://github.com/li-langverse/lic/blob/dev/docs/ecosystem/engineering-standards.md) | **Mandatory** functionality, security, performance |
| [li: vision-and-roadmap](https://github.com/li-langverse/lic/blob/dev/docs/ecosystem/vision-and-roadmap.md) | Where vision changes live |
| [li: agent coordination](https://github.com/li-langverse/lic/blob/dev/docs/ecosystem/agent-coordination.md) | Multi-agent + Cursor hooks on `lic` |
| [li: package scaffold](https://github.com/li-langverse/lic/blob/dev/docs/superpowers/plans/2026-05-16-li-package-scaffold.md) | `scripts/li-new-package`, layout, skill |
| [li: lip § A3](https://github.com/li-langverse/lic/blob/dev/docs/superpowers/plans/2026-05-16-li-package-manager-lip.md) | **Canonical `li.toml` schema** |
| [li: li-httpd plan](plan.md) | Server-specific package graph |

New features: document **Learned from** (2–4 ecosystems) per engineering-standards.

## Creating a new package

When `li-new-package` is available in [li-langverse/li](https://github.com/li-langverse/li):

```bash
cd /path/to/li   # compiler repo
./scripts/li-new-package li-foo --kind library --workspace packages --out /path/to/lis/packages
```

Later (phase 8b):

```bash
lip init li-foo    # equivalent to scaffold + lockfile hooks
```

## Ecosystem while language evolves

**lis** depends on **`lic`** (and later **lip** / **lit**). When the language changes:

1. Read [li-language: agent coordination](https://github.com/li-langverse/li-language/blob/dev/docs/ecosystem/agent-coordination.md).
2. Bump `li-toolchain.toml` when **`lic`** releases (file lands with implementation).
3. Keep `./scripts/ci.sh` green on **ubuntu / macOS / windows** before merging `dev` → `main`.

## This repo’s stubs

Current `packages/li-*` trees are **infra-only placeholders** (pre-Pkg). Before implementation:

1. Re-run `li-new-package` for each name to match § A3 `li.toml`.
2. Add root `[workspace].members` in `packages/li.toml`.
3. Register smoke tests under `li-tests/manifest.toml` per package.

## Org repos (e.g. li-math)

Create with the **same CLI** in a separate repository:

```bash
./scripts/li-new-package li-math --kind library --out ../li-math
```

See [org-packages.md](org-packages.md).
