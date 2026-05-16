# lis — Li HTTP gateway (li-httpd)

**lis** is the server repository for [li-httpd](plan.md): a proved, agent-native HTTP gateway (streaming SSE, TOML config, leak censorship, auto-TLS).

## Status

| Phase | State |
|-------|--------|
| **Infra** (now) | CI, packages layout, harness TOML, docs — **no application code yet** |
| **Implementation** | Blocked on Li language/compiler stabilization ([li-langverse/li](https://github.com/li-langverse/li)) |

## Quick links

| Doc | Content |
|-----|---------|
| [plan.md](plan.md) | Full implementation plan |
| [architecture.md](architecture.md) | Package graph |
| [ci.md](ci.md) | CI matrix and local runs |
| [cli.md](cli.md) | `li-httpd` commands (planned) |
| [packages/](packages/) | Per-package API catalogs |
| [package-workflow.md](package-workflow.md) | `li-new-package` / lip § A3 (required) |
| [org-packages.md](org-packages.md) | li-langverse org repos (e.g. li-math) |

## Repository

```
packages/          # publishable Li packages (stubs)
benchmarks/tier5_http/   # bench + exploit TOML harness
li-tests/          # validation runners
docs/              # this tree
```

## License

GPL-3.0-or-later — see [LICENSE](../LICENSE).
