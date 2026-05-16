# li-httpd CLI (planned)

| Command | Purpose |
|---------|---------|
| `li-httpd` | Start server |
| `li-httpd validate-config` | Desugar + validate TOML |
| `li-httpd explain-config` | Print canonical config |
| `li-httpd setup` | TLS + censor + default paths |
| `li-httpd setup-tls` | Certificates only |
| `li-httpd setup-censor` | Generate `leak_censor.generated.toml` from migrations |

Not implemented in infra-only phase.
