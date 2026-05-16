# Continuous integration

## Matrix

| OS | Runner | Jobs |
|----|--------|------|
| Linux | `ubuntu-24.04` | infra + security + load |
| macOS | `macos-14` | same |
| Windows | `windows-latest` | same (bash) |

## Local

```bash
./scripts/ci.sh
```

## Phases

1. **Infra (current):** TOML + layout + pytest harness — no `li-httpd` binary.
2. **Post-P0:** wire `lic build` from Li compiler when packages gain `.li` sources.
3. **M1.5+:** live exploit/load jobs against built binary.
