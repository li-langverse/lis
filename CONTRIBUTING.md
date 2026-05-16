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

## Implementation status

**Infra-only:** packages contain manifests and docs; Li source implementation waits for language stabilization. See `docs/plan.md`.

## License

GPL-3.0-or-later (see LICENSE).
