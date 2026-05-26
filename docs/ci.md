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

## PH-DB cross-repo gate (WP-G)

| Workflow | Trigger | Scope |
|----------|---------|-------|
| `CI` | PR, push | OS matrix; lidb checkout on Linux/macOS; `db-smoke.sh` when cmake + `LIDB_REPO` |
| `PH-DB cross-repo gate` | PR, push, dispatch | **ubuntu only** — checkout lidb @ `LIDB_CI_REF`, cmake, lidb subset pytest, `db-smoke`, supervisor pytest |

**Env (consumers / local):**

| Variable | Default | Purpose |
|----------|---------|---------|
| `LIDB_REPO` | `../lidb` | Sibling lidb checkout for embed + liorm |
| `LIDB_CI_REF` | `main` | Ref for cross-repo checkout in GHA (`workflow_dispatch` input) |
| `LI_DATA_DIR` | — | Ephemeral data dir for `lis db` smoke |

Engine e2e for agents is **not** in lis CI — see **li-cursor-agents** `ph-db-lidb-engine.yml` (**dispatch only**).

## Phases

1. **Infra (current):** TOML + layout + pytest harness — no `li-httpd` binary.
2. **Post-P0:** wire `lic build` from Li compiler when packages gain `.li` sources.
3. **M1.5+:** live exploit/load jobs against built binary.
