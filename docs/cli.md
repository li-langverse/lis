# CLI

## `lis db` (PH-DB-3 stub)

| Command | Purpose |
|---------|---------|
| `lis db start` | Start registry-min bundle (stub supervisor) |
| `lis db stop` | Stop bundle |
| `lis db status` | Ports, profile, lidb link state |
| `lis db migrate` | Apply lidb migrations (stub) |

See [cli-db.md](cli-db.md).

## li-httpd (planned)

| Command | Purpose |
|---------|---------|
| `li-httpd` | Start server |
| `li-httpd validate-config` | Desugar + validate TOML |
| `li-httpd explain-config` | Print canonical config |
| `li-httpd setup` | TLS + censor + default paths |
| `li-httpd setup-tls` | Certificates only |
| `li-httpd setup-censor` | Generate `leak_censor.generated.toml` from migrations |

Not implemented in infra-only phase.
