# li-httpd implementation status

## Done (infra — no `.li` yet)

- [x] Package stubs (`packages/li-*`, workspace `li.toml`)
- [x] tier5_http TOML harness (`verify_http`, `bench_http`, `exploit_http`, `audit_nginx_src`)
- [x] `nginx_mitigations.toml` + Tier A/F/G exploit stubs
- [x] CI: `./scripts/ci.sh` (3 OS in GitHub Actions)
- [x] `.gitmodules` for nginx oracle (optional submodule init)
- [x] Easy TOML desugar + routing oracle (`scripts/httpd_config.py`, `li-tests/run_httpd_config.sh`)
- [x] tier5 harness: `verify_http`, `bench_http`, `exploit_http`, `audit_nginx_src`

## Blocked on `lic` (P0 — before M1 `.li`)

| Gate | Master plan | Unblocks |
|------|-------------|----------|
| **2e–2f** Lean on `lic build` | Phase 2e–2f | Spec-first httpd modules |
| **Bytes / I/O** | httpd plan w0-bytes-io | `li-bytes`, parsers, config |
| **Async reactor** | w1-async-reactor | `li-net`, connections |
| **HTTP/1 parser** | w2-http11 | `li-http`, M1 core |

Track compiler: [li-langverse/lic](https://github.com/li-langverse/lic) master plan phase **H**.

## Next implementation steps (when P0 green)

1. Re-scaffold packages: `./scripts/li-new-package … --out packages` from `lic`
2. `li-bytes` → `li-net` → `li-http` → `li-httpd` (path deps)
3. M1: static + proxy + TOML desugar + `validate-config`
4. Wire harness to real binaries; enable `suite.toml` timing profile

## Agent discipline

See [lic engineering-standards](https://github.com/li-langverse/lic/blob/dev/docs/ecosystem/engineering-standards.md).
