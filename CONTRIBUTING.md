# Contributing to lis

## Branches

| Branch | Purpose |
|--------|---------|
| `main` | Release-aligned; always green CI |
| `dev` | Integration; merge to `main` via PR |

Keep `dev` mergeable into `main`: rebase or merge `main` into `dev` regularly.

## CI

Every PR to `main` or `dev` runs on **ubuntu-24.04**, **macos-14**, and **windows-latest**:

- Infra layout check
- TOML validation
- Security exploit TOML schema tests
- Load/bench TOML schema tests (stub until `li-httpd` ships)

```bash
./scripts/ci.sh
```

## Multi-agent & upstream sync

**Mandatory (read before implementation):**

- [lic: engineering-standards](https://github.com/li-langverse/lic/blob/dev/docs/ecosystem/engineering-standards.md) — functionality, security, performance
- [lic: vision-and-roadmap](https://github.com/li-langverse/lic/blob/dev/docs/ecosystem/vision-and-roadmap.md)
- [lic: agent coordination](https://github.com/li-langverse/lic/blob/dev/docs/ecosystem/agent-coordination.md) — `.li-agent-coord.json`, Cursor hooks
- [lic: language evolution](https://github.com/li-langverse/lic/blob/dev/docs/ecosystem/language-evolution.md) — pins when **`lic`** changes

## Packages

**Do not hand-roll `packages/<name>/`.** Use `scripts/li-new-package` from [li-langverse/li](https://github.com/li-langverse/li) when Phase **Pkg** lands ([scaffold plan](https://github.com/li-langverse/li/blob/dev/docs/superpowers/plans/2026-05-16-li-package-scaffold.md)); `li.toml` must match [lip § A3](https://github.com/li-langverse/li/blob/dev/docs/superpowers/plans/2026-05-16-li-package-manager-lip.md). See [docs/package-workflow.md](docs/package-workflow.md).

Existing stubs in this repo will be **re-generated** with that CLI before implementation starts.

## Implementation status

**Infra-only:** packages contain manifests and docs; Li source implementation waits for language stabilization. See `docs/plan.md`.

## License

GPL-3.0-or-later (see LICENSE).
