# lis CLI

## `lis db` (PH-DB-3)

Embedded **lidb** supervisor for local registry-min workloads.

| Command | Purpose |
|---------|---------|
| `lis db start` | Load profile, migrate, register liq plans, mark ready |
| `lis db migrate` | Apply `001_registry.sql` via `lidb_embed` |
| `lis db status` | JSON health; exit `0` when engine ready |
| `lis db stop` | Clear supervisor state (preserves `LI_DATA_DIR`) |

Flags: `--profile`, `--data-dir`, `--json` (pretty JSON on supported commands).

Full contract: [db.md](db.md).

## `li-httpd` (planned)

| Command | Purpose |
|---------|---------|
| `li-httpd` | Start server |
| `li-httpd validate-config` | Desugar + validate TOML |
| `li-httpd explain-config` | Print canonical config |
| `li-httpd setup` | TLS + censor + default paths |
| `li-httpd setup-tls` | Certificates only |
| `li-httpd setup-censor` | Generate `leak_censor.generated.toml` from migrations |

Not implemented in infra-only phase.
